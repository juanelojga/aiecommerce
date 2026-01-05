import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel

from aiecommerce.models.product import ProductMaster

# -------------------------
# AI Response Models
# -------------------------


class BatchNumberUnit(BaseModel):
    value: Optional[float]
    unit: Optional[str]


AttributeRawValue = Union[str, bool, BatchNumberUnit, None]


class AttributeMeta(BaseModel):
    value: AttributeRawValue
    confidence: Literal["high", "medium", "low"]
    source: Literal["product_data", "internet", "unknown"]


class BatchAttributeResponse(BaseModel):
    attributes: Dict[str, AttributeMeta]


# -------------------------
# AI Attribute Filler
# -------------------------


class AIAttributeFiller:
    """
    Batch-fills MercadoLibre attributes using a single AI call.

    - Attribute VALUES are returned in Spanish.
    - Code, comments, and logic are in English.
    - No MercadoLibre API calls here.
    - Enforces MercadoLibre rules locally.
    - Produces ML-ready attribute payloads.
    """

    def __init__(self):
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ.get("OPENAI_BASE_URL"),
            )
        )

    # =========================
    # Public API
    # =========================

    def fill_and_validate(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Returns:
        {
          "attributes": [ML-ready attribute payloads],
          "meta": confidence/source metadata,
          "missing_required": list of attribute IDs
        }
        """

        # 1️⃣ First AI pass
        values, meta = self._fill_attributes_with_meta(product, attributes)

        # 2️⃣ Drop low-confidence conditional_required attributes
        self._drop_low_confidence_required(values, meta, attributes)

        # 3️⃣ Validate conditional_required
        missing_required = self._find_missing_required(values, attributes)

        # 4️⃣ Retry ONLY missing conditional_required attributes
        if missing_required:
            retry_defs = [a for a in attributes if a["id"] in missing_required]

            retry_response = self._extract_batch(
                product,
                retry_defs,
                force_internet_if_missing=True,
            )

            retry_values, retry_meta = self._map_to_internal_values(
                retry_response.attributes,
                retry_defs,
            )

            values.update(retry_values)
            meta.update(retry_meta)

            self._drop_low_confidence_required(values, meta, attributes)
            missing_required = self._find_missing_required(values, attributes)

        # 5️⃣ Build MercadoLibre payload
        ml_payload = self._build_ml_attributes_payload(values, attributes)

        return {
            "attributes": ml_payload,
            "meta": meta,
            "missing_required": missing_required,
        }

    # =========================
    # Core AI Logic
    # =========================

    def _fill_attributes_with_meta(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        candidates = [a for a in attributes if not self._should_skip(a, product.specs)]
        if not candidates:
            return {}, {}

        response = self._extract_batch(product, candidates)
        return self._map_to_internal_values(response.attributes, candidates)

    def _extract_batch(
        self,
        product: ProductMaster,
        attributes: List[dict],
        force_internet_if_missing: bool = False,
    ) -> BatchAttributeResponse:
        prompt = self._build_batch_prompt(product, attributes, force_internet_if_missing)

        return self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_model=BatchAttributeResponse,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in MercadoLibre product catalogs.\n"
                        "Return attribute values in Spanish.\n"
                        "Do not invent information.\n"
                        "If you cannot determine a value with certainty, return null.\n"
                        "Provide confidence and source per attribute."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

    def _build_batch_prompt(
        self,
        product: ProductMaster,
        attributes: List[dict],
        force_internet_if_missing: bool,
    ) -> str:
        internet_rule = "If product info is missing, you MUST search the internet." if force_internet_if_missing else "If product info is missing, you MAY search the internet."

        return f"""
Authoritative product info:
- Description: {product.description}
- Code: {product.code}
- Current specs: {product.specs or {}}

Attributes to fill:
{attributes}

Rules:
- Output JSON strictly matching the response schema.
- Use Spanish for attribute values.
- Use ONLY the product info above if sufficient.
- {internet_rule}
- If still unknown, value must be null.
- Do NOT infer or guess.

confidence:
- high: explicitly present in product info/specs
- medium: found externally with strong evidence
- low: weak evidence (prefer null)

source must be one of:
- product_data
- internet
- unknown

IMPORTANT:
- Attributes with tag "conditional_required" have higher priority.
- If missing, you must search the internet.
- If still unknown, return null.
"""

    # =========================
    # Mapping & Validation
    # =========================

    def _map_to_internal_values(
        self,
        ai_attrs: Dict[str, AttributeMeta],
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Maps AI output to internal semantic values (not ML payload yet).
        """
        values: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}

        attr_map = {a["id"]: a for a in attributes}

        for attr_id, payload in ai_attrs.items():
            attr_def = attr_map.get(attr_id)
            if not attr_def or payload.value is None:
                continue

            meta[attr_id] = {
                "confidence": payload.confidence,
                "source": payload.source,
            }

            vt = attr_def.get("value_type")

            if vt == "boolean":
                values[attr_id] = bool(payload.value)
                continue

            if vt == "list":
                selected = str(payload.value).strip().lower()
                for opt in attr_def.get("values", []):
                    if selected in opt.get("name", "").lower():
                        values[attr_id] = opt["id"]
                        break
                continue

            if vt == "number_unit":
                if not isinstance(payload.value, BatchNumberUnit):
                    continue
                unit = payload.value.unit or attr_def.get("default_unit")
                if payload.value.value is not None and unit:
                    values[attr_id] = {
                        "value": payload.value.value,
                        "unit": unit,
                    }
                continue

            # string
            values[attr_id] = str(payload.value).strip()

        return values, meta

    def _build_ml_attributes_payload(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> List[dict]:
        """
        Builds MercadoLibre-compliant attribute payload.
        """
        result = []
        attr_map = {a["id"]: a for a in attributes}

        for attr_id, value in values.items():
            attr_def = attr_map.get(attr_id)
            if not attr_def:
                continue

            vt = attr_def.get("value_type")

            if vt == "list":
                result.append({"id": attr_id, "value_id": value})
            elif vt == "boolean":
                result.append(
                    {
                        "id": attr_id,
                        "value_id": "242085" if value else "242084",
                    }
                )
            elif vt == "number_unit":
                result.append(
                    {
                        "id": attr_id,
                        "value_name": f"{value['value']} {value['unit']}",
                    }
                )
            else:  # string
                result.append({"id": attr_id, "value_name": value})

        return result

    # =========================
    # Conditional Required Logic
    # =========================

    def _get_conditional_required_ids(self, attributes: List[dict]) -> set[str]:
        return {a["id"] for a in attributes if a.get("tags", {}).get("conditional_required") is True}

    def _find_missing_required(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> List[str]:
        required_ids = self._get_conditional_required_ids(attributes)
        return [aid for aid in required_ids if aid not in values]

    def _drop_low_confidence_required(
        self,
        values: Dict[str, Any],
        meta: Dict[str, Any],
        attributes: List[dict],
    ) -> None:
        required_ids = self._get_conditional_required_ids(attributes)

        for aid in list(values.keys()):
            if aid in required_ids and meta.get(aid, {}).get("confidence") == "low":
                values.pop(aid, None)

    # =========================
    # Skip Rules
    # =========================

    def _should_skip(self, attr: dict, specs: Optional[dict]) -> bool:
        tags = attr.get("tags", {})

        if tags.get("read_only"):
            return True
        if tags.get("fixed"):
            return True
        if tags.get("inferred"):
            return True

        if specs and attr.get("id") in specs and specs[attr["id"]] is not None:
            return True

        return False

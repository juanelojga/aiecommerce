import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel

from aiecommerce.models.product import ProductMaster


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


class AIAttributeFiller:
    """
    Batch-fills MercadoLibre attributes using a single AI call.
    - Attribute values are in Spanish.
    - Code/comments/communication are in English.
    - Adds confidence/source metadata.
    - Supports conditional_required validation via MercadoLibre API.
    """

    def __init__(self, ml_client):
        self.ml_client = ml_client
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ.get("OPENAI_BASE_URL"),
            )
        )

    def fill_attributes_with_meta(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Returns:
          - ml_ready_values: dict of {attr_id: formatted_value_for_ml}
          - meta: dict of {attr_id: {"confidence": ..., "source": ...}}
        """
        candidates = [a for a in attributes if not self._should_skip(a, product.specs)]
        if not candidates:
            return {}, {}

        response = self._extract_batch(product, candidates)

        ml_values, meta = self._map_to_ml_format_with_meta(response.attributes, candidates)

        return ml_values, meta

    def fill_and_validate_conditionals(
        self,
        product: ProductMaster,
        attributes: List[dict],
        category_id: str,
        base_item_payload: dict,
        retry_missing_required: bool = True,
    ) -> Dict[str, Any]:
        """
        Fills attributes, then checks MercadoLibre conditional_required rules.
        Optionally retries AI once for missing required attributes.
        Returns a report dict.
        """
        ml_values, meta = self.fill_attributes_with_meta(product, attributes)

        # Merge into item payload for conditional validation
        item_payload = dict(base_item_payload)
        item_payload["attributes"] = self._build_ml_attributes_payload(ml_values, attributes)

        required_ids = self.ml_client.get_conditional_required_attributes(
            category_id=category_id,
            item_payload=item_payload,
        )

        missing_required = [rid for rid in required_ids if rid not in ml_values]

        # Retry strategy: ask AI to focus only on missing required attributes
        if retry_missing_required and missing_required:
            missing_defs = [a for a in attributes if a.get("id") in missing_required]
            if missing_defs:
                retry_response = self._extract_batch(
                    product,
                    missing_defs,
                    force_internet_if_missing=True,
                )
                retry_values, retry_meta = self._map_to_ml_format_with_meta(
                    retry_response.attributes,
                    missing_defs,
                )

                ml_values.update(retry_values)
                meta.update(retry_meta)

                # Re-check
                missing_required = [rid for rid in required_ids if rid not in ml_values]

        return {
            "values": ml_values,
            "meta": meta,
            "required_ids": required_ids,
            "missing_required": missing_required,
        }

    def fill_and_validate(
        self,
        product: ProductMaster,
        attributes: list[dict],
    ) -> dict:
        """
        Main entry point.

        Returns:
          {
            "values": ML-ready attribute values,
            "meta": confidence/source per attribute,
            "missing_required": list of attribute IDs
          }
        """

        # First AI pass (normal rules)
        values, meta = self.fill_attributes_with_meta(product, attributes)

        missing_required = self._find_missing_required(values, attributes)

        # Retry ONLY for missing conditional_required attributes
        if missing_required:
            retry_defs = [a for a in attributes if a["id"] in missing_required]

            retry_response = self._extract_batch(
                product,
                retry_defs,
                force_internet_if_missing=True,
            )

            retry_values, retry_meta = self._map_to_ml_format_with_meta(
                retry_response.attributes,
                retry_defs,
            )

            values.update(retry_values)
            meta.update(retry_meta)

            missing_required = self._find_missing_required(values, attributes)

        return {
            "values": values,
            "meta": meta,
            "missing_required": missing_required,
        }

    # -------------------------
    # Internal helpers
    # -------------------------

    def _drop_low_confidence_required(
        self,
        values: dict[str, Any],
        meta: dict[str, Any],
        attributes: list[dict],
    ):
        required_ids = self._get_conditional_required_ids(attributes)

        for attr_id in list(values.keys()):
            if attr_id in required_ids:
                if meta.get(attr_id, {}).get("confidence") == "low":
                    values.pop(attr_id, None)

    def _get_conditional_required_ids(self, attributes: list[dict]) -> set[str]:
        return {attr["id"] for attr in attributes if attr.get("tags", {}).get("conditional_required") is True}

    def _find_missing_required(
        self,
        filled_values: dict[str, Any],
        attributes: list[dict],
    ) -> list[str]:
        required_ids = self._get_conditional_required_ids(attributes)
        return [attr_id for attr_id in required_ids if attr_id not in filled_values]

    def _should_skip(self, attr: dict, specs: Optional[dict]) -> bool:
        tags = attr.get("tags", {})

        # MercadoLibre tags
        if tags.get("read_only"):
            return True
        if tags.get("fixed"):
            return True
        if tags.get("inferred"):
            return True

        # If already filled in your internal specs, skip
        if specs and attr.get("id") in specs and specs[attr["id"]] is not None:
            return True

        return False

    def _extract_batch(
        self,
        product: ProductMaster,
        attributes: List[dict],
        force_internet_if_missing: bool = False,
    ):
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
                        "Provide confidence and source per attribute.\n"
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
- Output must be JSON matching the response schema.
- Use Spanish for attribute values.
- Use ONLY the product info above if sufficient.
- {internet_rule}
- If still unknown, value must be null.
- Do NOT infer or guess.
- confidence:
  - high: explicitly present in product info/specs
  - medium: found externally (internet) or strong explicit evidence
  - low: weak evidence (prefer null)
- source must be one of: product_data, internet, unknown

IMPORTANT:
- Attributes marked as "conditional_required" have higher priority.
- If they are missing from product data, you must search the internet.
- If still unknown, return null (do not guess).
"""

    def _map_to_ml_format_with_meta(
        self,
        ai_attrs: Dict[str, Any],
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Converts AI outputs into ML-ready values + a meta dict.
        """
        ml_values: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}

        attr_map = {a["id"]: a for a in attributes}

        for attr_id, payload in ai_attrs.items():
            attr_def = attr_map.get(attr_id)
            if not attr_def:
                continue

            # payload is AttributeMeta
            if payload.value is None:
                continue

            # Record meta even if mapping fails (optional)
            meta[attr_id] = {
                "confidence": payload.confidence,
                "source": payload.source,
            }

            vt = attr_def.get("value_type")

            if vt == "boolean":
                ml_values[attr_id] = "242085" if payload.value else "242084"
                continue

            if vt == "list":
                selected_name = str(payload.value).strip().lower()
                matched_id = None
                for option in attr_def.get("values", []):
                    if option.get("name", "").strip().lower() == selected_name:
                        matched_id = option.get("id")
                        break
                if matched_id:
                    ml_values[attr_id] = matched_id
                continue

            if vt == "number_unit":
                # payload.value is BatchNumberUnit
                val = payload.value.value
                unit = payload.value.unit
                allowed = {u["name"] for u in attr_def.get("allowed_units", [])}
                if val is not None and unit and (not allowed or unit in allowed):
                    ml_values[attr_id] = f"{val} {unit}"
                continue

            # string
            ml_values[attr_id] = str(payload.value).strip()

        return ml_values, meta

    def _build_ml_attributes_payload(self, ml_values: Dict[str, Any], attributes: List[dict]) -> List[dict]:
        """
        Builds MercadoLibre 'attributes' list payload from the dict values.
        Adjust this depending on the ML endpoint expectations in your publisher.
        """
        result = []
        for attr in attributes:
            attr_id = attr.get("id")
            if attr_id not in ml_values:
                continue
            result.append({"id": attr_id, "value_id": ml_values[attr_id]})
        return result

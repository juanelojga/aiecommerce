import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from aiecommerce.models.product import ProductMaster

# -------------------------
# AI Response Models
# -------------------------


class BatchNumberUnit(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None


AttributeRawValue = Union[str, bool, BatchNumberUnit, None]


class AttributeMeta(BaseModel):
    value: AttributeRawValue = None
    confidence: Literal["high", "medium", "low"]
    source: Literal["product_data", "internet", "unknown"]


class BatchAttributeResponse(BaseModel):
    attributes: Dict[str, AttributeMeta] = Field(default_factory=dict)


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

    def __init__(self) -> None:
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],
                base_url=os.environ.get("OPENROUTER_BASE_URL"),
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

        # 0️⃣ Seed from existing product specs (so we always return partial results)
        values, meta = self._seed_from_specs(product, attributes)

        # 1️⃣ First AI pass (only for attributes that are not already known)
        ai_values, ai_meta = self._fill_attributes_with_meta(product, attributes)
        values.update(ai_values)
        meta.update(ai_meta)

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

        # Enforce GTIN rules
        self._enforce_gtin_rules(values, attributes)

        # Build MercadoLibre payload
        ml_payload = self._build_ml_attributes_payload(values, attributes)

        return {
            "attributes": ml_payload,
            "meta": meta,
            "missing_required": missing_required,
        }

    # =========================
    # Helpers: tags/specs
    # =========================

    def _has_tag(self, attr: dict, tag: str) -> bool:
        tags = attr.get("tags")
        if isinstance(tags, list):
            return tag in tags
        if isinstance(tags, dict):
            return tags.get(tag) is True
        return False

    def _seed_from_specs(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Pre-populates values/meta from ProductMaster.specs so we return partial results
        even if the AI can't confidently fill anything.
        """
        values: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}

        specs = product.specs or {}
        if not isinstance(specs, dict):
            return values, meta

        # Common mapping between internal spec keys and MercadoLibre attribute IDs
        mapping = {
            "BRAND": ["manufacturer", "brand", "marca"],
            "MODEL": ["model_name", "model", "modelo"],
            "GTIN": ["gtin", "upc", "ean", "barcode", "part_number"],
        }

        for attr in attributes:
            attr_id = attr.get("id")
            if not attr_id:
                continue

            if self._should_skip(attr):
                continue

            # 1. Direct match
            val = specs.get(attr_id)

            # 2. Mapped match
            if val is None and attr_id in mapping:
                for alt_key in mapping[attr_id]:
                    if alt_key in specs and specs[alt_key] is not None:
                        val = specs[alt_key]
                        break

            if val is not None:
                values[attr_id] = val
                meta[attr_id] = {"confidence": "high", "source": "product_data"}

        return values, meta

    # =========================
    # Core AI Logic
    # =========================

    def _fill_attributes_with_meta(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        specs = product.specs or {}
        candidates = [a for a in attributes if not self._should_skip(a) and not (isinstance(specs, dict) and a.get("id") in specs and specs[a["id"]] is not None)]
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
        internet_rule = "If product info is missing, you MUST search the internet." if force_internet_if_missing or self._has_gtin(attributes) else "If product info is missing, you MAY search the internet."

        simplified_attrs = []
        for a in attributes:
            simplified = {
                "id": a["id"],
                "name": a.get("name"),
                "value_type": a.get("value_type"),
            }
            if a.get("values"):
                allowed = [v.get("name") for v in a["values"] if v.get("name")]
                if allowed:
                    simplified["allowed_values"] = allowed[:15]
            simplified_attrs.append(simplified)

        gtin_instructions = ""
        if self._has_gtin(attributes):
            gtin_instructions = """
SPECIAL RULES FOR GTIN (CRITICAL):

You are identifying the official GTIN (UPC / EAN / GTIN-14) for a real, existing product.

Authoritative product data (this is your primary source of truth):
- Product description
- Internal product code / SKU
- Structured product specifications (such as brand, model, storage, color, connectivity, size, etc.)

You MUST start from this product data and treat it as correct.

What GTIN is:
- A GTIN is a globally standardized barcode identifier (EAN-13, UPC-A, EAN-8, or GTIN-14).
- It is assigned by the manufacturer and published in authoritative product catalogs.
- GTINs uniquely identify exact product variants (model, capacity, color, connectivity, region).

Your task:
- Use the provided product data to identify the exact real-world product variant.
- Search external sources ONLY to discover the official manufacturer-assigned GTIN(s).
- Be conservative and precise. It is better to return null than an incorrect GTIN.

Search strategy (mandatory):
1. Use the following product data as search keys:
   - Brand / manufacturer
   - Model name
   - Variant details (storage, connectivity, color, size, etc.)
   - Internal product code, part number, or SKU if available
2. Search authoritative and reliable sources such as:
   - Official manufacturer product pages
   - Manufacturer datasheets or specification PDFs
   - GS1 / barcode lookup databases
   - Large, trusted ecommerce catalogs (major retailers or distributors)
3. Cross-check multiple sources whenever possible.

Validation rules:
- A GTIN must:
  - Contain ONLY digits
  - Have a length between 8 and 14 digits
- ONLY return a GTIN if:
  - The same code appears consistently across reliable sources
  - The code clearly matches the exact product variant described by the product data

Multiple GTINs:
- If multiple valid GTINs exist (e.g. regional or packaging variants):
  - You may return more than one
  - Prefer the GTIN that best matches the described variant
  - Prefer region-appropriate or international variants when applicable

Failure handling:
- If no GTIN can be determined with high confidence:
  - Set the GTIN value to null
  - Do NOT invent, guess, or reuse internal product codes as GTINs
  - The product may legitimately require an EMPTY_GTIN_REASON instead
    """

        return f"""
    Authoritative product info:
    - Description: {product.description}
    - Code: {product.code}
    - Current specs: {product.specs or {}}

    Attributes to fill:
    {json.dumps(simplified_attrs, indent=2, ensure_ascii=False)}

    Rules:
    - Output JSON strictly matching the response schema.
    - For value_type 'list', use one of the names from 'allowed_values' if provided.
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

    {gtin_instructions}
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

    def _find_missing_required(self, values: Dict[str, Any], attributes: List[dict]) -> List[str]:
        required_ids = self._get_conditional_required_ids(attributes)
        return [attr_id for attr_id in required_ids if attr_id not in values]

    def _drop_low_confidence_required(
        self,
        values: Dict[str, Any],
        meta: Dict[str, Any],
        attributes: List[dict],
    ) -> None:
        """
        Drops 'conditional_required' attributes that have low confidence,
        so they can be retried in the next step.

        NOTE: Per user requirement 'do not discard values', we are currently
        disabling the dropping logic to keep all AI-generated values.
        """
        # required_ids = self._get_conditional_required_ids(attributes)
        # for attr_id in required_ids:
        #     if attr_id in meta and meta[attr_id].get("confidence") == "low":
        #         values.pop(attr_id, None)
        #         meta.pop(attr_id, None)
        pass

    def _get_conditional_required_ids(self, attributes: List[dict]) -> set[str]:
        return {a["id"] for a in attributes if self._has_tag(a, "conditional_required")}

    # =========================
    # Skip Rules
    # =========================

    def _should_skip(self, attr: dict) -> bool:
        if self._has_tag(attr, "read_only"):
            return True
        if self._has_tag(attr, "fixed"):
            return True
        if self._has_tag(attr, "inferred"):
            return True
        return False

    def _has_gtin(self, attributes: List[dict]) -> bool:
        return any(a.get("id") == "GTIN" for a in attributes)

    def _enforce_gtin_rules(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> None:
        has_gtin = any(a["id"] == "GTIN" for a in attributes)
        has_empty_reason = any(a["id"] == "EMPTY_GTIN_REASON" for a in attributes)

        if not has_gtin:
            return

        gtin = values.get("GTIN")

        if gtin and self._is_valid_gtin(str(gtin)):
            return  # valid GTIN found

        # GTIN missing or invalid → remove it
        values.pop("GTIN", None)

        # Apply MercadoLibre fallback
        if has_empty_reason:
            # "El producto no tiene código registrado"
            values["EMPTY_GTIN_REASON"] = "17055160"

    def _is_valid_gtin(self, value: str) -> bool:
        return value.isdigit() and 8 <= len(value) <= 14

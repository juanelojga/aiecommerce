import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from aiecommerce.models.product import ProductMaster

# ============================================================
# AI RESPONSE MODELS
# ============================================================


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


class GTINResponse(BaseModel):
    gtin: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    source: Literal["product_data", "internet", "unknown"]


# ============================================================
# AI ATTRIBUTE FILLER
# ============================================================


class AIAttributeFiller:
    """
    Batch-fills MercadoLibre attributes using AI.

    - Non-GTIN attributes are filled in a single batch AI call
    - GTIN is resolved via a dedicated AI call
    - Attribute VALUES are returned in Spanish
    - Code, comments, and logic are in English
    - No MercadoLibre API calls here
    - Enforces MercadoLibre rules locally
    - Produces ML-ready attribute payloads
    """

    def __init__(self) -> None:
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],
                base_url=os.environ.get("OPENROUTER_BASE_URL"),
            )
        )

    # ============================================================
    # PUBLIC API
    # ============================================================

    def fill_and_validate(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Returns:
        {
          "attributes": [MercadoLibre-ready attribute payloads],
          "meta": confidence/source metadata,
          "missing_required": list of attribute IDs
        }
        """

        # 0️⃣ Seed from existing product specs
        values, meta = self._seed_from_specs(product, attributes)

        # 1️⃣ Fill non-GTIN attributes via batch AI
        ai_values, ai_meta = self._fill_attributes_with_meta(product, attributes)
        values.update(ai_values)
        meta.update(ai_meta)

        # 2️⃣ Validate conditional_required
        missing_required = self._find_missing_required(values, attributes)

        # 3️⃣ Retry ONLY missing conditional_required (non-GTIN)
        if missing_required:
            retry_defs = [a for a in attributes if a["id"] in missing_required and a["id"] != "GTIN"]

            if retry_defs:
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

        # 4️⃣ Dedicated GTIN resolution
        if self._has_gtin(attributes) and "GTIN" not in values:
            gtin_response = self._extract_gtin(product)

            print(f"GTIN response: {gtin_response}")

            if gtin_response and gtin_response.gtin and self._is_valid_gtin(gtin_response.gtin):
                values["GTIN"] = gtin_response.gtin
                meta["GTIN"] = {
                    "confidence": gtin_response.confidence,
                    "source": gtin_response.source,
                }

        # 5️⃣ Enforce GTIN fallback rules
        self._enforce_gtin_rules(values, attributes)

        # 6️⃣ Build MercadoLibre payload
        ml_payload = self._build_ml_attributes_payload(values, attributes)

        # 7️⃣ Final required validation
        missing_required = self._find_missing_required(values, attributes)

        return {
            "attributes": ml_payload,
            "meta": meta,
            "missing_required": missing_required,
        }

    # ============================================================
    # SEEDING FROM PRODUCT DATA
    # ============================================================

    def _seed_from_specs(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        values: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}

        specs = product.specs or {}
        if not isinstance(specs, dict):
            return values, meta

        mapping = {
            "BRAND": ["manufacturer", "brand", "marca"],
            "MODEL": ["model_name", "model", "modelo"],
            "GTIN": ["gtin", "ean", "upc", "barcode"],
        }

        for attr in attributes:
            attr_id = attr.get("id")
            if not attr_id or self._should_skip(attr):
                continue

            val = specs.get(attr_id)

            if val is None and attr_id in mapping:
                for alt in mapping[attr_id]:
                    if alt in specs and specs[alt] is not None:
                        val = specs[alt]
                        break

            if val is not None:
                values[attr_id] = val
                meta[attr_id] = {
                    "confidence": "high",
                    "source": "product_data",
                }

        return values, meta

    # ============================================================
    # BATCH ATTRIBUTE AI (NON-GTIN)
    # ============================================================

    def _fill_attributes_with_meta(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        specs = product.specs or {}

        candidates = [a for a in attributes if a.get("id") != "GTIN" and not self._should_skip(a) and not (isinstance(specs, dict) and a.get("id") in specs and specs[a["id"]] is not None)]

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
            model=os.environ.get("OPENROUTER_TITLE_GENERATION_MODEL"),
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

        simplified_attrs = []
        for a in attributes:
            simplified = {
                "id": a["id"],
                "name": a.get("name"),
                "value_type": a.get("value_type"),
            }
            if a.get("values"):
                allowed = [v["name"] for v in a["values"] if v.get("name")]
                if allowed:
                    simplified["allowed_values"] = allowed[:15]
            simplified_attrs.append(simplified)

        return f"""
Authoritative product info:
- Description: {product.description}
- Code: {product.code}
- Current specs: {product.specs or {}}

Attributes to fill:
{json.dumps(simplified_attrs, indent=2, ensure_ascii=False)}

Rules:
- Output JSON strictly matching the response schema.
- Use Spanish for attribute values.
- {internet_rule}
- If still unknown, value must be null.
- Do NOT infer or guess.
"""

    # ============================================================
    # GTIN DEDICATED AI
    # ============================================================

    def _extract_gtin(self, product: ProductMaster) -> Optional[GTINResponse]:
        prompt = self._build_gtin_prompt(product)

        print(f"GTIN prompt: {prompt}")

        return self.client.chat.completions.create(
            model=os.environ.get("OPENROUTER_TITLE_GENERATION_MODEL"),
            temperature=0,
            response_model=GTINResponse,
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
You are an assistant specialized in identifying official GTIN codes
(UPC, EAN-13, EAN-8, GTIN-14) for real, existing consumer electronics products.

Your role:
- Identify the exact commercial product variant described by the input data.
- Search authoritative external sources to find the manufacturer-assigned GTIN.
- Be conservative and precise.

Critical rules:
- NEVER invent, guess, or fabricate GTINs.
- NEVER reuse internal SKUs or part numbers as GTINs.
- If a GTIN cannot be verified with confidence, return "gtin_not_found".
- It is better to return no GTIN than an incorrect one.

A valid GTIN:
- Contains ONLY digits
- Has a length between 8 and 14 digits
- Appears consistently in reliable, authoritative sources
                        """
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

    def _build_gtin_prompt(self, product: ProductMaster) -> str:
        specs = product.specs or {}
        if not isinstance(specs, dict):
            specs = {}

        return f"""
You must find the correct GTIN (UPC / EAN / GTIN-14) for ONE exact product configuration.

────────────────────────
PRODUCT FACTS (AUTHORITATIVE)
────────────────────────

All fields below refer to the SAME product variant.

Category: {specs.get("category_type", "N/A")}
Brand / Manufacturer: {specs.get("manufacturer", "N/A")}
Model name (marketing): {specs.get("model_name", "N/A")}
Product family / line (if available): {specs.get("product_line", "N/A")}
Processor / CPU: {specs.get("cpu", "N/A")}
RAM: {specs.get("ram", "N/A")}
Storage: {specs.get("storage", "N/A")}
Screen size: {specs.get("screen_size", "N/A")}
Color: {specs.get("color", "N/A")}
Operating system: {specs.get("os", "N/A")}
Connectivity / network: {specs.get("network", "N/A")}
Ports / notable features: {specs.get("features", "N/A")}

Internal product code / SKU (NOT a GTIN):
- product.code: {product.code}
- part_number (if present): {specs.get("part_number", "N/A")}

Full commercial description:
"{product.description}"

────────────────────────
TASK
────────────────────────

1. Use the product facts above to precisely identify the real-world commercial product.
2. Search authoritative external sources to find the official GTIN assigned by the manufacturer.

You MUST prioritize:
- Official manufacturer product pages
- Manufacturer datasheets or PDFs
- GS1 / barcode lookup databases
- Large, well-known retailer or distributor catalogs

Search strategy (mandatory):
- Combine brand + model + key variant attributes (RAM, storage, size, color, OS).
- Use internal codes or part numbers ONLY as search keys, never as GTINs.
- Cross-check multiple sources whenever possible.

────────────────────────
VALIDATION RULES
────────────────────────

You may return a GTIN ONLY if:
- It contains only digits
- Length is between 8 and 14 digits
- It clearly matches the exact product variant
- It appears consistently in at least one reliable source

Multiple GTINs:
- If multiple GTINs exist (regional variants, packaging, keyboard layout):
  - List each GTIN
  - Explain the difference briefly

Failure handling:
- If no reliable GTIN can be confirmed:
  - Do NOT guess
  - Do NOT invent
  - Return status "gtin_not_found"

────────────────────────
OUTPUT FORMAT (JSON ONLY)
────────────────────────

{{
  "status": "ok" | "gtin_not_found",
  "product_match_notes": "short explanation of how close the match is",
  "gtins": [
    {{
      "code": "string",
      "format": "EAN-13 | UPC-A | GTIN-14 | other",
      "region": "string or null",
      "main_source": "short source description",
      "url": "source URL if available"
    }}
  ],
  "warnings": ["array of strings with any doubts or caveats"]
}}
"""

    # ============================================================
    # MAPPING & PAYLOAD
    # ============================================================

    def _map_to_internal_values(
        self,
        ai_attrs: Dict[str, AttributeMeta],
        attributes: List[dict],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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
            elif vt == "list":
                selected = str(payload.value).lower()
                for opt in attr_def.get("values", []):
                    if selected in opt.get("name", "").lower():
                        values[attr_id] = opt["id"]
                        break
            elif vt == "number_unit":
                if isinstance(payload.value, BatchNumberUnit):
                    unit = payload.value.unit or attr_def.get("default_unit")
                    if payload.value.value is not None and unit:
                        values[attr_id] = {
                            "value": payload.value.value,
                            "unit": unit,
                        }
            else:
                values[attr_id] = str(payload.value).strip()

        return values, meta

    def _build_ml_attributes_payload(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> List[dict]:
        payload = []
        attr_map = {a["id"]: a for a in attributes}

        for attr_id, value in values.items():
            attr_def = attr_map.get(attr_id)
            if not attr_def:
                continue

            vt = attr_def.get("value_type")

            if vt == "list":
                payload.append({"id": attr_id, "value_id": value})
            elif vt == "boolean":
                payload.append({"id": attr_id, "value_id": "242085" if value else "242084"})
            elif vt == "number_unit":
                payload.append({"id": attr_id, "value_name": f"{value['value']} {value['unit']}"})
            else:
                payload.append({"id": attr_id, "value_name": value})

        return payload

    # ============================================================
    # VALIDATION & RULES
    # ============================================================

    def _has_gtin(self, attributes: List[dict]) -> bool:
        return any(a.get("id") == "GTIN" for a in attributes)

    def _enforce_gtin_rules(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> None:
        if "GTIN" not in values:
            has_empty_reason = any(a["id"] == "EMPTY_GTIN_REASON" for a in attributes)
            if has_empty_reason:
                values["EMPTY_GTIN_REASON"] = "17055160"
            return

        if not self._is_valid_gtin(str(values["GTIN"])):
            values.pop("GTIN", None)
            if any(a["id"] == "EMPTY_GTIN_REASON" for a in attributes):
                values["EMPTY_GTIN_REASON"] = "17055160"

    def _is_valid_gtin(self, value: str) -> bool:
        return value.isdigit() and 8 <= len(value) <= 14

    def _find_missing_required(
        self,
        values: Dict[str, Any],
        attributes: List[dict],
    ) -> List[str]:
        required_ids = {a["id"] for a in attributes if self._has_tag(a, "conditional_required")}
        return [rid for rid in required_ids if rid not in values]

    def _has_tag(self, attr: dict, tag: str) -> bool:
        tags = attr.get("tags")
        if isinstance(tags, dict):
            return tags.get(tag) is True
        if isinstance(tags, list):
            return tag in tags
        return False

    def _should_skip(self, attr: dict) -> bool:
        return self._has_tag(attr, "read_only") or self._has_tag(attr, "fixed") or self._has_tag(attr, "inferred")

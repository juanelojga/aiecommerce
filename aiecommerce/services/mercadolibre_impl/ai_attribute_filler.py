import json
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.google_search_client import GoogleSearchClient

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


class GTINEntry(BaseModel):
    code: str = Field(description="The numeric GTIN/EAN/UPC code")
    format: str = Field(description="EAN-13, UPC-A, etc.")
    region: Optional[str] = Field(default=None, description="Region if applicable (e.g., 'USA', 'LATAM')")
    main_source: str = Field(description="Primary source of this GTIN, e.g., 'Manufacturer Website'")
    url: Optional[str] = Field(default=None, description="URL of the source")


class GTINResponse(BaseModel):
    status: Literal["ok", "gtin_not_found"]
    product_match_notes: str = Field(description="Notes on how well the found product matches the requested one.")
    gtins: List[GTINEntry] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================
# AI ATTRIBUTE FILLER
# ============================================================


class AIAttributeFiller:
    """
    Batch-fills MercadoLibre attributes using AI.

    - Non-GTIN attributes are filled in a single batch AI call
    - GTIN is resolved via a dedicated AI call with search integration
    - Attribute VALUES are returned in Spanish
    - Code, comments, and logic are in English
    - No MercadoLibre API calls here
    - Enforces MercadoLibre rules locally
    - Produces ML-ready attribute payloads
    """

    def __init__(self, search_client: Optional[GoogleSearchClient] = None) -> None:
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],
                base_url=os.environ.get("OPENROUTER_BASE_URL"),
            )
        )
        self.search_client = search_client

    def _get_clean_mpn(self, code: str) -> str:
        """Strips common internal prefixes to extract the core logistic part number."""
        # This regex looks for a common pattern of 3-6 uppercase letters often used as internal prefixes.
        # e.g. COMHPXBS6H5LT -> BS6H5LT
        match = re.match(r"^[A-Z]{3,6}([A-Z0-9-]{3,})", code)
        if match:
            # Return the second group, which is the supposed MPN
            return match.group(1)
        return code

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

            if gtin_response and gtin_response.status == "ok" and gtin_response.gtins:
                # For now, we take the first valid GTIN. Logic can be expanded here.
                first_gtin = gtin_response.gtins[0]
                if self._is_valid_gtin(first_gtin.code):
                    values["GTIN"] = first_gtin.code
                    meta["GTIN"] = {
                        "confidence": "high",  # Confidence is based on successful verification
                        "source": "internet",
                        "match_notes": gtin_response.product_match_notes,
                        "tecnomega_product_details_fetcher_impl": first_gtin.model_dump(),
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
        """
        Extracts GTIN using a "Search -> Candidate Selection -> Verification" flow.
        """
        search_snippets = ""
        if self.search_client:
            specs = product.specs or {}
            brand = specs.get("brand", "") or specs.get("manufacturer", "")
            clean_mpn = self._get_clean_mpn(product.code) if product.code else ""

            query_parts = [
                brand,
                clean_mpn,
                specs.get("model_name", ""),
                specs.get("cpu", ""),
                specs.get("ram", ""),
                specs.get("storage", ""),
                "GTIN",
                "EAN",
            ]
            query = " ".join(filter(None, query_parts))

            print(f"Performing search with query: {query}")
            try:
                search_results = self.search_client.list(q=query, num=5).execute()
                items = search_results.get("items", [])
                if items:
                    search_snippets = "\n\n".join(f"Source: {item.get('link')}\nSnippet: {item.get('snippet')}" for item in items)
            except Exception as e:
                print(f"Error during Google Search: {e}")
                # Continue without search results if the API fails

        prompt = self._build_gtin_prompt(product, search_snippets)

        try:
            return self.client.chat.completions.create(
                model=os.environ.get("OPENROUTER_TITLE_GENERATION_MODEL", "anthropic/claude-3.5-sonnet"),
                temperature=0,
                response_model=GTINResponse,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert system for identifying official manufacturer-assigned GTINs (EAN/UPC) for electronics. "
                            "Your primary goal is accuracy. It is better to return 'gtin_not_found' than an incorrect GTIN."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as e:
            print(f"Error calling AI model for GTIN extraction: {e}")
            return None

    def _build_gtin_prompt(self, product: ProductMaster, search_snippets: str = "") -> str:
        specs = product.specs or {}
        if not isinstance(specs, dict):
            specs = {}

        clean_mpn = self._get_clean_mpn(product.code) if product.code else ""

        web_context_section = ""
        if search_snippets:
            web_context_section = f"""
# Step 2: Analyze Web Search Results

Review these external search snippets for candidate GTINs.
Cross-reference them with the authoritative product facts.

---
{search_snippets}
---"""

        return f"""
Your task is to find the correct GTIN (UPC/EAN) for a specific electronics product. Follow this multi-step process precisely.

# Step 1: Understand the Authoritative Product Data

This is the ground truth for the product variant you must match.

- **Brand**: {specs.get("brand", "N/A")}
- **Model**: {specs.get("model", "N/A")}
- **Internal SKU / Code (NOT a GTIN)**: {product.code}
- **Cleaned MPN (for searching)**: {clean_mpn}
- **Description**: {product.description}
- **Key Specifications**:
    - **CPU**: {specs.get("cpu", "N/A")}
    - **RAM**: {specs.get("ram", "N/A")}
    - **Storage**: {specs.get("storage", "N/A")}
- **Regional Indicators**:
    - Look for clues like keyboard language (e.g., Spanish, #ABM), power plug type, or regional suffixes in part numbers.

{web_context_section}

# Step 3: Verification and Selection

1.  **Candidate Selection**: Identify potential GTINs from the web search context.
- **Strict Verification**: A candidate GTIN is valid ONLY IF it EXACTLY
  matches the product's key specifications (CPU, RAM, Storage).
  Also, consider regional indicators. For example, a GTIN for a US
  keyboard layout is incorrect for a product specified with a Latin
  American layout.
3.  **Regional Handling**: If you find multiple GTINs for different regions (e.g., USA `#ABA` vs. LATAM `#ABM`), list each one and specify its region.

# Step 4: Final Output

- **CRITICAL RULE**: NEVER use the internal SKU (`{product.code}`) or cleaned MPN (`{clean_mpn}`) as a GTIN. They are for searching only.
- If you find a verified GTIN that matches all criteria, set status to "ok".
- If no GTIN can be reliably verified against the specs, you MUST set status to "gtin_not_found".
- Provide notes on your matching process in `product_match_notes`.
- List any uncertainties in the `warnings` array.

Produce only a valid JSON object matching the response model.
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
                if isinstance(value, dict):
                    payload.append({"id": attr_id, "value_name": f"{value.get('value')} {value.get('unit')}"})
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
                values["EMPTY_GTIN_REASON"] = "17055160"  # "El producto no tiene código GTIN"
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

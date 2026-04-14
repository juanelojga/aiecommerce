from typing import Any, Dict, List, Optional

import instructor
from django.conf import settings
from pydantic import BaseModel, Field

from aiecommerce.models.product import ProductMaster


class MLAttributeValue(BaseModel):
    """
    Represents a single filled attribute for Mercado Libre.
    """

    id: str = Field(..., description="The attribute ID, e.g., 'BRAND' or 'MODEL'")
    value_name: Optional[str] = Field(None, description="The human-readable name of the value. MUST BE IN SPANISH.")
    value_id: Optional[str] = Field(None, description="The specific ID from the 'values' list if a match is found.")


class MercadolibreAttributeResponse(BaseModel):
    """
    The collection of attributes extracted by the AI.
    """

    attributes: List[MLAttributeValue]


class MercadolibreAIAttributeFiller:
    def __init__(self, client: instructor.Instructor) -> None:
        self.client = client

    def fill_and_validate(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> List[Dict[str, Any]]:
        """
        Uses instructor to map ProductMaster data to ML category attributes.
        Returns a list of dictionaries compatible with the Mercado Libre API.
        """

        # Consolidation of product data for context, utilizing already validated GTIN
        product_context = {
            "name": product.normalized_name or product.description,
            "specs": product.specs,
            "gtin": product.gtin,  # GTIN is already validated
            "seo_description": product.seo_description,
            "model_name": product.model_name,
        }

        # Filtering to relevant attributes to optimize prompt size
        relevant_defs = [attr for attr in attributes if attr.get("tags", {}).get("required") or attr.get("relevance") == 1]

        response = self.client.chat.completions.create(
            model=settings.OPENROUTER_MERCADOLIBRE_ATTRIBUTE_FILLER_MODEL,
            response_model=MercadolibreAttributeResponse,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at mapping product data to Mercado Libre's technical attributes.\n"
                        "CRITICAL RULES:\n"
                        "1. ALL returned 'value_name' MUST BE IN SPANISH.\n"
                        "2. MAP SPECIFIC FIELDS: Use 'gtin' for GTIN/EAN/UPC attributes, 'brand' for BRAND/MARCA, and 'model_name' for MODEL/MODELO.\n"
                        "3. UNIT FORMATTING: For numeric attributes like 'DISPLAY_SIZE', 'SCREEN_SIZE', or 'MEM_CAPACITY', extract the number and use the standard symbol.\n"
                        "   - For inches, ALWAYS use the double quote symbol (e.g., '65\"') instead of 'inch', 'pulgadas', or 'in'.\n"
                        "4. VALUES LIST: If an attribute definition contains a non-empty 'values' list, you MUST select the exact 'id' and 'name' from that list. "
                        "The 'value_name' MUST come from the chosen entry's 'name' field — never invent free-text when a catalog list is provided.\n"
                        "5. MODEL ATTRIBUTE (STRICT): For the 'MODEL' attribute specifically, only include it when the product's model matches an entry in the 'values' list "
                        "(emit both value_id and value_name from that entry). If the 'values' list is empty or no entry matches, OMIT the MODEL attribute entirely. "
                        "Do NOT emit free-text for MODEL — Mercado Libre will reject unresolvable model strings. "
                        "Never emit internal SKU codes, distributor part numbers, or product code fragments as the MODEL value_name.\n"
                        "6. GTIN (STRICT): Only include a GTIN attribute if 'gtin' is exactly 13 numeric digits. If the provided 'gtin' is shorter, longer, non-numeric, "
                        "or looks like an internal/distributor code, OMIT the GTIN attribute entirely.\n"
                        "7. REQUIRED COVERAGE: For every attribute in the definitions whose 'tags.required' is true, emit an entry. If data is thin, use the best-available "
                        "value derived from 'name'/'specs' rather than omitting a required attribute. Only omit a required attribute if there is truly no information available.\n"
                        "8. DATA INTEGRITY: Do not invent data. If a value is genuinely missing from all source data (specs, name, model), omit the attribute — "
                        "with the exception of rule 7 for required attributes."
                    ),
                },
                {"role": "user", "content": f"Product Data: {product_context}\n\nAttribute Definitions: {relevant_defs}"},
            ],
        )

        # Formats the response into the dictionary list expected by the orchestrator
        return [attr.model_dump(exclude_none=True) for attr in response.attributes]

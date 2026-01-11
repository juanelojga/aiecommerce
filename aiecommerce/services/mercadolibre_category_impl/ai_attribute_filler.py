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
                        "1. ALL returned values (value_name) MUST BE IN SPANISH.\n"
                        "2. Use the provided Product Data to fill the Attribute Definitions.\n"
                        "3. If an attribute has a 'values' list, you MUST use the exact 'id' and 'name' from that list if it matches.\n"
                        "4. The GTIN is already validated; ensure it is mapped to the correct GTIN attribute ID if required.\n"
                        "5. If a value is not found in the source data, do not invent it; simply omit the attribute."
                    ),
                },
                {"role": "user", "content": f"Product Data: {product_context}\n\nAttribute Definitions: {relevant_defs}"},
            ],
        )

        # Formats the response into the dictionary list expected by the orchestrator
        return [attr.model_dump(exclude_none=True) for attr in response.attributes]

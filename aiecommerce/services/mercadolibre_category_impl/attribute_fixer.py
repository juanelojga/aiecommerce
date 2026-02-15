from typing import Any, Dict, List

import instructor
from django.conf import settings
from pydantic import BaseModel

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_category_impl.ai_attribute_filler import MLAttributeValue


class MercadolibreAttributeFixResponse(BaseModel):
    """The corrected collection of attributes after fixing errors."""

    attributes: List[MLAttributeValue]


class MercadolibreAttributeFixer:
    def __init__(self, client: instructor.Instructor) -> None:
        self.client = client

    def fix_attributes(self, product: ProductMaster, current_attributes: List[Dict[str, Any]], error_message: str) -> List[Dict[str, Any]]:
        """
        Uses AI to fix validation errors by matching ML error causes with product specs.
        """
        product_context = {
            "name": product.normalized_name,
            "specs": product.specs,
            "model_name": product.model_name,
            "gtin": product.gtin,
        }

        response = self.client.chat.completions.create(
            model=settings.OPENROUTER_MERCADOLIBRE_ATTRIBUTE_FILLER_MODEL,
            response_model=MercadolibreAttributeFixResponse,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a specialized agent for fixing Mercado Libre API 400 Validation Errors.\n"
                        "CONTEXT PROVIDED:\n"
                        "- JSON Error Body: Look at 'cause' -> 'code' and 'message' to identify missing or invalid attributes.\n"
                        "- Database Info: You have access to 'gtin', 'model_name', and technical 'specs'.\n"
                        "RULES:\n"
                        "1. MISSING GTIN: If the error mentions 'item.attribute.missing_conditional_required' for GTIN, "
                        "extract the value from the provided 'gtin' field in the Database Info.\n"
                        "2. INVALID BRAND/MODEL: If the error indicates a BRAND or MODEL issue, verify the correct value "
                        "against the 'name' and 'model_name' fields.\n"
                        "3. FORMAT CORRECTION: If an attribute value was rejected for format (like '65 inch'), "
                        "convert it to the required Mercado Libre format (e.g., '65 \"').\n"
                        "4. FULL RECONSTRUCTION: Return the COMPLETE list of attributes, including those that were already correct "
                        "plus the new/fixed ones.\n"
                        "5. LANGUAGE: All fixed 'value_name' entries must be in SPANISH."
                    ),
                },
                {"role": "user", "content": (f"Error Message: {error_message}\nCurrent Attributes: {current_attributes}\nProduct Specs: {product_context}")},
            ],
        )

        return [attr.model_dump(exclude_none=True) for attr in response.attributes]

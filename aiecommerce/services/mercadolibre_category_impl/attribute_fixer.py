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
        }

        response = self.client.chat.completions.create(
            model=settings.OPENROUTER_MERCADOLIBRE_ATTRIBUTE_FILLER_MODEL,
            response_model=MercadolibreAttributeFixResponse,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at fixing Mercado Libre validation errors.\n"
                        "Given a list of current attributes, product technical specs, and an API error message,\n"
                        "your task is to return a corrected and complete list of attributes.\n"
                        "RULES:\n"
                        "1. Identify missing or invalid attributes mentioned in the error message.\n"
                        "2. Extract the correct values from the Product Specs.\n"
                        "3. Return the FULL list of attributes (current ones + fixed/added ones).\n"
                        "4. All values must be in SPANISH.\n"
                        "5. If a required value is missing from specs, try to infer it ONLY if it's standard (e.g., Voltage for a region)."
                    ),
                },
                {"role": "user", "content": (f"Error Message: {error_message}\nCurrent Attributes: {current_attributes}\nProduct Specs: {product_context}")},
            ],
        )

        return [attr.model_dump(exclude_none=True) for attr in response.attributes]

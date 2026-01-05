import os
from typing import Any, Dict, Optional, Union

import instructor
from openai import OpenAI
from pydantic import BaseModel

from aiecommerce.models.product import ProductMaster


class BatchNumberUnit(BaseModel):
    value: Optional[float]
    unit: Optional[str]


AttributeValue = Union[
    str,
    bool,
    BatchNumberUnit,
    None,
]


class BatchAttributeResponse(BaseModel):
    attributes: Dict[str, AttributeValue]


class AIAttributeFiller:
    """
    Batch-fills MercadoLibre attributes using a single AI call.
    """

    def __init__(self):
        self.client = instructor.from_openai(
            OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ.get("OPENAI_BASE_URL"),
            )
        )

    def fill_attributes(
        self,
        product: ProductMaster,
        attributes: list[dict],
    ) -> Dict[str, Any]:
        """
        Returns MercadoLibre-ready attributes.
        """

        candidate_attributes = [a for a in attributes if not self._should_skip(a, product.specs or {})]

        if not candidate_attributes:
            return {}

        response = self._extract_batch(product, candidate_attributes)

        return self._map_to_ml_format(response.attributes, candidate_attributes)

    def _should_skip(self, attr: dict, specs: Dict[Any, Any]) -> bool:
        tags = attr.get("tags", {})

        if tags.get("read_only"):
            return True

        if tags.get("fixed"):
            return True

        if attr["id"] in (specs or {}):
            return True

        return False

    def _extract_batch(
        self,
        product: ProductMaster,
        attributes: list[dict],
    ) -> BatchAttributeResponse:
        prompt = self._build_batch_prompt(product, attributes)

        return self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_model=BatchAttributeResponse,
            messages=[
                {
                    "role": "system",
                    "content": ("You are an expert in MercadoLibre product catalogs.\nExtract product attributes accurately.\nReturn values in Spanish.\nDo not invent information."),
                },
                {"role": "user", "content": prompt},
            ],
        )

    def _build_batch_prompt(
        self,
        product: ProductMaster,
        attributes: list[dict],
    ) -> str:
        return f"""
    Product information (authoritative):
    - Description: {product.description}
    - Code: {product.code}
    - Current specs: {product.specs or {}}

    Attributes to complete:
    {attributes}

    Rules:
    - Complete ONLY the attributes provided.
    - Use ONLY the product information.
    - If information is missing, you MAY search the internet.
    - If the value cannot be determined with certainty, return null.
    - Do NOT infer or guess.
    - Use Spanish for attribute values.
    - Output a JSON object with attribute IDs as keys.
    - Respect allowed values and units.
    """

    def _map_to_ml_format(
        self,
        ai_values: Dict[str, Any],
        attributes: list[dict],
    ) -> Dict[str, Any]:
        result = {}
        attr_map = {a["id"]: a for a in attributes}

        for attr_id, value in ai_values.items():
            attr = attr_map.get(attr_id)
            if not attr or value is None:
                continue

            vt = attr["value_type"]

            if vt == "boolean":
                result[attr_id] = "242085" if value else "242084"

            elif vt == "list":
                for option in attr.get("values", []):
                    if option["name"].lower() == str(value).lower():
                        result[attr_id] = option["id"]
                        break

            elif vt == "number_unit":
                result[attr_id] = f"{value['value']} {value['unit']}"

            else:  # string
                result[attr_id] = str(value)

        return result

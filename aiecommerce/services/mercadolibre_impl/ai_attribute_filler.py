import os
from typing import Any, Dict, List, Optional

import instructor
from openai import OpenAI
from pydantic.v1 import BaseModel, Field, validator

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.google_search_client import GoogleSearchClient


# Pydantic Models for AI Extraction
class AttributeValueString(BaseModel):
    value: str = Field(
        ...,
        description="El valor extraído para el atributo. Debe ser una cadena de texto.",
    )


class AttributeValueNumber(BaseModel):
    value: float = Field(
        ...,
        description="El valor numérico extraído para el atributo.",
    )
    unit: str = Field(
        ...,
        description="La unidad de medida para el valor numérico. Debe ser una de las unidades permitidas.",
    )

    @validator("unit")
    def validate_unit(cls, v: str, values: Dict[str, Any]) -> str:
        # This is a placeholder validator. The actual allowed units will be passed in the prompt.
        return v


class AttributeValueBoolean(BaseModel):
    value: bool = Field(
        ...,
        description="El valor booleano extraído. True para 'Sí', False para 'No'.",
    )


class AttributeValueList(BaseModel):
    values: List[str] = Field(
        ...,
        description="Una lista de valores de texto para el atributo.",
    )


class AIAttributeFiller:
    """Service to fill product specifications using AI and web search."""

    def __init__(
        self,
        search_client: GoogleSearchClient,
        instructor_client: Optional[instructor.Instructor] = None,
    ):
        self.search_client = search_client
        if instructor_client:
            self.instructor_client = instructor_client
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("OPENAI_BASE_URL")
            self.instructor_client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))

        self.google_cse_id = os.environ.get("GOOGLE_CSE_ID")
        if not self.google_cse_id:
            raise ValueError("GOOGLE_CSE_ID environment variable not set.")

    def fill_product_specs(
        self,
        product: ProductMaster,
        required_metadata: List[Dict[str, Any]],
    ) -> None:
        """
        Enriches a ProductMaster's 'specs' JSONField with attributes found via web search and AI extraction.

        The process is done in Spanish.
        """
        updated_specs = product.specs.copy() if product.specs else {}
        needs_update = False

        for attr_meta in required_metadata:
            attr_id = attr_meta.get("id")
            if not attr_id or self._is_attribute_filled(attr_id, updated_specs):
                continue

            search_query = f"{product.description} {product.code} especificaciones técnicas"
            search_results = self._perform_search(search_query)

            if not search_results:
                continue

            extracted_value = self._extract_attribute_with_ai(product, attr_meta, search_results)

            if extracted_value is not None:
                updated_specs[attr_id] = extracted_value
                needs_update = True

        if needs_update:
            product.specs = updated_specs
            product.save(update_fields=["specs"])

    def _is_attribute_filled(self, attr_id: str, specs: Dict[str, Any]) -> bool:
        """Checks if an attribute is already present and valid in the specs."""
        return attr_id in specs and specs[attr_id] is not None

    def _perform_search(self, query: str) -> str:
        """Performs a web search and returns a formatted string of results."""
        try:
            response = self.search_client.list(q=query, cx=self.google_cse_id, num=5)
            items = response.get("items", [])
            return "\n".join([f"Fuente {i + 1}: {item.get('title')}\nURL: {item.get('link')}\nFragmento: {item.get('snippet')}" for i, item in enumerate(items)])
        except Exception:
            # In case of search errors, proceed without search results.
            return ""

    def _extract_attribute_with_ai(
        self,
        product: ProductMaster,
        attr_meta: Dict[str, Any],
        context: str,
    ) -> Optional[Any]:
        """Uses an LLM to extract a single attribute value from the provided context."""
        value_type = attr_meta.get("value_type")
        prompt = self._build_prompt(product, attr_meta, context)

        response_model: Optional[BaseModel] = None
        if value_type == "string":
            response_model = AttributeValueString
        elif value_type == "number_unit":
            response_model = AttributeValueNumber
        elif value_type == "boolean":
            response_model = AttributeValueBoolean
        elif value_type == "list":
            response_model = AttributeValueList
        else:
            return None  # Unsupported type

        try:
            response = self.instructor_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente experto en completar especificaciones técnicas de "
                            "productos en español. Tu única tarea es extraer el valor solicitado de "
                            "forma precisa basándote en la información proporcionada. Debes ser "
                            "preciso y técnico."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_model=response_model,
                temperature=0.0,
            )
            return self._format_response(response, value_type, attr_meta)
        except Exception:
            # If AI extraction fails, we can't fill the attribute.
            return None

    def _build_prompt(
        self,
        product: ProductMaster,
        attr_meta: Dict[str, Any],
        context: str,
    ) -> str:
        """Constructs the prompt for the AI based on the attribute metadata."""
        attr_name = attr_meta.get("name")
        value_type = attr_meta.get("value_type")

        base_prompt = f"""
        **Producto:**
        - **Descripción:** {product.description}
        - **Código/SKU:** {product.code}

        **Contexto de Búsqueda (Fuentes de Internet):**
        ---
        {context}
        ---

        **Tarea de Extracción (en ESPAÑOL):**
        Extrae el valor para el siguiente atributo técnico: **'{attr_name}'**.
        """

        if value_type == "number_unit":
            allowed_units = [unit["name"] for unit in attr_meta.get("allowed_units", [])]
            base_prompt += f"\nEl valor debe ser numérico y la unidad debe ser una de las siguientes: {', '.join(allowed_units)}."
        elif value_type == "boolean":
            base_prompt += "\nResponde únicamente con 'true' si la respuesta es afirmativa ('Sí') o 'false' si es negativa ('No')."

        return base_prompt

    def _format_response(self, response: BaseModel, value_type: str, attr_meta: Dict[str, Any]) -> Any:
        """Formats the structured response from the AI into the required format for saving."""
        if value_type == "string" and isinstance(response, AttributeValueString):
            return response.value
        if value_type == "number_unit" and isinstance(response, AttributeValueNumber):
            return f"{response.value} {response.unit}"
        if value_type == "boolean" and isinstance(response, AttributeValueBoolean):
            # Mercado Libre uses specific IDs for boolean values.
            # "Sí" -> "242085", "No" -> "242086"
            return "242085" if response.value else "242086"
        if value_type == "list" and isinstance(response, AttributeValueList):
            return response.values
        return None

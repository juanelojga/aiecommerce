import json
import logging
import os
from typing import Optional

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from aiecommerce.models import ProductMaster

# Configure logging
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un experto en redacción de títulos optimizados para publicaciones en Mercado Libre.
Tu objetivo es generar un TÍTULO DE PRODUCTO que cumpla exactamente con estas reglas oficiales:
1. Usa la estructura: Producto + Marca + Modelo + Especificaciones clave.
   Ejemplo: Notebook HP ProBook 440 G10 Intel Core i5 16GB 512GB SSD 14" Windows 11
2. No incluyas:
   - Estado del producto ("nuevo", "usado", "reacondicionado").
   - Información de stock, garantía, envíos, promociones o descuentos.
   - Nombres de marcas de terceros salvo que indique compatibilidad.
3. Separa las palabras con espacios, sin guiones ni símbolos.
4. Mantén el título con un máximo de 60 caracteres.
5. Usa formato consistente en mayúsculas y números (por ejemplo, 16GB o 512GB SSD).
Input (datos del producto en formato JSON):
{product_data}
Output:
Un título breve y limpio, listo para usar como `title` en la API de Mercado Libre.
""".strip()

MAX_TITLE_LENGTH = 60


class AITitle(BaseModel):
    title: str = Field(
        ...,
        description="The generated product title, optimized for Mercado Libre.",
        max_length=MAX_TITLE_LENGTH,
    )


class TitleGeneratorService:
    """A service to generate SEO-friendly titles using an AI model."""

    def __init__(self, client: Optional[instructor.Instructor] = None):
        """
        Initializes the service.

        Args:
            client: An optional `instructor.Instructor` client. If not provided,
                    a new one will be created using environment variables.
        """
        if client:
            self._client = client
        else:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")

            if not api_key or not base_url:
                raise ValueError("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment variables if a client is not provided.")

            self._client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))

    def generate_title(self, product: ProductMaster) -> str:
        """
        Generates an SEO title for a given product.

        Args:
            product: The ProductMaster instance.

        Returns:
            A generated title, truncated to the maximum allowed length.
        """
        logger.info(f"Generating title for product code: {product.code}")
        fallback_title = (product.description or "")[:MAX_TITLE_LENGTH]

        product_data = {
            "description": product.description,
            "specs": product.specs or {},
        }

        try:
            prompt = SYSTEM_PROMPT.format(product_data=json.dumps(product_data, indent=2))

            response = self._client.chat.completions.create(
                model=os.getenv("OPENROUTER_TITLE_GENERATION_MODEL"),
                response_model=AITitle,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            generated_title = response.title.strip()
            logger.info(f"Successfully generated title for product {product.code}: '{generated_title}'")

            return generated_title[:MAX_TITLE_LENGTH]

        except Exception as e:
            logger.error(f"AI title generation failed for product {product.code}. Error: {e}. Using fallback title.")
            return fallback_title

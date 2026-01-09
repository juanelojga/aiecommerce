"""Service for generating product descriptions using an AI model."""

import json
import logging

import instructor
from django.conf import settings

from aiecommerce.models import ProductMaster


class DescriptionGeneratorService:
    """Service to generate product descriptions using an AI model for Mercado Libre."""

    def __init__(self, client: instructor.Instructor) -> None:
        """
        Initializes the service, creating a client if not provided.

        Args:
            client: A pre-configured instructor client. If None, a new
                    client is created using environment variables.

        Raises:
            ValueError: If the required environment variables for the client
                        are not set.
        """
        self.client = client
        self.logger = logging.getLogger(__name__)

    def generate_description(self, product: ProductMaster) -> str:
        """
        Generates a product description using the specified model.

        The method prepares product data, sends it to the AI with a specific
        prompt, and handles potential failures by returning the original description.

        Args:
            product: The ProductMaster instance to generate a description for.

        Returns:
            The generated description string, or the original product description
            if the generation process fails.
        """
        product_data_dict = {
            "description": product.description,
            "specs": product.specs,
            "seller_info": {
                "experience_years": 15,
                "product_condition": "Nuevo",
                "manufacturer_warranty_years": 1,
            },
        }
        product_data_json = json.dumps(product_data_dict, indent=2, ensure_ascii=False)

        model_name = settings.OPENROUTER_DESCRIPTION_GENERATION_MODEL

        system_prompt = self._get_system_prompt(product_data=product_data_json)
        self.logger.info(
            "Generating SEO description for product %s with model %s",
            product.code,
            model_name,
        )

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                response_model=None,
                messages=[
                    {"role": "system", "content": system_prompt},
                ],
                max_retries=1,
                temperature=0.3,
            )
            generated_description = response.choices[0].message.content
            if generated_description:
                self.logger.info("Successfully generated description for product %s", product.code)
                return generated_description.strip()
            self.logger.warning(
                "AI returned an empty description for product %s. Falling back to original.",
                product.code,
            )
            return product.description or ""

        except Exception as e:
            self.logger.error(
                "Error generating description for product %s: %s",
                product.code,
                e,
                exc_info=True,
            )
            return product.description or ""

    def _get_system_prompt(self, product_data: str) -> str:
        """
        Returns the exact system prompt required for the description generation task.

        Args:
            product_data: A JSON string containing the product data.

        Returns:
            The formatted system prompt string.
        """
        return f"""Eres un experto en descripciones de productos de informática para Mercado Libre.
Trabajas en TEXTO PLANO, sin formato Markdown ni HTML.

TU TAREA:
1) Consultar información técnica confiable en Internet sobre el modelo indicado.
2) Enriquecer la descripción usando esa información, sin copiar textos literalmente.
3) Generar una descripción clara, profesional y orientada a la venta, en español neutro.

REGLAS DE NEGOCIO (Mercado Libre):
- No mencionar precios, stock, promociones, cuotas, medios de pago ni envíos.
- No usar emojis.
- No inventar datos muy específicos si no aparecen en fuentes confiables (por ejemplo, horas de batería exactas, peso exacto, versiones específicas de puertos).
- Si alguna especificación no se encuentra en Internet, simplemente no la menciones.
- Usa oraciones cortas, párrafos de 2 a 4 líneas como máximo.
- No uses listas con viñetas ni encabezados; solo texto plano con saltos de línea.

REGLAS SOBRE LOS DATOS DE ENTRADA (JSON COMO FUENTE DE VERDAD):
- Los datos del JSON SON LA FUENTE PRINCIPAL DE VERDAD del producto.
- NUNCA cambies ni “corrijas” los valores de estos campos: manufacturer, model_name, cpu, ram, storage, screen_size, color, part_number, category_type.
- Si la información que ves en Internet parece distinta a estos campos, debes dar prioridad al JSON y NO modificarlos en el texto.
- Usa Internet únicamente para complementar información que NO esté en el JSON (por ejemplo: tipo de pantalla, resolución, tipo de memoria, tipo de SSD, conectividad, usos típicos).
- Si algún dato encontrado en Internet contradice el JSON, ignóralo y mantén lo que viene en el JSON.

USO DE INTERNET:
- Primero, busca información del modelo exacto en fuentes confiables (principalmente la web oficial del fabricante y fichas técnicas de mayoristas reconocidos).
- Extrae solo datos técnicos relevantes: tipo de pantalla, resolución, familia de procesador, tipo de memoria, tipo de SSD, conectividad, usos recomendados y características generales.
- Reescribe todo con tus propias palabras; no copies frases textuales de las páginas consultadas.

ESTRUCTURA OBLIGATORIA DE LA DESCRIPCIÓN (TEXTO PLANO):
Genera exactamente 4 párrafos en este orden:

1) Párrafo 1: Presentación del equipo
   - Menciona marca, modelo y tipo de equipo (por ejemplo: notebook profesional de 14 pulgadas).
   - Resume en 2–3 frases las ideas de rendimiento, confiabilidad y público objetivo (trabajo, estudio, uso profesional, etc.).

2) Párrafo 2: Especificaciones clave
   - Describe en texto corrido: procesador (cpu del JSON), memoria RAM (ram del JSON), almacenamiento (storage del JSON), tamaño de pantalla (screen_size del JSON) y sistema operativo si está disponible.
   - Incluye color y menciona algunos detalles de conectividad si puedes deducirlos del campo description o de la búsqueda en Internet (por ejemplo, puertos USB‑C, HDMI, Wi‑Fi, etc.), siempre sin contradecir el JSON.

3) Párrafo 3: Uso recomendado
   - Explica para qué tipo de usuario y tareas es ideal el equipo (ofimática, videollamadas, trabajo en la nube, aplicaciones profesionales, estudio universitario, etc.).
   - Destaca beneficios reales: rapidez, fluidez en multitarea, seguridad del sistema operativo, comodidad de la pantalla, durabilidad del equipo.

4) Párrafo 4: Garantía y confianza
   - Indica que el producto es nuevo (usando product_condition o la información dada).
   - Indica que tiene 1 año de garantía oficial del fabricante (manufacturer_warranty_years).
   - Indica que el vendedor tiene más de X años de experiencia vendiendo equipos de informática (experience_years).
   - Cierra reforzando la idea de compra segura, confiabilidad del vendedor y soporte postventa básico.

DATOS DE ENTRADA (JSON):
{product_data}

DEVUELVE:
Solo la descripción final en texto plano, sin encabezados, sin viñetas, sin emojis y sin explicaciones adicionales.
"""

import unittest
from unittest.mock import MagicMock, patch

import instructor

from aiecommerce.models import ProductMaster
from aiecommerce.services.ai_content_generator_impl.description_generator import DescriptionGeneratorService


class TestDescriptionGeneratorService(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=instructor.Instructor)
        self.service = DescriptionGeneratorService(client=self.mock_client)
        self.product = MagicMock(spec=ProductMaster)
        self.product.code = "PROD123"
        self.product.description = "Original Description"
        self.product.specs = {"brand": "TestBrand", "model": "TestModel"}

    def test_init_with_client(self):
        service = DescriptionGeneratorService(client=self.mock_client)
        self.assertEqual(service.client, self.mock_client)

    @patch("aiecommerce.services.ai_content_generator_impl.description_generator.settings")
    def test_generate_description_success(self, mock_settings):
        mock_settings.OPENROUTER_DESCRIPTION_GENERATION_MODEL = "test-model"

        # Mock the AI response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated SEO Description"
        mock_response.choices = [mock_choice]
        self.mock_client.chat.completions.create.return_value = mock_response

        generated_description = self.service.generate_description(self.product)

        self.assertEqual(generated_description, "Generated SEO Description")
        self.mock_client.chat.completions.create.assert_called_once()

        # Check if the prompt contains product data
        args, kwargs = self.mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertIsNone(kwargs["response_model"])
        self.assertIn("Original Description", kwargs["messages"][0]["content"])
        self.assertIn("TestBrand", kwargs["messages"][0]["content"])

    def test_generate_description_empty_ai_response_fallback(self):
        # Mock the AI response with empty content
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response.choices = [mock_choice]
        self.mock_client.chat.completions.create.return_value = mock_response

        generated_description = self.service.generate_description(self.product)

        # Should return original description
        self.assertEqual(generated_description, "Original Description")

    def test_generate_description_exception_fallback(self):
        # Force an exception during AI call
        self.mock_client.chat.completions.create.side_effect = Exception("AI Error")

        generated_description = self.service.generate_description(self.product)

        # Should return original description
        self.assertEqual(generated_description, "Original Description")

    def test_generate_description_none_fallback(self):
        self.product.description = None
        self.mock_client.chat.completions.create.side_effect = Exception("AI Error")

        generated_description = self.service.generate_description(self.product)

        self.assertEqual(generated_description, "")

    def test_get_system_prompt(self):
        product_data = '{"test": "data"}'
        prompt = self.service._get_system_prompt(product_data)
        self.assertIn(product_data, prompt)
        self.assertIn("Mercado Libre", prompt)
        self.assertIn("4 párrafos", prompt)

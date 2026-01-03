import os
import unittest
from unittest.mock import MagicMock, patch

import instructor

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.ai_content.title_generator import (
    MAX_TITLE_LENGTH,
    AITitle,
    TitleGeneratorService,
)


class TestTitleGeneratorService(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=instructor.Instructor)
        self.service = TitleGeneratorService(client=self.mock_client)
        self.product = MagicMock(spec=ProductMaster)
        self.product.code = "PROD123"
        self.product.description = "Test Product Description"
        self.product.specs = {"brand": "TestBrand", "model": "TestModel"}

    def test_init_with_client(self):
        service = TitleGeneratorService(client=self.mock_client)
        self.assertEqual(service._client, self.mock_client)

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key", "OPENROUTER_BASE_URL": "https://test.url"})
    @patch("aiecommerce.services.mercadolibre_impl.ai_content.title_generator.OpenAI")
    @patch("instructor.from_openai")
    def test_init_without_client_success(self, mock_from_openai, mock_openai):
        mock_from_openai.return_value = self.mock_client
        service = TitleGeneratorService()
        self.assertEqual(service._client, self.mock_client)
        mock_openai.assert_called_once_with(api_key="test_key", base_url="https://test.url")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_client_failure(self):
        with self.assertRaises(ValueError) as cm:
            TitleGeneratorService()
        self.assertIn("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set", str(cm.exception))

    @patch("os.getenv")
    def test_generate_title_success(self, mock_getenv):
        mock_getenv.return_value = "test-model"

        # Mock the AI response
        mock_response = MagicMock(spec=AITitle)
        mock_response.title = "Generated SEO Title"
        self.mock_client.chat.completions.create.return_value = mock_response

        generated_title = self.service.generate_title(self.product)

        self.assertEqual(generated_title, "Generated SEO Title")
        self.mock_client.chat.completions.create.assert_called_once()

        # Check if the prompt contains product data
        args, kwargs = self.mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["response_model"], AITitle)
        self.assertIn("Test Product Description", kwargs["messages"][0]["content"])
        self.assertIn("TestBrand", kwargs["messages"][0]["content"])

    def test_generate_title_truncation(self):
        # Mock the AI response with a long title
        long_title = "A" * (MAX_TITLE_LENGTH + 10)
        mock_response = MagicMock(spec=AITitle)
        mock_response.title = long_title
        self.mock_client.chat.completions.create.return_value = mock_response

        generated_title = self.service.generate_title(self.product)

        self.assertEqual(len(generated_title), MAX_TITLE_LENGTH)
        self.assertEqual(generated_title, long_title[:MAX_TITLE_LENGTH])

    def test_generate_title_fallback_on_exception(self):
        # Force an exception during AI call
        self.mock_client.chat.completions.create.side_effect = Exception("AI Error")

        generated_title = self.service.generate_title(self.product)

        # Should return truncated description as fallback
        expected_fallback = self.product.description[:MAX_TITLE_LENGTH]
        self.assertEqual(generated_title, expected_fallback)

    def test_generate_title_fallback_empty_description(self):
        self.product.description = None
        self.mock_client.chat.completions.create.side_effect = Exception("AI Error")

        generated_title = self.service.generate_title(self.product)

        self.assertEqual(generated_title, "")

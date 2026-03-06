import unittest
from unittest.mock import MagicMock, patch

import instructor

from aiecommerce.models import ProductMaster
from aiecommerce.services.ai_content_generator_impl import (
    MAX_TITLE_LENGTH,
    AITitle,
    TitleGeneratorService,
)


class TestAITitle(unittest.TestCase):
    """Tests for the AITitle Pydantic model and its field_validator."""

    def test_title_under_max_length_unchanged(self):
        title = "Notebook HP ProBook 440 G10 i5 16GB 512GB"
        result = AITitle(title=title)
        self.assertEqual(result.title, title)

    def test_title_exactly_max_length_unchanged(self):
        title = "A" * MAX_TITLE_LENGTH
        result = AITitle(title=title)
        self.assertEqual(result.title, title)
        self.assertEqual(len(result.title), MAX_TITLE_LENGTH)

    def test_title_over_max_length_truncated_at_word_boundary(self):
        # 74 chars — mirrors the real failure case
        title = "Procesador AMD Ryzen 5 9600 3.8GHz 6 Núcleos 12 Hilos 32MB L3 Cache 65W"
        result = AITitle(title=title)
        self.assertLessEqual(len(result.title), MAX_TITLE_LENGTH)
        # Must not cut mid-word
        self.assertFalse(result.title.endswith(" "))
        self.assertNotIn("  ", result.title)

    def test_title_over_max_length_no_spaces_hard_truncates(self):
        # No spaces means rfind returns -1, falls through to hard truncate
        title = "A" * (MAX_TITLE_LENGTH + 20)
        result = AITitle(title=title)
        self.assertEqual(len(result.title), MAX_TITLE_LENGTH)

    def test_title_strips_whitespace(self):
        title = "  Notebook HP ProBook  "
        result = AITitle(title=title)
        self.assertEqual(result.title, "Notebook HP ProBook")

    def test_title_long_with_trailing_spaces_after_truncation(self):
        # Build a title where truncation lands right after a space
        title = "A" * 59 + " B extra words that exceed the limit"
        result = AITitle(title=title)
        self.assertLessEqual(len(result.title), MAX_TITLE_LENGTH)
        self.assertFalse(result.title.endswith(" "))


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
        self.assertEqual(service.client, self.mock_client)

    @patch("aiecommerce.services.ai_content_generator_impl.title_generator.settings")
    def test_generate_title_success(self, mock_settings):
        mock_settings.OPENROUTER_TITLE_GENERATION_MODEL = "test-model"

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
        # Mock the AI response with a long title (no spaces, so hard-truncated)
        long_title = "A" * (MAX_TITLE_LENGTH + 10)
        mock_response = MagicMock(spec=AITitle)
        mock_response.title = long_title
        self.mock_client.chat.completions.create.return_value = mock_response

        generated_title = self.service.generate_title(self.product)

        self.assertLessEqual(len(generated_title), MAX_TITLE_LENGTH)

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

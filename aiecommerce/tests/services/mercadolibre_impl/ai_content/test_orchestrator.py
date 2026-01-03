from unittest.mock import MagicMock

from django.test import TestCase

from aiecommerce.services.mercadolibre_impl.ai_content.description_generator import DescriptionGeneratorService
from aiecommerce.services.mercadolibre_impl.ai_content.orchestrator import AIContentOrchestrator
from aiecommerce.services.mercadolibre_impl.ai_content.title_generator import TitleGeneratorService
from aiecommerce.tests.factories import ProductMasterFactory


class TestAIContentOrchestrator(TestCase):
    def setUp(self):
        self.mock_title_gen = MagicMock(spec=TitleGeneratorService)
        self.mock_desc_gen = MagicMock(spec=DescriptionGeneratorService)
        self.mock_title_gen.generate_title.return_value = "Default Title"
        self.mock_desc_gen.generate_description.return_value = "Default Description"
        self.orchestrator = AIContentOrchestrator(title_generator=self.mock_title_gen, description_generator=self.mock_desc_gen)
        self.product = ProductMasterFactory(is_for_mercadolibre=True, seo_title=None, seo_description=None)

    def test_process_product_content_success(self):
        self.mock_title_gen.generate_title.return_value = "Generated Title"
        self.mock_desc_gen.generate_description.return_value = "Generated Description"

        result = self.orchestrator.process_product_content(self.product)

        self.assertTrue(result["updated"])
        self.assertIn("seo_title", result["generated_fields"])
        self.assertIn("seo_description", result["generated_fields"])

        # Verify product was updated in DB
        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Generated Title")
        self.assertEqual(self.product.seo_description, "Generated Description")

    def test_process_product_content_dry_run(self):
        self.mock_title_gen.generate_title.return_value = "Generated Title"
        self.mock_desc_gen.generate_description.return_value = "Generated Description"

        result = self.orchestrator.process_product_content(self.product, dry_run=True)

        self.assertFalse(result["updated"])
        self.assertIn("seo_title", result["generated_fields"])
        self.assertIn("seo_description", result["generated_fields"])

        # Verify product was NOT updated in DB
        self.product.refresh_from_db()
        self.assertIsNone(self.product.seo_title)
        self.assertIsNone(self.product.seo_description)

    def test_process_product_content_force_refresh(self):
        self.product.seo_title = "Old Title"
        self.product.seo_description = "Old Description"
        self.product.save()

        self.mock_title_gen.generate_title.return_value = "New Title"
        self.mock_desc_gen.generate_description.return_value = "New Description"

        # Without force_refresh, nothing should happen
        result = self.orchestrator.process_product_content(self.product, force_refresh=False)
        self.assertFalse(result["updated"])
        self.assertEqual(len(result["generated_fields"]), 0)

        # With force_refresh, it should regenerate
        result = self.orchestrator.process_product_content(self.product, force_refresh=True)
        self.assertTrue(result["updated"])
        self.assertIn("seo_title", result["generated_fields"])
        self.assertIn("seo_description", result["generated_fields"])

        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "New Title")
        self.assertEqual(self.product.seo_description, "New Description")

    def test_process_product_content_partial(self):
        self.product.seo_title = "Existing Title"
        self.product.seo_description = None
        self.product.save()

        self.mock_desc_gen.generate_description.return_value = "New Description"

        result = self.orchestrator.process_product_content(self.product)

        self.assertTrue(result["updated"])
        self.assertEqual(result["generated_fields"], ["seo_description"])
        self.mock_title_gen.generate_title.assert_not_called()

        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Existing Title")
        self.assertEqual(self.product.seo_description, "New Description")

    def test_process_product_content_error_handling(self):
        self.mock_title_gen.generate_title.side_effect = Exception("Title Gen Error")

        result = self.orchestrator.process_product_content(self.product)

        self.assertFalse(result["updated"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Title Gen Error")

    def test_process_batch(self):
        # Create 5 products that need processing
        ProductMasterFactory.create_batch(5, is_for_mercadolibre=True, seo_title=None, seo_description=None)
        # Create 2 products that don't need processing (already have content)
        ProductMasterFactory.create_batch(2, is_for_mercadolibre=True, seo_title="T", seo_description="D")
        # Create 3 products not for MercadoLibre
        ProductMasterFactory.create_batch(3, is_for_mercadolibre=False, seo_title=None, seo_description=None)

        self.mock_title_gen.generate_title.return_value = "Title"
        self.mock_desc_gen.generate_description.return_value = "Description"

        # Initial count of products to process should be 6 (5 + self.product from setUp)
        # self.product from setUp also matches the criteria.

        processed_count = self.orchestrator.process_batch(limit=10)

        self.assertEqual(processed_count, 6)
        self.assertEqual(self.mock_title_gen.generate_title.call_count, 6)

    def test_process_batch_limit(self):
        ProductMasterFactory.create_batch(10, is_for_mercadolibre=True, seo_title=None, seo_description=None)

        processed_count = self.orchestrator.process_batch(limit=3)

        self.assertEqual(processed_count, 3)

    def test_process_batch_force_refresh(self):
        # 5 products with content
        ProductMasterFactory.create_batch(5, is_for_mercadolibre=True, seo_title="T", seo_description="D")

        # Without force_refresh, only 1 should be processed (self.product from setUp)
        processed_count = self.orchestrator.process_batch(limit=10, force_refresh=False)
        self.assertEqual(processed_count, 1)

        # With force_refresh, all should be processed (5 + 1)
        processed_count = self.orchestrator.process_batch(limit=10, force_refresh=True)
        self.assertEqual(processed_count, 6)

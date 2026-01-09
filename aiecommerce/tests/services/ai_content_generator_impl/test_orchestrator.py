from unittest.mock import MagicMock

import instructor
from django.test import TestCase

from aiecommerce.services.ai_content_generator_impl import (
    AIContentGeneratorCandidateSelector,
    AIContentOrchestrator,
    TitleGeneratorService,
)
from aiecommerce.services.ai_content_generator_impl.description_generator import DescriptionGeneratorService
from aiecommerce.tests.factories import ProductMasterFactory


class TestAIContentOrchestrator(TestCase):
    def setUp(self):
        self.mock_title_gen = MagicMock(spec=TitleGeneratorService)
        self.mock_desc_gen = MagicMock(spec=DescriptionGeneratorService)
        self.mock_client = MagicMock(spec=instructor.Instructor)
        self.mock_selector = MagicMock(spec=AIContentGeneratorCandidateSelector)

        self.mock_title_gen.generate_title.return_value = "Default Title"
        self.mock_desc_gen.generate_description.return_value = "Default Description"

        self.orchestrator = AIContentOrchestrator(
            title_generator=self.mock_title_gen,
            description_generator=self.mock_desc_gen,
            client=self.mock_client,
            selector=self.mock_selector,
        )
        self.product = ProductMasterFactory(is_for_mercadolibre=True, seo_title=None, seo_description=None)

    def test_run_success(self):
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        self.mock_title_gen.generate_title.return_value = "Generated Title"
        self.mock_desc_gen.generate_description.return_value = "Generated Description"

        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        self.assertEqual(result["processed"], 1)

        # Verify product was updated in DB
        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Generated Title")
        self.assertEqual(self.product.seo_description, "Generated Description")

    def test_run_dry_run(self):
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        self.mock_title_gen.generate_title.return_value = "Generated Title"
        self.mock_desc_gen.generate_description.return_value = "Generated Description"

        result = self.orchestrator.run(force=False, dry_run=True, delay=0)

        self.assertEqual(result["processed"], 1)

        # Verify product was NOT updated in DB
        self.product.refresh_from_db()
        self.assertIsNone(self.product.seo_title)
        self.assertIsNone(self.product.seo_description)

    def test_run_force_refresh(self):
        self.product.seo_title = "Old Title"
        self.product.seo_description = "Old Description"
        self.product.save()

        self.mock_title_gen.generate_title.return_value = "New Title"
        self.mock_desc_gen.generate_description.return_value = "New Description"

        # mock_selector.get_queryset should handle the force flag logic in real use,
        # but here we mock its return based on what we want to test in the orchestrator.

        # With force=True
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        result = self.orchestrator.run(force=True, dry_run=False, delay=0)
        self.assertEqual(result["processed"], 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "New Title")
        self.assertEqual(self.product.seo_description, "New Description")

    def test_run_partial_generation(self):
        # Case where only description is missing
        self.product.seo_title = "Existing Title"
        self.product.seo_description = None
        self.product.save()

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        self.mock_desc_gen.generate_description.return_value = "New Description"

        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        self.assertEqual(result["processed"], 1)
        self.mock_title_gen.generate_title.assert_not_called()

        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Existing Title")
        self.assertEqual(self.product.seo_description, "New Description")

    def test_run_error_handling(self):
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        self.mock_title_gen.generate_title.side_effect = Exception("Title Gen Error")

        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        self.assertEqual(result["processed"], 1)
        # The orchestrator catches exceptions and logs them, continuing to the next product.
        # It doesn't return the error in the main result dict (stats), but we could verify logs if needed.
        # Based on current implementation, it just increments processed.

    def test_run_batch(self):
        products = ProductMasterFactory.create_batch(5)
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 5
        mock_queryset.iterator.return_value = products
        self.mock_selector.get_queryset.return_value = mock_queryset

        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        self.assertEqual(result["processed"], 5)
        self.assertEqual(self.mock_title_gen.generate_title.call_count, 5)
        self.assertEqual(self.mock_desc_gen.generate_description.call_count, 5)

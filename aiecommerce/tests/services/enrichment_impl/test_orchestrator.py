from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.services.enrichment_impl.orchestrator import EnrichmentOrchestrator
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestEnrichmentOrchestrator:
    def setup_method(self):
        self.selector = MagicMock()
        self.specs_orchestrator = MagicMock()
        self.orchestrator = EnrichmentOrchestrator(selector=self.selector, specs_orchestrator=self.specs_orchestrator)

    def test_run_empty_queryset(self, caplog):
        self.selector.get_queryset.return_value.count.return_value = 0

        with caplog.at_level("INFO"):
            stats = self.orchestrator.run(force=False, dry_run=False)

        assert stats["total"] == 0
        assert "No products need enrichment." in caplog.text
        self.specs_orchestrator.process_product.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_run_success(self, mock_sleep):
        p1 = ProductMasterFactory(specs=None)
        p2 = ProductMasterFactory(specs=None)

        # Mock queryset iterator
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 2
        mock_queryset.iterator.return_value = [p1, p2]
        self.selector.get_queryset.return_value = mock_queryset

        # Mock process_product success
        self.specs_orchestrator.process_product.return_value = (True, {"some": "specs"})

        stats = self.orchestrator.run(force=False, dry_run=False, delay=0.1)

        assert stats["total"] == 2
        assert stats["enriched"] == 2
        assert self.specs_orchestrator.process_product.call_count == 2
        assert mock_sleep.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_run_skips_products_with_specs(self, mock_sleep, caplog):
        p1 = ProductMasterFactory(specs={"already": "here"}, normalized_name="Name", model_name="Model")

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [p1]
        self.selector.get_queryset.return_value = mock_queryset

        with caplog.at_level("INFO"):
            stats = self.orchestrator.run(force=False, dry_run=False)

        assert stats["total"] == 1
        assert stats["enriched"] == 0
        assert self.specs_orchestrator.process_product.assert_not_called
        assert f"Product {p1.id}: Skipping enrichment" in caplog.text

    @patch("time.sleep", return_value=None)
    def test_run_force_reenriches_even_with_specs(self, mock_sleep):
        p1 = ProductMasterFactory(specs={"already": "here"}, normalized_name="Name", model_name="Model")

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [p1]
        self.selector.get_queryset.return_value = mock_queryset

        self.specs_orchestrator.process_product.return_value = (True, {"new": "specs"})

        stats = self.orchestrator.run(force=True, dry_run=False)

        assert stats["enriched"] == 1
        self.specs_orchestrator.process_product.assert_called_once_with(p1, False)

    @patch("time.sleep", return_value=None)
    def test_run_handles_process_product_exception(self, mock_sleep, caplog):
        p1 = ProductMasterFactory(specs=None)

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [p1]
        self.selector.get_queryset.return_value = mock_queryset

        self.specs_orchestrator.process_product.side_effect = Exception("AI failure")

        with caplog.at_level("ERROR"):
            stats = self.orchestrator.run(force=False, dry_run=False)

        assert stats["enriched"] == 0
        assert f"Product {p1.id}: AI enrichment crashed" in caplog.text

    @patch("time.sleep", return_value=None)
    def test_run_passes_dry_run_flag(self, mock_sleep):
        p1 = ProductMasterFactory(specs=None)

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [p1]
        self.selector.get_queryset.return_value = mock_queryset

        self.specs_orchestrator.process_product.return_value = (True, {"dry": "specs"})

        self.orchestrator.run(force=False, dry_run=True)

        self.specs_orchestrator.process_product.assert_called_once_with(p1, True)

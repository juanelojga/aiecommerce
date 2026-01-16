from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.models import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.batch_orchestrator import BatchPublisherOrchestrator
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductMasterFactory


@pytest.mark.django_db
class TestBatchPublisherOrchestrator:
    @pytest.fixture
    def mock_publisher_orchestrator(self):
        return MagicMock()

    @pytest.fixture
    def batch_orchestrator(self, mock_publisher_orchestrator):
        return BatchPublisherOrchestrator(publisher_orchestrator=mock_publisher_orchestrator)

    def test_get_pending_listings(self, batch_orchestrator):
        # Create some listings
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING)
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING)
        MercadoLibreListingFactory(status="PUBLISHED")  # Should be ignored

        pending = batch_orchestrator._get_pending_listings()

        assert len(pending) == 2
        for listing in pending:
            assert listing.status == MercadoLibreListing.Status.PENDING

    def test_run_no_pending_listings(self, batch_orchestrator, mock_publisher_orchestrator):
        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=[]):
            batch_orchestrator.run(dry_run=False, sandbox=True)
            mock_publisher_orchestrator.run.assert_not_called()

    def test_run_with_pending_listings_success(self, batch_orchestrator, mock_publisher_orchestrator):
        product1 = ProductMasterFactory(code="PROD1")
        product2 = ProductMasterFactory(code="PROD2")
        listing1 = MercadoLibreListingFactory(product_master=product1, status=MercadoLibreListing.Status.PENDING)
        listing2 = MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING)

        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=[listing1, listing2]):
            batch_orchestrator.run(dry_run=True, sandbox=False)

            assert mock_publisher_orchestrator.run.call_count == 2
            mock_publisher_orchestrator.run.assert_any_call(product_code="PROD1", dry_run=True, sandbox=False)
            mock_publisher_orchestrator.run.assert_any_call(product_code="PROD2", dry_run=True, sandbox=False)

    def test_run_skips_listing_without_product_master(self, batch_orchestrator, mock_publisher_orchestrator):
        listing_no_product = MagicMock(spec=MercadoLibreListing)
        listing_no_product.product_master = None
        listing_no_product.id = 123

        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=[listing_no_product]):
            batch_orchestrator.run(dry_run=False, sandbox=True)
            mock_publisher_orchestrator.run.assert_not_called()

    def test_run_continues_on_exception(self, batch_orchestrator, mock_publisher_orchestrator):
        product1 = ProductMasterFactory(code="PROD1")
        product2 = ProductMasterFactory(code="PROD2")
        listing1 = MercadoLibreListingFactory(product_master=product1, status=MercadoLibreListing.Status.PENDING)
        listing2 = MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING)

        # First call fails, second should still happen
        mock_publisher_orchestrator.run.side_effect = [Exception("Error"), None]

        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=[listing1, listing2]):
            batch_orchestrator.run(dry_run=False, sandbox=True)

            assert mock_publisher_orchestrator.run.call_count == 2
            mock_publisher_orchestrator.run.assert_any_call(product_code="PROD1", dry_run=False, sandbox=True)
            mock_publisher_orchestrator.run.assert_any_call(product_code="PROD2", dry_run=False, sandbox=True)

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
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, available_quantity=10)
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, available_quantity=5)
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, available_quantity=0)  # Should be ignored (stock 0)
        MercadoLibreListingFactory(status="PUBLISHED", available_quantity=10)  # Should be ignored (wrong status)

        pending = batch_orchestrator._get_pending_listings()

        assert pending.count() == 2
        for listing in pending:
            assert listing.status == MercadoLibreListing.Status.PENDING

    def test_get_pending_listings_with_max_count(self, batch_orchestrator):
        # Create 5 listings, but limit to 3
        for _ in range(5):
            MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, available_quantity=10)

        pending = batch_orchestrator._get_pending_listings(max_count=3)
        assert pending.count() == 3

    def test_run_no_pending_listings(self, batch_orchestrator, mock_publisher_orchestrator):
        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=MercadoLibreListing.objects.none()):
            stats = batch_orchestrator.run(dry_run=False, sandbox=True)

            assert stats == {"success": 0, "errors": 0, "skipped": 0}
            mock_publisher_orchestrator.run.assert_not_called()

    def test_run_with_pending_listings_success(self, batch_orchestrator, mock_publisher_orchestrator):
        product1 = ProductMasterFactory(code="PROD1")
        product2 = ProductMasterFactory(code="PROD2")
        MercadoLibreListingFactory(product_master=product1, status=MercadoLibreListing.Status.PENDING, available_quantity=10)
        MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING, available_quantity=5)

        stats = batch_orchestrator.run(dry_run=True, sandbox=False)

        assert stats["success"] == 2
        assert stats["errors"] == 0
        assert stats["skipped"] == 0
        assert mock_publisher_orchestrator.run.call_count == 2
        mock_publisher_orchestrator.run.assert_any_call(product_code="PROD1", dry_run=True, sandbox=False)
        mock_publisher_orchestrator.run.assert_any_call(product_code="PROD2", dry_run=True, sandbox=False)

    def test_run_skips_listing_without_product_master(self, batch_orchestrator, mock_publisher_orchestrator):
        listing_no_product = MagicMock(spec=MercadoLibreListing)
        listing_no_product.product_master = None
        listing_no_product.id = 123

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.__iter__.return_value = iter([listing_no_product])

        with patch.object(BatchPublisherOrchestrator, "_get_pending_listings", return_value=mock_queryset):
            stats = batch_orchestrator.run(dry_run=False, sandbox=True)

            assert stats["skipped"] == 1
            assert stats["success"] == 0
            assert stats["errors"] == 0
            mock_publisher_orchestrator.run.assert_not_called()

    def test_run_continues_on_exception(self, batch_orchestrator, mock_publisher_orchestrator):
        product1 = ProductMasterFactory(code="PROD1")
        product2 = ProductMasterFactory(code="PROD2")
        MercadoLibreListingFactory(product_master=product1, status=MercadoLibreListing.Status.PENDING, available_quantity=10)
        MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING, available_quantity=5)

        # First call fails, second should still happen
        mock_publisher_orchestrator.run.side_effect = [Exception("Error"), None]

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        assert stats["success"] == 1
        assert stats["errors"] == 1
        assert stats["skipped"] == 0
        assert mock_publisher_orchestrator.run.call_count == 2
        mock_publisher_orchestrator.run.assert_any_call(product_code="PROD1", dry_run=False, sandbox=True)
        mock_publisher_orchestrator.run.assert_any_call(product_code="PROD2", dry_run=False, sandbox=True)

    def test_run_with_max_batch_size(self, batch_orchestrator, mock_publisher_orchestrator):
        # Create more listings than the batch size
        for i in range(5):
            ProductMasterFactory(code=f"PROD{i}")
            MercadoLibreListingFactory(product_master=ProductMasterFactory(code=f"PROD{i}"), status=MercadoLibreListing.Status.PENDING, available_quantity=10)

        stats = batch_orchestrator.run(dry_run=False, sandbox=True, max_batch_size=3)

        # Should process only 3 listings
        assert mock_publisher_orchestrator.run.call_count == 3
        assert stats["success"] + stats["errors"] + stats["skipped"] == 3

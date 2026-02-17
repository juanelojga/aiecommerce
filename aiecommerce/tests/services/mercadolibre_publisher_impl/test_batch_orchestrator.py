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

            assert stats == {"success": 0, "errors": 0, "skipped": 0, "published_ids": []}
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
        listing1 = MercadoLibreListingFactory(product_master=product1, status=MercadoLibreListing.Status.PENDING, available_quantity=10, sync_error=None)
        listing2 = MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING, available_quantity=5, sync_error=None)

        # First call fails, second should still happen
        error_message = "AI fixer validation error"
        mock_publisher_orchestrator.run.side_effect = [Exception(error_message), None]

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        assert stats["success"] == 1
        assert stats["errors"] == 1
        assert stats["skipped"] == 0
        assert mock_publisher_orchestrator.run.call_count == 2

        # Refresh both listings and check which one failed
        listing1.refresh_from_db()
        listing2.refresh_from_db()

        # One should be ERROR, one should be PENDING (order depends on queryset)
        error_listings = [listing for listing in [listing1, listing2] if listing.status == MercadoLibreListing.Status.ERROR]
        pending_listings = [listing for listing in [listing1, listing2] if listing.status == MercadoLibreListing.Status.PENDING]

        assert len(error_listings) == 1, "Exactly one listing should be marked as ERROR"
        assert len(pending_listings) == 1, "Exactly one listing should remain PENDING"
        assert error_message in error_listings[0].sync_error

    def test_run_with_max_batch_size(self, batch_orchestrator, mock_publisher_orchestrator):
        # Create more listings than the batch size
        for i in range(5):
            ProductMasterFactory(code=f"PROD{i}")
            MercadoLibreListingFactory(product_master=ProductMasterFactory(code=f"PROD{i}"), status=MercadoLibreListing.Status.PENDING, available_quantity=10)

        stats = batch_orchestrator.run(dry_run=False, sandbox=True, max_batch_size=3)

        # Should process only 3 listings
        assert mock_publisher_orchestrator.run.call_count == 3
        assert stats["success"] + stats["errors"] + stats["skipped"] == 3

    def test_run_marks_failed_listing_as_error(self, batch_orchestrator, mock_publisher_orchestrator):
        """Test that when publication fails, listing is marked ERROR with sync_error populated."""
        product = ProductMasterFactory(code="PROD1")
        listing = MercadoLibreListingFactory(product_master=product, status=MercadoLibreListing.Status.PENDING, available_quantity=10, sync_error=None)

        # Simulate AI fixer failure
        error_message = "HTTP Error 400: Invalid attributes after AI fixer attempt"
        mock_publisher_orchestrator.run.side_effect = Exception(error_message)

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        assert stats["errors"] == 1
        assert stats["success"] == 0

        # Verify listing was marked as ERROR with error details
        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert listing.sync_error == error_message

    def test_run_persists_error_status_after_transaction_rollback(self, batch_orchestrator, mock_publisher_orchestrator):
        """Test that ERROR status persists even after transaction rollback."""
        product = ProductMasterFactory(code="PROD1")
        listing = MercadoLibreListingFactory(product_master=product, status=MercadoLibreListing.Status.PENDING, available_quantity=10, ml_id=None, sync_error=None)

        # Simulate failure that would trigger transaction rollback
        error_message = "MLAPIError: AI attribute fixer failed for product PROD1"
        mock_publisher_orchestrator.run.side_effect = Exception(error_message)

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        # Verify error was counted
        assert stats["errors"] == 1

        # Verify listing status was updated OUTSIDE the transaction
        # This ensures the ERROR status persists even though the transaction rolled back
        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert listing.sync_error == error_message
        assert listing.ml_id is None  # Should remain None since publication failed

    def test_run_collects_ml_ids_on_success(self, batch_orchestrator, mock_publisher_orchestrator):
        """Test that ML IDs are collected from successfully published listings."""
        product1 = ProductMasterFactory(code="PROD1")
        product2 = ProductMasterFactory(code="PROD2")
        MercadoLibreListingFactory(
            product_master=product1,
            status=MercadoLibreListing.Status.PENDING,
            available_quantity=10,
            ml_id="MLB123456789",  # Simulating successful publication
        )
        MercadoLibreListingFactory(product_master=product2, status=MercadoLibreListing.Status.PENDING, available_quantity=5, ml_id="MLB987654321")

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        assert stats["success"] == 2
        assert stats["errors"] == 0
        assert "MLB123456789" in stats["published_ids"]
        assert "MLB987654321" in stats["published_ids"]

    def test_run_handles_multiple_failures_correctly(self, batch_orchestrator, mock_publisher_orchestrator):
        """Test that multiple failures are handled correctly, each marked as ERROR."""
        products = [ProductMasterFactory(code=f"PROD{i}") for i in range(3)]
        listings = [MercadoLibreListingFactory(product_master=products[i], status=MercadoLibreListing.Status.PENDING, available_quantity=10, sync_error=None) for i in range(3)]

        # All three publications fail with different errors
        mock_publisher_orchestrator.run.side_effect = [
            Exception("AI fixer timeout"),
            Exception("HTTP 400: Invalid category"),
            Exception("Connection error"),
        ]

        stats = batch_orchestrator.run(dry_run=False, sandbox=True)

        assert stats["errors"] == 3
        assert stats["success"] == 0

        # Verify all listings marked as ERROR with respective errors
        for i, listing in enumerate(listings):
            listing.refresh_from_db()
            assert listing.status == MercadoLibreListing.Status.ERROR
            assert listing.sync_error is not None
            assert len(listing.sync_error) > 0

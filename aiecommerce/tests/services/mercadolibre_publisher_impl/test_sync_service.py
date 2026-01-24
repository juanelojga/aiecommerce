from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.sync_service import MercadoLibreSyncService
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductMasterFactory


@pytest.fixture
def ml_client():
    return MagicMock()


@pytest.fixture
def sync_service(ml_client):
    return MercadoLibreSyncService(ml_client=ml_client)


@pytest.mark.django_db
class TestMercadoLibreSyncService:
    def test_sync_listing_no_changes(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("100.00"), is_active=True)
        listing = MercadoLibreListingFactory(
            product_master=product,
            final_price=Decimal("180.52"),  # Matching default price engine calc for 100
            available_quantity=4,
            ml_id="ML123",
        )

        # Mock price engine and stock engine to return current values
        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": Decimal("180.52"), "net_price": Decimal("161.18"), "profit": Decimal("22.00")}
            mock_stock.return_value = 4

            result = sync_service.sync_listing(listing)

            assert result is False
            ml_client.put.assert_not_called()

    def test_sync_listing_price_update(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("110.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id="ML123")

        new_price = Decimal("195.00")
        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": new_price, "net_price": Decimal("175.00"), "profit": Decimal("25.00")}
            mock_stock.return_value = 4

            result = sync_service.sync_listing(listing)

            assert result is True
            ml_client.put.assert_called_once_with("items/ML123", json={"price": new_price})

            listing.refresh_from_db()
            assert listing.final_price == new_price
            assert listing.net_price == Decimal("175.00")
            assert listing.profit == Decimal("25.00")

    def test_sync_listing_quantity_update(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("100.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id="ML123")

        new_quantity = 2
        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": Decimal("180.52"), "net_price": Decimal("161.18"), "profit": Decimal("22.00")}
            mock_stock.return_value = new_quantity

            result = sync_service.sync_listing(listing)

            assert result is True
            ml_client.put.assert_called_once_with("items/ML123", json={"available_quantity": new_quantity})

            listing.refresh_from_db()
            assert listing.available_quantity == new_quantity

    def test_sync_listing_both_update(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("110.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id="ML123")

        new_price = Decimal("195.00")
        new_quantity = 2
        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": new_price, "net_price": Decimal("175.00"), "profit": Decimal("25.00")}
            mock_stock.return_value = new_quantity

            result = sync_service.sync_listing(listing)

            assert result is True
            ml_client.put.assert_called_once_with("items/ML123", json={"price": new_price, "available_quantity": new_quantity})

            listing.refresh_from_db()
            assert listing.final_price == new_price
            assert listing.available_quantity == new_quantity

    def test_sync_listing_missing_ml_id(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("110.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id=None)

        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": Decimal("195.00"), "net_price": Decimal("175.00"), "profit": Decimal("25.00")}
            mock_stock.return_value = 2

            result = sync_service.sync_listing(listing)

            assert result is True
            ml_client.put.assert_not_called()

            listing.refresh_from_db()
            assert listing.final_price == Decimal("180.52")

    def test_sync_listing_dry_run(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("110.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id="ML123")

        new_price = Decimal("195.00")
        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": new_price, "net_price": Decimal("175.00"), "profit": Decimal("25.00")}
            mock_stock.return_value = 2

            result = sync_service.sync_listing(listing, dry_run=True)

            assert result is True
            ml_client.put.assert_not_called()

            listing.refresh_from_db()
            assert listing.final_price == Decimal("180.52")
            assert listing.available_quantity == 4

    def test_sync_listing_client_error(self, sync_service, ml_client):
        product = ProductMasterFactory(price=Decimal("110.00"), is_active=True)
        listing = MercadoLibreListingFactory(product_master=product, final_price=Decimal("180.52"), available_quantity=4, ml_id="ML123")

        ml_client.put.side_effect = Exception("API Error")

        with patch.object(sync_service._price_engine, "calculate") as mock_calc, patch.object(sync_service._stock_engine, "get_available_quantity") as mock_stock:
            mock_calc.return_value = {"final_price": Decimal("195.00"), "net_price": Decimal("175.00"), "profit": Decimal("25.00")}
            mock_stock.return_value = 2

            result = sync_service.sync_listing(listing)

            assert result is False
            listing.refresh_from_db()
            assert listing.final_price == Decimal("180.52")

    def test_sync_all_listings(self, sync_service, ml_client):
        # Create 2 active listings that need updates
        l1 = MercadoLibreListingFactory(status=MercadoLibreListing.Status.ACTIVE, final_price=100, available_quantity=5, ml_id="ML1")
        l2 = MercadoLibreListingFactory(status=MercadoLibreListing.Status.ACTIVE, final_price=200, available_quantity=10, ml_id="ML2")
        # Create 1 inactive listing
        l3 = MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, final_price=300, available_quantity=15, ml_id="ML3")

        with patch.object(sync_service, "sync_listing") as mock_sync_listing:
            mock_sync_listing.return_value = True

            sync_service.sync_all_listings()

            assert mock_sync_listing.call_count == 2
            # Verify sync_listing was called for active listings
            called_listings = [call.args[0] for call in mock_sync_listing.call_args_list]
            assert l1 in called_listings
            assert l2 in called_listings
            assert l3 not in called_listings

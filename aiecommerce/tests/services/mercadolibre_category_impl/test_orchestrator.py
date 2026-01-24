from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_category_impl.orchestrator import MercadolibreEnrichmentCategoryOrchestrator
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestMercadolibreEnrichmentCategoryOrchestrator:
    @pytest.fixture
    def mock_selector(self):
        return MagicMock()

    @pytest.fixture
    def mock_category_predictor(self):
        return MagicMock()

    @pytest.fixture
    def mock_price_engine(self):
        return MagicMock()

    @pytest.fixture
    def mock_stock_engine(self):
        return MagicMock()

    @pytest.fixture
    def mock_attribute_fetcher(self):
        return MagicMock()

    @pytest.fixture
    def mock_attribute_filler(self):
        return MagicMock()

    @pytest.fixture
    def orchestrator(
        self,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
        mock_attribute_fetcher,
        mock_attribute_filler,
    ):
        return MercadolibreEnrichmentCategoryOrchestrator(
            selector=mock_selector,
            category_predictor=mock_category_predictor,
            price_engine=mock_price_engine,
            stock_engine=mock_stock_engine,
            attribute_fetcher=mock_attribute_fetcher,
            attribute_filler=mock_attribute_filler,
        )

    def test_run_no_products(self, orchestrator, mock_selector):
        mock_selector.get_queryset.return_value.count.return_value = 0

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 0, "processed": 0}
        mock_selector.get_queryset.assert_called_once_with(False, False, None)

    def test_run_success(
        self,
        orchestrator,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
        mock_attribute_fetcher,
        mock_attribute_filler,
    ):
        product = ProductMasterFactory(seo_title="Some Title", price=Decimal("100.00"))
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]

        mock_category_predictor.predict_category.return_value = "ML123"
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 10
        mock_attribute_fetcher.get_category_attributes.return_value = [{"id": "ATTR1"}]
        mock_attribute_filler.fill_and_validate.return_value = [{"id": "ATTR1", "value_name": "Val"}]

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 1, "processed": 1}

        listing = MercadoLibreListing.objects.get(product_master=product)
        assert listing.category_id == "ML123"
        assert listing.final_price == Decimal("150.00")
        assert listing.available_quantity == 10
        assert listing.attributes == [{"id": "ATTR1", "value_name": "Val"}]

    def test_run_dry_run(
        self,
        orchestrator,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
    ):
        product = ProductMasterFactory(seo_title="Some Title", price=Decimal("100.00"))
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]

        mock_category_predictor.predict_category.return_value = "ML123"
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 10

        stats = orchestrator.run(force=False, dry_run=True, delay=0)

        assert stats == {"total": 1, "processed": 1}

        # In dry run, listing might be created (get_or_create) but not saved with category_id
        listing = MercadoLibreListing.objects.get(product_master=product)
        assert listing.category_id is None

    def test_run_skips_no_seo_title(self, orchestrator, mock_selector, caplog):
        product = ProductMasterFactory(seo_title=None)
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 1, "processed": 0}
        assert f"Product {product.code} has no SEO title, skipping category prediction." in caplog.text
        assert MercadoLibreListing.objects.filter(product_master=product).count() == 0

    def test_run_skips_price_calculation_no_price(self, orchestrator, mock_selector, mock_category_predictor, mock_price_engine, caplog):
        product = ProductMasterFactory(seo_title="Title", price=None)
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]
        mock_category_predictor.predict_category.return_value = "ML123"

        orchestrator.run(force=False, dry_run=False, delay=0)

        mock_price_engine.calculate.assert_not_called()
        assert f"Product {product.code} has no price, skipping price calculation for listing." in caplog.text

    def test_run_exception_handling(self, orchestrator, mock_selector, mock_category_predictor, mock_price_engine, mock_stock_engine, mock_attribute_fetcher, mock_attribute_filler, caplog):
        p1 = ProductMasterFactory(seo_title="P1", price=Decimal("100"))
        p2 = ProductMasterFactory(seo_title="P2", price=Decimal("100"))
        mock_selector.get_queryset.return_value.count.return_value = 2
        mock_selector.get_queryset.return_value.iterator.return_value = [p1, p2]

        mock_category_predictor.predict_category.side_effect = [Exception("Boom"), "ML123"]
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 10
        mock_attribute_fetcher.get_category_attributes.return_value = []
        mock_attribute_filler.fill_and_validate.return_value = []

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 2, "processed": 1}
        assert "AI enrichment crashed - Boom" in caplog.text

    def test_run_category_none_skips_attribute_steps(
        self,
        orchestrator,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
        mock_attribute_fetcher,
        mock_attribute_filler,
    ):
        product = ProductMasterFactory(seo_title="Title", price=Decimal("100.00"))
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]
        mock_category_predictor.predict_category.return_value = None
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 5

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 1, "processed": 1}
        mock_attribute_fetcher.get_category_attributes.assert_not_called()
        mock_attribute_filler.fill_and_validate.assert_not_called()

        listing = MercadoLibreListing.objects.get(product_master=product)
        assert listing.category_id is None
        assert listing.final_price == Decimal("150.00")
        assert listing.available_quantity == 5
        assert listing.attributes is None

    def test_run_updates_existing_listing(
        self,
        orchestrator,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
        mock_attribute_fetcher,
        mock_attribute_filler,
    ):
        product = ProductMasterFactory(seo_title="Title", price=Decimal("100.00"))
        existing_listing = MercadoLibreListing.objects.create(
            product_master=product,
            category_id="OLD",
            final_price=Decimal("10.00"),
            available_quantity=1,
        )
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]
        mock_category_predictor.predict_category.return_value = "ML123"
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 10
        mock_attribute_fetcher.get_category_attributes.return_value = [{"id": "ATTR1"}]
        mock_attribute_filler.fill_and_validate.return_value = [{"id": "ATTR1", "value_name": "Val"}]

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 1, "processed": 1}
        existing_listing.refresh_from_db()
        assert existing_listing.category_id == "ML123"
        assert existing_listing.final_price == Decimal("150.00")
        assert existing_listing.available_quantity == 10
        assert existing_listing.attributes == [{"id": "ATTR1", "value_name": "Val"}]

    def test_run_dry_run_does_not_persist_updates(
        self,
        orchestrator,
        mock_selector,
        mock_category_predictor,
        mock_price_engine,
        mock_stock_engine,
    ):
        product = ProductMasterFactory(seo_title="Title", price=Decimal("100.00"))
        listing = MercadoLibreListing.objects.create(
            product_master=product,
            category_id="OLD",
            final_price=Decimal("10.00"),
            available_quantity=1,
        )
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [product]
        mock_category_predictor.predict_category.return_value = "ML123"
        mock_price_engine.calculate.return_value = {
            "final_price": Decimal("150.00"),
            "net_price": Decimal("130.00"),
            "profit": Decimal("20.00"),
        }
        mock_stock_engine.get_available_quantity.return_value = 10

        stats = orchestrator.run(force=False, dry_run=True, delay=0)

        assert stats == {"total": 1, "processed": 1}
        listing.refresh_from_db()
        assert listing.category_id == "OLD"
        assert listing.final_price == Decimal("10.00")
        assert listing.available_quantity == 1

    @patch("time.sleep", return_value=None)
    def test_run_with_delay(self, mock_sleep, orchestrator, mock_selector, mock_category_predictor):
        p1 = ProductMasterFactory(seo_title="P1")
        mock_selector.get_queryset.return_value.count.return_value = 1
        mock_selector.get_queryset.return_value.iterator.return_value = [p1]
        mock_category_predictor.predict_category.return_value = "ML123"

        orchestrator.run(force=False, dry_run=False, delay=1.0)

        mock_sleep.assert_called_once_with(1.0)

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter


@pytest.mark.django_db
class TestMercadoLibreFilter:
    def setup_method(self):
        # Mock settings for testing
        self.original_rules = getattr(settings, "MERCADOLIBRE_PUBLICATION_RULES", {})
        self.original_threshold = getattr(settings, "MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS", 24)

        settings.MERCADOLIBRE_PUBLICATION_RULES = {"Electronics": {"price_threshold": 100}, "Laptops": {"price_threshold": 500}}
        settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS = 24

    def teardown_method(self):
        settings.MERCADOLIBRE_PUBLICATION_RULES = self.original_rules
        settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS = self.original_threshold

    def test_is_eligible_freshness_logic(self):
        filter_service = MercadoLibreFilter()

        # Product just on the edge of freshness
        now = timezone.now()
        fresh_product = ProductMaster.objects.create(
            code="P1",
            description="Fresh Product",
            price=150,
            category="Electronics",
            is_active=True,
        )
        ProductMaster.objects.filter(id=fresh_product.id).update(last_updated=now - timedelta(hours=23, minutes=59))
        fresh_product.refresh_from_db()

        old_product = ProductMaster.objects.create(
            code="P2",
            description="Old Product",
            price=150,
            category="Electronics",
            is_active=True,
        )
        ProductMaster.objects.filter(id=old_product.id).update(last_updated=now - timedelta(hours=24, minutes=1))
        old_product.refresh_from_db()

        assert filter_service.is_eligible(fresh_product) is True
        assert filter_service.is_eligible(old_product) is False

    def test_is_eligible_none_handling(self):
        filter_service = MercadoLibreFilter()

        product_no_price = ProductMaster.objects.create(code="P3", price=None, category="Electronics", is_active=True)
        assert filter_service.is_eligible(product_no_price) is False

        product_no_category = ProductMaster.objects.create(code="P4", price=150, category=None, is_active=True)
        assert filter_service.is_eligible(product_no_category) is False

    def test_category_matching_not_brittle(self):
        # Substring match issue: "Car" should NOT match "Cartoons"
        rules = {"Car": {"price_threshold": 100}}
        filter_service = MercadoLibreFilter(publication_rules=rules)

        product = ProductMaster.objects.create(code="P5", price=150, category="Cartoons", is_active=True)

        # Freshness is also required
        now = timezone.now()
        ProductMaster.objects.filter(id=product.id).update(last_updated=now)
        product.refresh_from_db()

        # This should now return False because "Car" != "Cartoons"
        assert filter_service.is_eligible(product) is False

        # Should match if it's exact match (case-insensitive)
        product.category = "car"
        product.save()
        assert filter_service.is_eligible(product) is True

    def test_handles_simple_threshold_rules(self):
        # Support both dict and simple float/int
        rules = {"Electronics": 1000.0}
        filter_service = MercadoLibreFilter(publication_rules=rules)

        product = ProductMaster.objects.create(code="P6", price=1500, category="Electronics", is_active=True)
        assert filter_service.is_eligible(product) is True

        product.price = 500
        product.save()
        assert filter_service.is_eligible(product) is False

    def test_get_eligible_products_efficiency(self):
        rules = {"Electronics": 100, "Laptops": {"price_threshold": 500}}
        filter_service = MercadoLibreFilter(publication_rules=rules, freshness_threshold_hours=24)

        # Create eligible products
        ProductMaster.objects.create(code="E1", price=200, category="Electronics", is_active=True, model_name="M1", sku="S1", seo_title="T1")
        ProductMaster.objects.create(code="L1", price=600, category="Laptops", is_active=True, model_name="M2", sku="S2", seo_title="T2")

        # Create ineligible products
        ProductMaster.objects.create(code="E2", price=50, category="Electronics", is_active=True, model_name="M3", sku="S3", seo_title="T3")
        ProductMaster.objects.create(code="L2", price=400, category="Laptops", is_active=True, model_name="M4", sku="S4", seo_title="T4")
        ProductMaster.objects.create(code="E3", price=200, category="Electronics", is_active=False, model_name="M5", sku="S5", seo_title="T5")

        eligible = filter_service.get_eligible_products()
        assert eligible.count() == 2
        codes = set(eligible.values_list("code", flat=True))
        assert codes == {"E1", "L1"}

    def test_get_eligible_products_empty_rules(self):
        filter_service = MercadoLibreFilter(publication_rules={}, freshness_threshold_hours=24)
        ProductMaster.objects.create(
            code="E1",
            price=200,
            category="Electronics",
            is_active=True,
            model_name="M1",
            sku="S1",
            seo_title="T1",
        )

        eligible = filter_service.get_eligible_products()
        assert eligible.count() == 0

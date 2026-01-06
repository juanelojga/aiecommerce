import pytest

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector


@pytest.mark.django_db
class TestEnrichmentCandidateSelector:
    def setup_method(self):
        # Active items
        # p1: Active, specs=None, sku="SKU1" -> Should be included (specs is None)
        self.p1 = ProductMaster.objects.create(code="A1", category="Electronics", is_active=True, specs=None, sku="SKU1")
        # p2: Active, specs={}, sku="SKU2" -> Should be included (specs is {})
        self.p2 = ProductMaster.objects.create(code="A2", category="Home", is_active=True, specs={}, sku="SKU2")
        # p3: Active, specs={"color": "red"}, sku="SKU3" -> Should be excluded (has specs AND sku)
        self.p3 = ProductMaster.objects.create(code="A3", category="electronics - Gadgets", is_active=True, specs={"color": "red"}, sku="SKU3")
        # p6: Active, specs={"color": "blue"}, sku=None -> Should be included (sku is None)
        self.p6 = ProductMaster.objects.create(code="A6", category="Electronics", is_active=True, specs={"color": "blue"}, sku=None)

        # Inactive items (should be excluded in all cases)
        self.p4 = ProductMaster.objects.create(code="A4", category="Electronics", is_active=False, specs=None, sku="SKU4")
        self.p5 = ProductMaster.objects.create(code="A5", category="Home", is_active=False, specs={"x": 1}, sku="SKU5")

        self.selector = EnrichmentCandidateSelector()

    def test_default_filters_active_and_missing_specs_or_sku(self):
        qs = self.selector.get_queryset(force=False, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # Should include A1 (specs=None), A2 (specs={}), A6 (sku=None)
        assert set(ids) == {"A1", "A2", "A6"}, ids

    def test_force_includes_active_regardless_of_specs_or_sku(self):
        qs = self.selector.get_queryset(force=True, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # All active items regardless of specs/sku
        assert set(ids) == {"A1", "A2", "A3", "A6"}, ids

    def test_dry_run_limits_to_three(self):
        # dry_run returns early after applying only is_active filter
        qs = self.selector.get_queryset(force=False, dry_run=True)
        assert qs.count() <= 3
        # Should be the first 3 active products by ID
        ids = list(qs.values_list("code", flat=True))
        expected = ["A1", "A2", "A3"]  # Since they are created in this order
        assert ids == expected, ids

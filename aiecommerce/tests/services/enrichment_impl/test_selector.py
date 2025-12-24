import pytest

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector


@pytest.mark.django_db
class TestEnrichmentCandidateSelector:
    def setup_method(self):
        # Active items
        self.p1 = ProductMaster.objects.create(code="A1", category="Electronics", is_active=True, specs=None)
        self.p2 = ProductMaster.objects.create(code="A2", category="Home", is_active=True, specs={})
        self.p3 = ProductMaster.objects.create(code="A3", category="electronics - Gadgets", is_active=True, specs={"color": "red"})

        # Inactive items (should be excluded in all cases)
        self.p4 = ProductMaster.objects.create(code="A4", category="Electronics", is_active=False, specs=None)
        self.p5 = ProductMaster.objects.create(code="A5", category="Home", is_active=False, specs={"x": 1})

        self.selector = EnrichmentCandidateSelector()

    def test_default_filters_active_and_missing_specs(self):
        qs = self.selector.get_queryset(category_filter=None, force=False, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # Should include only active with specs is null or empty dict, ordered by id/creation
        assert ids == ["A1", "A2"], ids

    def test_force_includes_active_regardless_of_specs(self):
        qs = self.selector.get_queryset(category_filter=None, force=True, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # All active items regardless of specs, ordered by id/creation
        assert ids == ["A1", "A2", "A3"], ids

    def test_category_filter_is_icontains_and_combines_with_specs_filter(self):
        # With force=False, should include only items in categories containing 'electronic' and missing specs
        qs = self.selector.get_queryset(category_filter="electronic", force=False, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # p1 matches category and has missing specs; p3 matches category but has specs -> excluded
        assert ids == ["A1"], ids

    def test_dry_run_limits_to_three_and_skips_specs_filtering(self):
        # dry_run returns early after applying only is_active and optional category filters, not specs filtering
        qs = self.selector.get_queryset(category_filter=None, force=False, dry_run=True)
        ids = list(qs.values_list("code", flat=True))
        # First three active products by id: A1, A2, A3 (even though A3 has specs)
        assert ids == ["A1", "A2", "A3"], ids

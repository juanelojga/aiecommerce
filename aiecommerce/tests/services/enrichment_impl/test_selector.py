import pytest

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector


@pytest.mark.django_db
class TestEnrichmentCandidateSelector:
    def setup_method(self):
        # Active items
        # p1: Active, specs=None, price=10.0, category="Electronics" -> Should be included (specs is None)
        self.p1 = ProductMaster.objects.create(code="A1", category="Electronics", is_active=True, specs=None, normalized_name="N1", model_name="M1", price=10.0, is_for_mercadolibre=True)
        # p2: Active, specs={}, price=20.0, category="Home" -> Should be included (specs is {})
        self.p2 = ProductMaster.objects.create(code="A2", category="Home", is_active=True, specs={}, normalized_name="N2", model_name="M2", price=20.0, is_for_mercadolibre=True)
        # p3: Active, specs={"color": "red"}, price=30.0, category="Gadgets", normalized_name="N3", model_name="M3" -> Should be excluded (everything present)
        self.p3 = ProductMaster.objects.create(code="A3", category="Gadgets", is_active=True, specs={"color": "red"}, price=30.0, normalized_name="N3", model_name="M3", is_for_mercadolibre=True)
        # p6: Active, specs={"color": "blue"}, price=40.0, category="Electronics", normalized_name=None -> Should be included (normalized_name is None)
        self.p6 = ProductMaster.objects.create(code="A6", category="Electronics", is_active=True, specs={"color": "blue"}, price=40.0, normalized_name=None, model_name="M6", is_for_mercadolibre=True)
        # p7: Active, specs={"color": "green"}, price=50.0, category="Electronics", model_name="" -> Should be included (model_name is empty)
        self.p7 = ProductMaster.objects.create(code="A7", category="Electronics", is_active=True, specs={"color": "green"}, price=50.0, normalized_name="N7", model_name="", is_for_mercadolibre=True)

        # Inactive items (should be excluded in all cases)
        self.p4 = ProductMaster.objects.create(code="A4", category="Electronics", is_active=False, specs=None, price=50.0)
        self.p5 = ProductMaster.objects.create(code="A5", category="Home", is_active=False, specs={"x": 1}, price=60.0)

        self.selector = EnrichmentCandidateSelector()

    def test_default_filters_active_and_missing_specs_or_names(self):
        qs = self.selector.get_queryset(force=False, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # Should include A1 (specs=None), A2 (specs={}), A6 (normalized_name=None), A7 (model_name="")
        assert set(ids) == {"A1", "A2", "A6", "A7"}, ids

    def test_force_includes_active_regardless_of_specs_or_names(self):
        qs = self.selector.get_queryset(force=True, dry_run=False)
        ids = list(qs.values_list("code", flat=True))
        # All active items regardless of specs/names
        assert set(ids) == {"A1", "A2", "A3", "A6", "A7"}, ids

    def test_dry_run_limits_to_three(self):
        # dry_run returns early after applying only is_active filter
        qs = self.selector.get_queryset(force=False, dry_run=True)
        assert qs.count() <= 3
        # Should be the first 3 active products by ID
        ids = list(qs.values_list("code", flat=True))
        expected = ["A1", "A2", "A3"]  # Since they are created in this order
        assert ids == expected, ids

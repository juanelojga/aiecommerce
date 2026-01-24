from datetime import timedelta
from decimal import Decimal

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from aiecommerce.models import ProductMaster
from aiecommerce.services.update_ml_eligibility_impl.selector import UpdateMlEligibilityCandidateSelector


@override_settings(
    MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS=24,
    MERCADOLIBRE_PUBLICATION_RULES={
        "NOTEBOOK": {"price_threshold": Decimal("1000.00")},
        " MONITOR ": Decimal("10.00"),
        "SKIP": {"price_threshold": None},
    },
)
class TestUpdateMlEligibilityCandidateSelector(TransactionTestCase):
    def setUp(self):
        self.selector = UpdateMlEligibilityCandidateSelector()
        self.now = timezone.now()

    def _create_product(self, **kwargs) -> ProductMaster:
        last_updated = kwargs.pop("last_updated", self.now)
        defaults = {
            "code": "CODE",
            "is_active": True,
            "price": Decimal("1500.00"),
            "category": "NOTEBOOK",
            "stock_principal": "Si",
            "stock_colon": "Si",
            "stock_sur": "No",
            "stock_gye_norte": "No",
            "stock_gye_sur": "No",
            "is_for_mercadolibre": False,
        }
        product = ProductMaster.objects.create(**{**defaults, **kwargs})
        ProductMaster.objects.filter(pk=product.pk).update(last_updated=last_updated)
        product.refresh_from_db()
        return product

    def test_get_queryset_applies_base_filters_and_rules(self):
        eligible = self._create_product(code="ELIGIBLE")
        self._create_product(code="INACTIVE", is_active=False)
        self._create_product(code="NO_PRICE", price=None)
        self._create_product(code="NO_CATEGORY", category=None)
        self._create_product(code="OLD", last_updated=self.now - timedelta(hours=25))
        self._create_product(code="NO_PRINCIPAL", stock_principal="No")
        self._create_product(
            code="NO_BRANCH",
            stock_colon="No",
            stock_sur="No",
            stock_gye_norte="No",
            stock_gye_sur="No",
        )
        self._create_product(code="LOW_PRICE", price=Decimal("999.00"))

        qs = self.selector.get_queryset(force=False, dry_run=False)
        codes = list(qs.values_list("code", flat=True))

        assert codes == [eligible.code]

    def test_force_includes_mercadolibre_flagged_products(self):
        product = self._create_product(code="FORCED", is_for_mercadolibre=True)

        qs_default = self.selector.get_queryset(force=False, dry_run=False)
        codes_default = list(qs_default.values_list("code", flat=True))
        assert product.code not in codes_default

        qs_forced = self.selector.get_queryset(force=True, dry_run=False)
        codes_forced = list(qs_forced.values_list("code", flat=True))
        assert product.code in codes_forced

    def test_dry_run_returns_first_three_matching_products(self):
        self._create_product(code="P1")
        self._create_product(code="P2", is_for_mercadolibre=True)
        self._create_product(code="P3")
        self._create_product(code="P4")

        qs = self.selector.get_queryset(force=False, dry_run=True)
        codes = list(qs.values_list("code", flat=True))

        assert codes == ["P1", "P2", "P3"]

    def test_publication_rules_support_non_dict_values_and_strip_keys(self):
        self._create_product(code="NOTEBOOK_OK", category="notebook", price=Decimal("1000.00"))
        self._create_product(code="MONITOR_OK", category="monitor", price=Decimal("10.00"))
        self._create_product(code="SKIP_RULE", category="SKIP", price=Decimal("9999.00"))

        qs = self.selector.get_queryset(force=False, dry_run=False)
        codes = set(qs.values_list("code", flat=True))

        assert {"NOTEBOOK_OK", "MONITOR_OK"} <= codes
        assert "SKIP_RULE" not in codes

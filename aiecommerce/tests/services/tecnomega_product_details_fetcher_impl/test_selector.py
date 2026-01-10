import pytest

from aiecommerce.services.tecnomega_product_details_fetcher_impl.selector import TecnomegaDetailSelector
from aiecommerce.tests.factories import ProductMasterFactory

pytestmark = pytest.mark.django_db


class TestTecnomegaDetailSelector:
    @pytest.fixture
    def selector(self):
        return TecnomegaDetailSelector()

    def test_get_queryset_base_filters(self, selector):
        # Active, price, category
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Test")
        p2 = ProductMasterFactory(is_active=False, price=10.0, category="Test")
        p3 = ProductMasterFactory(is_active=True, price=None, category="Test")
        p4 = ProductMasterFactory(is_active=True, price=10.0, category=None)

        qs = selector.get_queryset(force=True, dry_run=False)

        assert p1 in qs
        assert p2 not in qs
        assert p3 not in qs
        assert p4 not in qs

    def test_get_queryset_dry_run(self, selector):
        # Limits to 3, orders by id
        products = [ProductMasterFactory(is_active=True, price=10.0, category="Test") for _ in range(5)]
        products.sort(key=lambda x: x.id)

        qs = selector.get_queryset(force=True, dry_run=True)

        assert list(qs) == products[:3]

    def test_get_queryset_force_false(self, selector):
        # Needs enrichment: sku is null or empty
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku=None)
        p2 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku="")
        p3 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku="SOME-SKU")

        qs = selector.get_queryset(force=False, dry_run=False)

        assert p1 in qs
        assert p2 in qs
        assert p3 not in qs

    def test_get_queryset_force_true(self, selector):
        # Bypasses enrichment check
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku=None)
        p2 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku="")
        p3 = ProductMasterFactory(is_active=True, price=10.0, category="Test", sku="SOME-SKU")

        qs = selector.get_queryset(force=True, dry_run=False)

        assert p1 in qs
        assert p2 in qs
        assert p3 in qs

    def test_get_queryset_ordering(self, selector):
        p1 = ProductMasterFactory(id=100, is_active=True, price=10.0, category="Test")
        p2 = ProductMasterFactory(id=50, is_active=True, price=10.0, category="Test")
        p3 = ProductMasterFactory(id=150, is_active=True, price=10.0, category="Test")

        qs = selector.get_queryset(force=True, dry_run=False)

        assert list(qs) == [p2, p1, p3]

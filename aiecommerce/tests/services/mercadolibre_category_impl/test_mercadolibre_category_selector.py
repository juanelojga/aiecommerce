import pytest

from aiecommerce.models import MercadoLibreListing, ProductMaster
from aiecommerce.services.mercadolibre_category_impl.selector import MercadolibreCategorySelector


@pytest.mark.django_db
class TestMercadolibreCategorySelector:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.selector = MercadolibreCategorySelector()

        # Create some products
        # 1. Active, ML, No listing
        self.p1 = ProductMaster.objects.create(code="P1", is_active=True, is_for_mercadolibre=True, category="cat-a")
        # 2. Active, ML, No listing
        self.p2 = ProductMaster.objects.create(code="P2", is_active=True, is_for_mercadolibre=True, category="cat-a")
        # 3. Active, ML, No listing
        self.p3 = ProductMaster.objects.create(code="P3", is_active=True, is_for_mercadolibre=True, category="cat-b")
        # 4. Active, ML, With listing
        self.p4 = ProductMaster.objects.create(code="P4", is_active=True, is_for_mercadolibre=True, category="cat-a")
        MercadoLibreListing.objects.create(product_master=self.p4, ml_id="ML4", status=MercadoLibreListing.Status.ACTIVE)

        # 5. Inactive, ML, No listing
        self.p5 = ProductMaster.objects.create(code="P5", is_active=False, is_for_mercadolibre=True, category="cat-a")

        # 6. Active, Not ML, No listing
        self.p6 = ProductMaster.objects.create(code="P6", is_active=True, is_for_mercadolibre=False, category="cat-a")

    def test_get_queryset_dry_run(self):
        # Should return max 3 items, ordered by ID, only active and ML
        # Expected: p1, p2, p3 (p4 is also active/ML but dry_run limits to 3)
        qs = self.selector.get_queryset(force=False, dry_run=True)
        assert qs.count() == 3
        ids = list(qs.values_list("id", flat=True))
        assert ids == sorted(ids)
        assert self.p1.id in ids
        assert self.p2.id in ids
        assert self.p3.id in ids
        assert self.p4.id not in ids
        assert self.p5.id not in ids
        assert self.p6.id not in ids

    def test_get_queryset_force_false(self):
        # Should return active, ML, without listing OR with listing in PENDING or ERROR status
        # Expected: p1, p2, p3, p7, p8

        # 7. Active, ML, With PENDING listing
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        # 8. Active, ML, With ERROR listing
        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b")
        MercadoLibreListing.objects.create(product_master=self.p8, ml_id="ML8", status=MercadoLibreListing.Status.ERROR)

        qs = self.selector.get_queryset(force=False, dry_run=False)
        ids = list(qs.values_list("id", flat=True))

        assert qs.count() == 5
        assert self.p1.id in ids
        assert self.p2.id in ids
        assert self.p3.id in ids
        assert self.p4.id not in ids
        assert self.p5.id not in ids
        assert self.p6.id not in ids
        assert self.p7.id in ids
        assert self.p8.id in ids

    def test_get_queryset_force_true(self):
        # Should return all active, ML, even with listing
        # Expected: p1, p2, p3, p4, p7, p8
        # 7. Active, ML, With PENDING listing
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        # 8. Active, ML, With ERROR listing
        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b")
        MercadoLibreListing.objects.create(product_master=self.p8, ml_id="ML8", status=MercadoLibreListing.Status.ERROR)

        qs = self.selector.get_queryset(force=True, dry_run=False)
        assert qs.count() == 6
        ids = list(qs.values_list("id", flat=True))
        assert self.p1.id in ids
        assert self.p2.id in ids
        assert self.p3.id in ids
        assert self.p4.id in ids
        assert self.p7.id in ids
        assert self.p8.id in ids
        assert self.p5.id not in ids
        assert self.p6.id not in ids

    def test_get_queryset_category_filter(self):
        # Should return only active ML products for the requested category.
        # Expected for cat-a: p1, p2, p7
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b")
        MercadoLibreListing.objects.create(product_master=self.p8, ml_id="ML8", status=MercadoLibreListing.Status.ERROR)

        qs = self.selector.get_queryset(force=False, dry_run=False, category="cat-a")
        ids = list(qs.values_list("id", flat=True))

        assert qs.count() == 3
        assert self.p1.id in ids
        assert self.p2.id in ids
        assert self.p7.id in ids
        assert self.p3.id not in ids
        assert self.p4.id not in ids
        assert self.p5.id not in ids
        assert self.p6.id not in ids
        assert self.p8.id not in ids

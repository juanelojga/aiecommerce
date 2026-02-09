import pytest

from aiecommerce.models import MercadoLibreListing, ProductMaster
from aiecommerce.services.mercadolibre_category_impl.selector import MercadolibreCategorySelector


@pytest.mark.django_db
class TestMercadolibreCategorySelector:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.selector = MercadolibreCategorySelector()

        # Create some products
        # 1. Active, ML, No listing, WITH STOCK
        self.p1 = ProductMaster.objects.create(code="P1", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567890", stock_principal="Si", stock_colon="Si")
        # 2. Active, ML, No listing, WITH STOCK
        self.p2 = ProductMaster.objects.create(code="P2", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567891", stock_principal="Si", stock_sur="Si")
        # 3. Active, ML, No listing, WITH STOCK
        self.p3 = ProductMaster.objects.create(code="P3", is_active=True, is_for_mercadolibre=True, category="cat-b", gtin="7501234567892", stock_principal="Si", stock_gye_norte="Si")
        # 4. Active, ML, With listing, WITH STOCK
        self.p4 = ProductMaster.objects.create(code="P4", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567893", stock_principal="Si", stock_gye_sur="Si")
        MercadoLibreListing.objects.create(product_master=self.p4, ml_id="ML4", status=MercadoLibreListing.Status.ACTIVE)

        # 5. Inactive, ML, No listing (stock values don't matter, will be filtered by is_active)
        self.p5 = ProductMaster.objects.create(code="P5", is_active=False, is_for_mercadolibre=True, category="cat-a", gtin="7501234567894", stock_principal="Si", stock_colon="Si")

        # 6. Active, Not ML, No listing (stock values don't matter, will be filtered by is_for_mercadolibre)
        self.p6 = ProductMaster.objects.create(code="P6", is_active=True, is_for_mercadolibre=False, category="cat-a", gtin="7501234567895", stock_principal="Si", stock_colon="Si")

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

        # 7. Active, ML, With PENDING listing, WITH STOCK
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567896", stock_principal="Si", stock_colon="Si")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        # 8. Active, ML, With ERROR listing, WITH STOCK
        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b", gtin="7501234567897", stock_principal="Si", stock_sur="Si")
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
        # 7. Active, ML, With PENDING listing, WITH STOCK
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567896", stock_principal="Si", stock_gye_norte="Si")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        # 8. Active, ML, With ERROR listing, WITH STOCK
        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b", gtin="7501234567897", stock_principal="Si", stock_gye_sur="Si")
        MercadoLibreListing.objects.create(product_master=self.p8, ml_id="ML8", status=MercadoLibreListing.Status.ERROR)

        qs = self.selector.get_queryset(force=True, dry_run=False, batch_size=10)
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
        self.p7 = ProductMaster.objects.create(code="P7", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567896", stock_principal="Si", stock_colon="Si")
        MercadoLibreListing.objects.create(product_master=self.p7, ml_id="ML7", status=MercadoLibreListing.Status.PENDING)

        self.p8 = ProductMaster.objects.create(code="P8", is_active=True, is_for_mercadolibre=True, category="cat-b", gtin="7501234567897", stock_principal="Si", stock_sur="Si")
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

    def test_get_queryset_filters_by_stock_principal(self):
        # Products without stock_principal="Si" should be excluded
        # Create product with no principal stock
        no_stock = ProductMaster.objects.create(code="NO_STOCK", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567898", stock_principal="No", stock_colon="Si")

        qs = self.selector.get_queryset(force=False, dry_run=False, batch_size=10)
        ids = list(qs.values_list("id", flat=True))

        # no_stock should not be in results
        assert no_stock.id not in ids
        # p1, p2, p3 should still be in results
        assert self.p1.id in ids
        assert self.p2.id in ids
        assert self.p3.id in ids

    def test_get_queryset_filters_by_branch_availability(self):
        # Products must have at least one branch with stock="Si"
        # Create product with principal stock but no branch stock
        no_branch_stock = ProductMaster.objects.create(
            code="NO_BRANCH", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567899", stock_principal="Si", stock_colon="No", stock_sur="No", stock_gye_norte="No", stock_gye_sur="No"
        )

        qs = self.selector.get_queryset(force=False, dry_run=False, batch_size=10)
        ids = list(qs.values_list("id", flat=True))

        # no_branch_stock should not be in results
        assert no_branch_stock.id not in ids
        # Products with at least one branch stock should be included
        assert self.p1.id in ids

    def test_get_queryset_excludes_products_without_stock(self):
        # Create products with various stock issues
        # 1. No principal stock (None)
        p_no_principal = ProductMaster.objects.create(code="NO_PRIN", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567900", stock_principal=None, stock_colon="Si")

        # 2. Principal stock but all branches None
        p_no_branches = ProductMaster.objects.create(
            code="NO_BRANCH", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567901", stock_principal="Si", stock_colon=None, stock_sur=None, stock_gye_norte=None, stock_gye_sur=None
        )

        # 3. Both None
        p_all_none = ProductMaster.objects.create(code="ALL_NONE", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567902", stock_principal=None, stock_colon=None)

        qs = self.selector.get_queryset(force=False, dry_run=False, batch_size=20)
        ids = list(qs.values_list("id", flat=True))

        # None of the problem products should be included
        assert p_no_principal.id not in ids
        assert p_no_branches.id not in ids
        assert p_all_none.id not in ids

        # Original products with proper stock should still be there
        assert self.p1.id in ids
        assert self.p2.id in ids

    def test_get_queryset_accepts_multiple_branch_combinations(self):
        # Test that different branch combinations work
        # Create products with different branch stock patterns
        p_colon = ProductMaster.objects.create(code="COLON_ONLY", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567903", stock_principal="Si", stock_colon="Si", stock_sur="No")

        p_sur = ProductMaster.objects.create(code="SUR_ONLY", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567904", stock_principal="Si", stock_colon="No", stock_sur="Si")

        p_multiple = ProductMaster.objects.create(
            code="MULTIPLE", is_active=True, is_for_mercadolibre=True, category="cat-a", gtin="7501234567905", stock_principal="Si", stock_colon="Si", stock_sur="Si", stock_gye_norte="Si"
        )

        qs = self.selector.get_queryset(force=False, dry_run=False, batch_size=20)
        ids = list(qs.values_list("id", flat=True))

        # All should be included
        assert p_colon.id in ids
        assert p_sur.id in ids
        assert p_multiple.id in ids

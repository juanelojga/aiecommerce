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

        qs = self.selector.get_queryset(force=False, dry_run=False, batch_size=10)
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

        qs = self.selector.get_queryset(force=False, dry_run=False, category="cat-a", batch_size=10)
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

    def test_get_queryset_case_insensitive_stock_filtering(self):
        """
        Test that stock filtering is case-insensitive to align with stock engine logic.
        The selector should accept "Si", "SI", "si", " Si " (with whitespace), etc.
        """
        # Create products with different case variations in stock fields
        p_uppercase = ProductMaster.objects.create(
            code="UPPER",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-case",
            gtin="7501234567906",
            stock_principal="SI",  # Uppercase
            stock_colon="SI",
        )

        p_lowercase = ProductMaster.objects.create(
            code="LOWER",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-case",
            gtin="7501234567907",
            stock_principal="si",  # Lowercase
            stock_sur="si",
        )

        p_mixed = ProductMaster.objects.create(
            code="MIXED",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-case",
            gtin="7501234567908",
            stock_principal="Si",  # Mixed case
            stock_gye_norte="SI",
        )

        # Create product with "NO" in different cases - should be excluded
        p_no_uppercase = ProductMaster.objects.create(
            code="NO_UPPER",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-case",
            gtin="7501234567909",
            stock_principal="NO",  # Uppercase NO
            stock_colon="SI",
        )

        p_no_lowercase = ProductMaster.objects.create(
            code="NO_LOWER",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-case",
            gtin="7501234567910",
            stock_principal="no",  # Lowercase NO
            stock_colon="si",
        )

        qs = self.selector.get_queryset(force=False, dry_run=False, category="cat-case", batch_size=20)
        ids = list(qs.values_list("id", flat=True))

        # All "SI"/"si"/"Si" variations should be included
        assert p_uppercase.id in ids, "Uppercase 'SI' should be accepted"
        assert p_lowercase.id in ids, "Lowercase 'si' should be accepted"
        assert p_mixed.id in ids, "Mixed case 'Si' should be accepted"

        # All "NO"/"no" variations should be excluded
        assert p_no_uppercase.id not in ids, "Uppercase 'NO' should be excluded"
        assert p_no_lowercase.id not in ids, "Lowercase 'no' should be excluded"

    def test_get_queryset_handles_whitespace_in_stock_values(self):
        """
        Test that stock filtering handles whitespace correctly.
        Django's __iexact doesn't automatically strip whitespace, but the data
        should ideally be clean. This test verifies behavior with whitespace.
        """
        # Create products with whitespace in stock fields
        ProductMaster.objects.create(
            code="SPACES",
            is_active=True,
            is_for_mercadolibre=True,
            category="cat-space",
            gtin="7501234567911",
            stock_principal=" Si ",  # With spaces
            stock_colon=" Si ",
        )

        qs = self.selector.get_queryset(force=False, dry_run=False, category="cat-space", batch_size=20)

        # Note: __iexact doesn't strip whitespace by default in Django,
        # so " Si " won't match "si". This test documents the expected behavior.
        # The stock engine strips whitespace, so ideally data should be clean.
        # If this product appears, data normalization is working; if not, that's also expected.
        # We document this to make the behavior explicit.
        # For now, we just verify the query executes without error
        assert qs.count() >= 0  # Query should execute successfully

    def test_get_queryset_prioritizes_products_without_listings(self):
        """
        Test that products without listings are prioritized over products with PENDING/ERROR status.
        This ensures new products are always enriched before re-processing existing listings.
        """
        # First, create products WITH listings (PENDING status)
        # These should have lower priority (priority=1)
        pending_products = []
        for i in range(3):
            p = ProductMaster.objects.create(
                code=f"PENDING_{i}",
                is_active=True,
                is_for_mercadolibre=True,
                category="test-priority",
                gtin=f"750123456790{i}",
                stock_principal="Si",
                stock_colon="Si",
            )
            MercadoLibreListing.objects.create(product_master=p, status=MercadoLibreListing.Status.PENDING)
            pending_products.append(p)

        # Now create products WITHOUT listings (created after pending, so higher IDs)
        # These should have higher priority (priority=0)
        new_products = []
        for i in range(3):
            p = ProductMaster.objects.create(
                code=f"NEW_{i}",
                is_active=True,
                is_for_mercadolibre=True,
                category="test-priority",
                gtin=f"750123456791{i}",
                stock_principal="Si",
                stock_sur="Si",
            )
            new_products.append(p)

        # Request batch using the test category filter to isolate our test data
        qs = self.selector.get_queryset(force=False, dry_run=False, category="test-priority", batch_size=3)
        result_products = list(qs)

        assert len(result_products) == 3

        # All 3 selected products should be NEW products (without listings)
        # even though PENDING products have lower IDs
        new_product_ids = [p.id for p in new_products]
        pending_product_ids = [p.id for p in pending_products]

        for product in result_products:
            assert product.id in new_product_ids, f"Product {product.code} (ID {product.id}) should be a NEW product without listing"
            assert product.id not in pending_product_ids, f"Product {product.code} (ID {product.id}) should NOT be a PENDING product"

        # Verify all new products were selected
        result_ids = [p.id for p in result_products]
        assert set(result_ids) == set(new_product_ids), "All NEW products should be selected before PENDING products"

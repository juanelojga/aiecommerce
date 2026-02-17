"""Tests for GTINEnrichmentCandidateSelector."""

import pytest
from django.utils import timezone

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_enrichment_impl.selector import GTINEnrichmentCandidateSelector


@pytest.mark.django_db
class TestGTINEnrichmentCandidateSelector:
    """Test suite for GTINEnrichmentCandidateSelector."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Base timestamp for ordering tests
        base_time = timezone.now()

        # Product 1: Should be included (active, for ML, no GTIN, no gtin_source)
        self.p1 = ProductMaster.objects.create(
            code="P1",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
        )

        # Product 2: Should be included (active, for ML, no GTIN, gtin_source is empty string)
        self.p2 = ProductMaster.objects.create(
            code="P2",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="",
        )

        # Product 3: Should be EXCLUDED (gtin_source is NOT_FOUND)
        self.p3 = ProductMaster.objects.create(
            code="P3",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="NOT_FOUND",
        )

        # Product 4: Should be EXCLUDED (already has GTIN)
        self.p4 = ProductMaster.objects.create(
            code="P4",
            is_active=True,
            is_for_mercadolibre=True,
            gtin="1234567890123",
            gtin_source="sku_normalized_name",
        )

        # Product 5: Should be EXCLUDED (not active)
        self.p5 = ProductMaster.objects.create(
            code="P5",
            is_active=False,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
        )

        # Product 6: Should be EXCLUDED (not for MercadoLibre)
        self.p6 = ProductMaster.objects.create(
            code="P6",
            is_active=True,
            is_for_mercadolibre=False,
            gtin=None,
            gtin_source=None,
        )

        # Product 7: Should be included (active, for ML, no GTIN, different gtin_source)
        self.p7 = ProductMaster.objects.create(
            code="P7",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="model_brand",  # Has source but no GTIN (edge case)
        )

        # Update timestamps using QuerySet.update() to bypass auto_now
        # This allows us to set specific last_updated values for testing ordering
        ProductMaster.objects.filter(code="P1").update(last_updated=base_time)
        ProductMaster.objects.filter(code="P2").update(last_updated=base_time - timezone.timedelta(days=1))
        ProductMaster.objects.filter(code="P7").update(last_updated=base_time - timezone.timedelta(days=6))

        self.selector = GTINEnrichmentCandidateSelector()

    def test_get_batch_returns_only_eligible_products(self):
        """Test that get_batch returns only products that meet all criteria."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        # Should include P1, P2, P7 (all eligible)
        # Should exclude P3 (NOT_FOUND), P4 (has GTIN), P5 (inactive), P6 (not for ML)
        assert set(codes) == {"P1", "P2", "P7"}, f"Expected P1, P2, P7 but got {codes}"

    def test_get_batch_excludes_not_found_sources(self):
        """Test that products with gtin_source='NOT_FOUND' are excluded."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        assert "P3" not in codes, "Product with NOT_FOUND source should be excluded"

    def test_get_batch_excludes_products_with_gtin(self):
        """Test that products that already have a GTIN are excluded."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        assert "P4" not in codes, "Product with GTIN should be excluded"

    def test_get_batch_excludes_inactive_products(self):
        """Test that inactive products are excluded."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        assert "P5" not in codes, "Inactive product should be excluded"

    def test_get_batch_excludes_non_mercadolibre_products(self):
        """Test that products not for MercadoLibre are excluded."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        assert "P6" not in codes, "Product not for ML should be excluded"

    def test_get_batch_orders_by_last_updated(self):
        """Test that results are ordered by last_updated (oldest first)."""
        qs = self.selector.get_batch(limit=10)
        codes = list(qs.values_list("code", flat=True))

        # Expected order: P7 (oldest), P2, P1 (newest)
        assert codes == ["P7", "P2", "P1"], f"Expected P7, P2, P1 but got {codes}"

    def test_get_batch_respects_limit(self):
        """Test that the limit parameter works correctly."""
        # Create additional eligible products
        base_time = timezone.now()
        for i in range(10):
            ProductMaster.objects.create(
                code=f"EXTRA{i}",
                is_active=True,
                is_for_mercadolibre=True,
                gtin=None,
                gtin_source=None,
            )

        # Update their timestamps to be older
        for i in range(10):
            ProductMaster.objects.filter(code=f"EXTRA{i}").update(last_updated=base_time - timezone.timedelta(days=10 + i))

        # Test with limit=2
        qs = self.selector.get_batch(limit=2)
        assert qs.count() == 2, f"Expected 2 products but got {qs.count()}"

        # Test with limit=5
        qs = self.selector.get_batch(limit=5)
        assert qs.count() == 5, f"Expected 5 products but got {qs.count()}"

    def test_get_batch_default_limit(self):
        """Test that default limit is 15."""
        # Create 20 eligible products
        base_time = timezone.now()
        for i in range(20):
            ProductMaster.objects.create(
                code=f"TEST{i}",
                is_active=True,
                is_for_mercadolibre=True,
                gtin=None,
                gtin_source=None,
            )

        # Update their timestamps
        for i in range(20):
            ProductMaster.objects.filter(code=f"TEST{i}").update(last_updated=base_time - timezone.timedelta(days=20 + i))

        # Call without limit argument
        qs = self.selector.get_batch()
        assert qs.count() == 15, f"Expected default limit of 15 but got {qs.count()}"

    def test_get_batch_returns_queryset(self):
        """Test that get_batch returns a QuerySet."""
        from django.db.models import QuerySet

        qs = self.selector.get_batch(limit=10)
        assert isinstance(qs, QuerySet), "get_batch should return a QuerySet"

    def test_get_batch_with_zero_eligible_products(self):
        """Test behavior when no products meet the criteria."""
        # Delete all eligible products
        ProductMaster.objects.filter(is_active=True, is_for_mercadolibre=True, gtin__isnull=True).exclude(gtin_source="NOT_FOUND").delete()

        qs = self.selector.get_batch(limit=10)
        assert qs.count() == 0, "Should return empty queryset when no eligible products"

    def test_get_batch_with_mixed_gtin_sources(self):
        """Test that products with various gtin_source values are handled correctly."""
        base_time = timezone.now()

        # Create products with different gtin_source values
        ProductMaster.objects.create(
            code="SOURCE1",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="sku_normalized_name",
        )

        ProductMaster.objects.create(
            code="SOURCE2",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="model_brand",
        )

        ProductMaster.objects.create(
            code="SOURCE3",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="raw_description",
        )

        # Update timestamps
        ProductMaster.objects.filter(code="SOURCE1").update(last_updated=base_time - timezone.timedelta(days=30))
        ProductMaster.objects.filter(code="SOURCE2").update(last_updated=base_time - timezone.timedelta(days=31))
        ProductMaster.objects.filter(code="SOURCE3").update(last_updated=base_time - timezone.timedelta(days=32))

        qs = self.selector.get_batch(limit=20)
        codes = set(qs.values_list("code", flat=True))

        # All these should be included (they don't have GTIN even though they have source)
        assert "SOURCE1" in codes
        assert "SOURCE2" in codes
        assert "SOURCE3" in codes
        # NOT_FOUND should still be excluded
        assert "P3" not in codes

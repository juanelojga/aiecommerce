from django.test import TestCase

from aiecommerce.services.gtin_search_impl.selector import GTINSearchSelector
from aiecommerce.tests.factories import ProductMasterFactory


class TestGTINSearchSelector(TestCase):
    def setUp(self):
        self.selector = GTINSearchSelector()

    def test_base_filters(self):
        # Active product with price and category
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics")
        # Inactive product
        p2 = ProductMasterFactory(is_active=False, price=10.0, category="Electronics")
        # Product without price
        p3 = ProductMasterFactory(is_active=True, price=None, category="Electronics")
        # Product without category
        p4 = ProductMasterFactory(is_active=True, price=10.0, category=None)

        qs = self.selector.get_queryset(force=True, dry_run=False)

        self.assertIn(p1, qs)
        self.assertNotIn(p2, qs)
        self.assertNotIn(p3, qs)
        self.assertNotIn(p4, qs)

    def test_dry_run_limits_results(self):
        # Create 5 valid products
        for i in range(5):
            ProductMasterFactory(is_active=True, price=10.0, category="Electronics", id=i + 1)

        qs = self.selector.get_queryset(force=False, dry_run=True)

        self.assertEqual(qs.count(), 3)
        self.assertEqual(list(qs.values_list("id", flat=True)), [1, 2, 3])

    def test_force_false_needs_enrichment(self):
        # Needs enrichment: gtin is null
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics", gtin=None)
        # Needs enrichment: gtin is empty string
        p2 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics", gtin="")
        # Needs enrichment: model_name is NOT null
        p3 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics", gtin="123", model_name="Some Model")
        # Does NOT need enrichment: gtin is set and model_name is null
        p4 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics", gtin="123", model_name=None)

        qs = self.selector.get_queryset(force=False, dry_run=False)

        self.assertIn(p1, qs)
        self.assertIn(p2, qs)
        self.assertIn(p3, qs)
        self.assertNotIn(p4, qs)

    def test_force_true_ignores_enrichment_needs(self):
        # Does NOT need enrichment according to standard rules
        p1 = ProductMasterFactory(is_active=True, price=10.0, category="Electronics", gtin="123", model_name=None)

        qs = self.selector.get_queryset(force=True, dry_run=False)

        self.assertIn(p1, qs)

    def test_ordering_by_id(self):
        p2 = ProductMasterFactory(id=20, is_active=True, price=10.0, category="Electronics")
        p1 = ProductMasterFactory(id=10, is_active=True, price=10.0, category="Electronics")

        qs = self.selector.get_queryset(force=True, dry_run=False)

        self.assertEqual(list(qs), [p1, p2])

import pytest
from model_bakery import baker

from aiecommerce.models.product import ProductImage, ProductMaster
from aiecommerce.services.mercadolibre_impl.image_candidate_selector import ImageCandidateSelector


@pytest.mark.django_db
class TestImageCandidateSelector:
    def test_find_products_without_images_basic(self):
        # Eligible product without images
        eligible = baker.make(ProductMaster, is_active=True, is_for_mercadolibre=True)

        # Product with images
        with_image = baker.make(ProductMaster, is_active=True, is_for_mercadolibre=True)
        baker.make(ProductImage, product=with_image)

        selector = ImageCandidateSelector()
        results = selector.find_products_without_images()

        assert results.count() == 1
        assert results.first() == eligible

    def test_find_products_without_images_limit(self):
        baker.make(ProductMaster, is_active=True, is_for_mercadolibre=True, _quantity=5)

        selector = ImageCandidateSelector()
        results = selector.find_products_without_images(limit=3)

        assert results.count() == 3

    def test_find_products_without_images_distinct(self):
        # Test that distinct() is working if multiple search criteria might match (though here it's simple)
        # More importantly, if it had multiple images and we filtered for isnull=False,
        # distinct would be important. For isnull=True it's less likely to duplicate but good to have.

        selector = ImageCandidateSelector()
        results = selector.find_products_without_images()

        assert results.count() == 1

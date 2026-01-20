import pytest

from aiecommerce.services.upscale_images_impl.selector import UpscaleHighResSelector
from aiecommerce.tests.factories import ProductDetailScrapeFactory, ProductImageFactory, ProductMasterFactory


@pytest.mark.django_db
class TestUpscaleHighResSelector:
    @pytest.fixture
    def selector(self):
        return UpscaleHighResSelector()

    def test_get_candidates_base_filtering(self, selector):
        # Product matching all criteria
        product_ok = ProductMasterFactory(is_active=True, price=10.0, category="Test Category", is_for_mercadolibre=True)
        ProductDetailScrapeFactory(product=product_ok, image_urls=["http://example.com/image.jpg"])

        # Product missing is_active
        ProductMasterFactory(is_active=False, price=10.0, category="Test", is_for_mercadolibre=True)

        # Product missing price
        ProductMasterFactory(is_active=True, price=None, category="Test", is_for_mercadolibre=True)

        # Product missing category
        ProductMasterFactory(is_active=True, price=10.0, category=None, is_for_mercadolibre=True)

        # Product not for mercadolibre
        ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=False)

        # Product missing detail_scrapes (image_urls)
        product_no_scrape = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
        # We don't create a ProductDetailScrape for this one

        # Product with detail_scrapes but image_urls is empty list
        product_empty_images = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
        ProductDetailScrapeFactory(product=product_empty_images, image_urls=[])

        candidates = selector.get_candidates()

        candidate_ids = list(candidates.values_list("id", flat=True))
        assert product_ok.id in candidate_ids
        assert product_empty_images.id in candidate_ids  # Because [] is not NULL
        assert product_no_scrape.id not in candidate_ids
        assert candidates.count() == 2

    def test_get_candidates_with_product_code(self, selector):
        product1 = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True, code="CODE1")
        ProductDetailScrapeFactory(product=product1, image_urls=["http://example.com/1.jpg"])

        product2 = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True, code="CODE2")
        ProductDetailScrapeFactory(product=product2, image_urls=["http://example.com/2.jpg"])

        candidates = selector.get_candidates(product_code="CODE1")

        assert candidates.count() == 1
        assert candidates.first() == product1

    def test_get_candidates_excludes_processed_images(self, selector):
        # Product without images (should be included as it doesn't have images__is_processed=True)
        product_no_images = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
        ProductDetailScrapeFactory(product=product_no_images, image_urls=["http://example.com/1.jpg"])

        # Product with unprocessed images
        product_unprocessed = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
        ProductDetailScrapeFactory(product=product_unprocessed, image_urls=["http://example.com/2.jpg"])
        ProductImageFactory(product=product_unprocessed, is_processed=False)

        # Product with processed images (should be excluded)
        product_processed = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
        ProductDetailScrapeFactory(product=product_processed, image_urls=["http://example.com/3.jpg"])
        ProductImageFactory(product=product_processed, is_processed=True)

        candidates = selector.get_candidates()

        assert candidates.count() == 2
        candidate_ids = [c.id for c in candidates]
        assert product_no_images.id in candidate_ids
        assert product_unprocessed.id in candidate_ids
        assert product_processed.id not in candidate_ids

    def test_get_candidates_multiple_results(self, selector):
        for i in range(3):
            p = ProductMasterFactory(is_active=True, price=10.0, category="Test", is_for_mercadolibre=True)
            ProductDetailScrapeFactory(product=p, image_urls=["http://example.com/image.jpg"])

        candidates = selector.get_candidates()
        assert candidates.count() == 3

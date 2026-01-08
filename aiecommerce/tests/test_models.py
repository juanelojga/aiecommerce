from decimal import Decimal

import pytest

from aiecommerce.tests.factories import (
    ProductDetailScrapeFactory,
    ProductImageFactory,
    ProductMasterFactory,
    ProductRawPDFFactory,
    ProductRawWebFactory,
)

pytestmark = pytest.mark.django_db


def test_product_raw_pdf_str():
    """Verify the __str__ method for ProductRawPDF returns the expected format."""
    pdf_product = ProductRawPDFFactory(raw_description="A test PDF product description")
    expected_str = f"PDF Row ({pdf_product.id}) - A test PDF product description"
    assert str(pdf_product) == expected_str


def test_product_raw_pdf_str_no_description():
    """Verify the __str__ method for ProductRawPDF handles no description."""
    pdf_product = ProductRawPDFFactory(raw_description=None)
    expected_str = f"PDF Row ({pdf_product.id}) - No description"
    assert str(pdf_product) == expected_str


def test_product_raw_web_str():
    """Verify the __str__ method for ProductRawWeb returns the expected format."""
    web_product = ProductRawWebFactory(distributor_code="TEST-SKU-123")
    expected_str = f"Web Scrape ({web_product.id}) - SKU: TEST-SKU-123"
    assert str(web_product) == expected_str


def test_product_raw_web_str_no_sku():
    """Verify the __str__ method for ProductRawWeb handles no SKU."""
    web_product = ProductRawWebFactory(distributor_code=None)
    expected_str = f"Web Scrape ({web_product.id}) - SKU: N/A"
    assert str(web_product) == expected_str


def test_product_master_str():
    """Verify the __str__ method for ProductMaster returns the expected format."""
    master_product = ProductMasterFactory(code="MASTER-SKU-456", description="A master product for testing")
    expected_str = "Master: MASTER-SKU-456 - A master product for testing (Images: No)"
    assert str(master_product) == expected_str


def test_product_master_str_no_description():
    """Verify the __str__ method for ProductMaster handles no description."""
    master_product = ProductMasterFactory(code="MASTER-SKU-789", description=None)
    expected_str = "Master: MASTER-SKU-789 - No description (Images: No)"
    assert str(master_product) == expected_str


def test_product_master_str_with_images():
    """Verify the __str__ method for ProductMaster when it has images."""
    master_product = ProductMasterFactory(code="MASTER-SKU-IMAGE", description="Product with images")
    ProductImageFactory(product=master_product, url="http://example.com/image1.jpg")
    expected_str = "Master: MASTER-SKU-IMAGE - Product with images (Images: Yes)"
    assert str(master_product) == expected_str


def test_product_image_str():
    """Verify the __str__ method for ProductImage returns the expected format."""
    master_product = ProductMasterFactory(code="SKU-123")
    image = ProductImageFactory(product=master_product, url="http://example.com/img.jpg", order=1)
    expected_str = "Image for SKU-123 (1) - http://example.com/img.jpg"
    assert str(image) == expected_str


def test_product_master_price_precision():
    """Assert that 'price' retains 2-decimal precision."""
    price = Decimal("12345.67")
    master_product = ProductMasterFactory(price=price)
    master_product.refresh_from_db()
    assert master_product.price == price
    assert master_product.price.as_tuple().exponent == -2


def test_product_master_json_fields():
    """Verify JSON fields in ProductMaster."""
    specs = {"Weight": "1.2kg", "Color": "Silver"}
    master_product = ProductMasterFactory(specs=specs)
    master_product.refresh_from_db()
    assert master_product.specs == specs


def test_product_detail_scrape_str():
    """Verify the __str__ method for ProductDetailScrape."""
    master = ProductMasterFactory(code="SKU-DETAIL")
    scrape = ProductDetailScrapeFactory(product=master)
    expected_str = f"Detail Scrape for SKU-DETAIL at {scrape.created_at}"
    assert str(scrape) == expected_str


def test_product_detail_scrape_json_fields():
    """Verify JSON fields in ProductDetailScrape."""
    attributes = {"Brand": "Test", "Model": "X1"}
    image_urls = ["http://img1.com", "http://img2.com"]
    scrape = ProductDetailScrapeFactory(attributes=attributes, image_urls=image_urls)
    scrape.refresh_from_db()
    assert scrape.attributes == attributes
    assert scrape.image_urls == image_urls


def test_product_master_additional_fields():
    """Verify additional fields in ProductMaster."""
    master = ProductMasterFactory(
        sku="SKU-MASTER-001", is_for_mercadolibre=True, seo_title="Best Product Ever", gtin="1234567890123", gtin_source="google_search", normalized_name="Apple MacBook Pro M3 16GB 512GB", model_name="MacBook Pro M3"
    )
    master.refresh_from_db()
    assert master.sku == "SKU-MASTER-001"
    assert master.is_for_mercadolibre is True
    assert master.seo_title == "Best Product Ever"
    assert master.gtin == "1234567890123"
    assert master.gtin_source == "google_search"
    assert master.normalized_name == "Apple MacBook Pro M3 16GB 512GB"
    assert master.model_name == "MacBook Pro M3"


def test_product_master_stock_fields():
    """Verify stock fields in ProductMaster."""
    master = ProductMasterFactory(stock_principal="Si", stock_colon="No", stock_sur="5", stock_gye_norte="Si", stock_gye_sur="No")
    master.refresh_from_db()
    assert master.stock_principal == "Si"
    assert master.stock_colon == "No"
    assert master.stock_sur == "5"
    assert master.stock_gye_norte == "Si"
    assert master.stock_gye_sur == "No"


def test_product_raw_pdf_fields():
    """Verify other fields in ProductRawPDF."""
    pdf = ProductRawPDFFactory(distributor_price=Decimal("99.99"), category_header="Laptops")
    pdf.refresh_from_db()
    assert pdf.distributor_price == Decimal("99.99")
    assert pdf.category_header == "Laptops"


def test_product_raw_web_fields():
    """Verify other fields in ProductRawWeb."""
    web = ProductRawWebFactory(stock_principal="Si", scrape_session_id="session-123", search_term="test-search")
    web.refresh_from_db()
    assert web.stock_principal == "Si"
    assert web.scrape_session_id == "session-123"
    assert web.search_term == "test-search"


def test_product_image_fields():
    """Verify other fields in ProductImage."""
    image = ProductImageFactory(is_processed=True)
    image.refresh_from_db()
    assert image.is_processed is True


def test_product_detail_scrape_fields():
    """Verify other fields in ProductDetailScrape."""
    scrape = ProductDetailScrapeFactory(price=Decimal("150.50"), currency="EUR", scrape_session_id="scrape-sess-456")
    scrape.refresh_from_db()
    assert scrape.price == Decimal("150.50")
    assert scrape.currency == "EUR"
    assert scrape.scrape_session_id == "scrape-sess-456"

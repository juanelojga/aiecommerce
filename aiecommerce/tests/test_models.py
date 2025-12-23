from decimal import Decimal

import pytest

from aiecommerce.tests.factories import (
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
    expected_str = "Master: MASTER-SKU-456 - A master product for testing"
    assert str(master_product) == expected_str


def test_product_master_str_no_description():
    """Verify the __str__ method for ProductMaster handles no description."""
    master_product = ProductMasterFactory(code="MASTER-SKU-789", description=None)
    expected_str = "Master: MASTER-SKU-789 - No description"
    assert str(master_product) == expected_str


def test_product_master_price_precision():
    """Assert that 'price_distributor' retains 2-decimal precision."""
    price = Decimal("12345.67")
    master_product = ProductMasterFactory(price=price)
    master_product.refresh_from_db()
    assert master_product.price == price
    assert master_product.price.as_tuple().exponent == -2

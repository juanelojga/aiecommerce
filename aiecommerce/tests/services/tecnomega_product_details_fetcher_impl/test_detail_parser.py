import pytest
from bs4 import BeautifulSoup

from aiecommerce.services.tecnomega_product_details_fetcher_impl.detail_parser import TecnomegaDetailParser


@pytest.fixture
def parser():
    return TecnomegaDetailParser()


class TestTecnomegaDetailParser:
    def test_parse_name_success(self, parser):
        html = '<div class="md:w-2/6"><h1>Test Product Name</h1></div>'
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_name(soup) == "Test Product Name"

    def test_parse_name_not_found(self, parser):
        html = "<div><h1>Wrong Place</h1></div>"
        soup = BeautifulSoup(html, "html.parser")
        with pytest.raises(ValueError, match=r"Product name \(h1\) not found"):
            parser._parse_name(soup)

    def test_parse_price_amber_selector(self, parser):
        html = '<p class="text-amber-600">$1,234.56</p>'
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_price(soup) == 1234.56

    def test_parse_price_attribute_row(self, parser):
        html = """
        <div class="flex justify-between border-b border-slate-300">
            <strong>Precio:</strong>
            <span>$500.00</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_price(soup) == 500.00

    def test_parse_price_regex_search(self, parser):
        html = "<div><p>El PVP es de 150.50 dollars</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_price(soup) == 150.50

    def test_parse_price_nextjs_script_priceW(self, parser):
        html = '<script>{"priceW": 1200.50, "priceD": 1100.00}</script>'
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_price(soup) == 1200.50

    def test_parse_price_nextjs_script_priceD(self, parser):
        html = '<script>{"priceD": 1100.00}</script>'
        soup = BeautifulSoup(html, "html.parser")
        assert parser._parse_price(soup) == 1100.00

    def test_parse_price_not_found(self, parser):
        html = "<div>No price here</div>"
        soup = BeautifulSoup(html, "html.parser")
        with pytest.raises(ValueError, match="Product price not found"):
            parser._parse_price(soup)

    def test_parse_images_success(self, parser):
        html = """
        <div class="flex justify-center">
            <img alt="image-current" src="main.jpg">
        </div>
        <div class="bg-zinc-100">
            <img src="thumb1.jpg">
            <img src="thumb2.jpg">
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        images = parser._parse_images(soup)
        assert images == ["main.jpg", "thumb1.jpg", "thumb2.jpg"]

    def test_parse_images_no_images(self, parser, caplog):
        html = "<div>No images here</div>"
        soup = BeautifulSoup(html, "html.parser")
        images = parser._parse_images(soup)
        assert images == []
        assert "No images found on Tecnomega product page" in caplog.text

    def test_parse_attributes_success(self, parser):
        html = """
        <div class="flex justify-between border-b border-slate-300">
            <strong>Código</strong>
            <span>SKU123</span>
        </div>
        <div class="flex justify-between border-b border-slate-300">
            <strong>Marca</strong>
            <span>BrandX</span>
        </div>
        <div class="flex justify-between border-b border-slate-300">
            <strong>Unknown</strong>
            <span>Value</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        attributes = parser._parse_attributes(soup)
        assert attributes == {"sku": "SKU123", "brand": "BrandX", "unknown": "Value"}

    def test_parse_full(self, parser):
        html = """
        <div class="md:w-2/6"><h1>Test Product</h1></div>
        <p class="text-amber-600">$99.99</p>
        <div class="flex justify-center"><img alt="image-current" src="main.jpg"></div>
        <div class="flex justify-between border-b border-slate-300">
            <strong>Marca</strong>
            <span>TestBrand</span>
        </div>
        """
        result = parser.parse(html)
        assert result["name"] == "Test Product"
        assert result["price"] == 99.99
        assert result["currency"] == "USD"
        assert result["images"] == ["main.jpg"]
        assert result["attributes"] == {"brand": "TestBrand"}

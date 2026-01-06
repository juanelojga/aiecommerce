import logging

import pytest

from aiecommerce.services.scrape_tecnomega_impl.detail_parser import TecnomegaDetailParser


@pytest.fixture
def parser():
    return TecnomegaDetailParser()


def test_parse_name_success(parser):
    html = '<div class="md:w-2/6"><h1>Test Product Name</h1></div>'
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    assert parser._parse_name(soup) == "Test Product Name"


def test_parse_name_missing(parser):
    html = "<div><p>Not a name</p></div>"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    with pytest.raises(ValueError, match=r"Product name \(h1\) not found"):
        parser._parse_name(soup)


def test_parse_price_success(parser):
    html = '<p class="text-amber-600">$1,573.78</p>'
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    assert parser._parse_price(soup) == 1573.78


def test_parse_price_different_format(parser):
    html = '<p class="text-amber-600">Price: 100.50 USD</p>'
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    assert parser._parse_price(soup) == 100.5


def test_parse_price_missing(parser):
    html = "<div>No price here</div>"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    with pytest.raises(ValueError, match="Product price not found"):
        parser._parse_price(soup)


def test_parse_price_no_match(parser):
    html = '<p class="text-amber-600">No price</p>'
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    with pytest.raises(ValueError, match="Unable to parse price from 'No price'"):
        parser._parse_price(soup)


def test_parse_images_success(parser):
    html = """
    <div class="flex justify-center">
        <img alt="image-current" src="main.jpg">
    </div>
    <div class="bg-zinc-100">
        <img src="thumb1.jpg">
        <img src="thumb2.jpg">
        <img src="main.jpg">  <!-- Duplicate, should be ignored -->
    </div>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    images = parser._parse_images(soup)
    assert images == ["main.jpg", "thumb1.jpg", "thumb2.jpg"]


def test_parse_images_none(parser, caplog):
    html = "<div>No images</div>"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    with caplog.at_level(logging.WARNING):
        images = parser._parse_images(soup)
    assert images == []
    assert "No images found on Tecnomega product page" in caplog.text


def test_parse_attributes_success(parser):
    html = """
    <div class="flex justify-between border-b border-slate-300">
        <strong>Código:</strong>
        <span>12345</span>
    </div>
    <div class="flex justify-between border-b border-slate-300">
        <strong>Marca:</strong>
        <span>HP</span>
    </div>
    <div class="flex justify-between border-b border-slate-300">
        <strong>Empty:</strong>
        <!-- Missing span -->
    </div>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    attributes = parser._parse_attributes(soup)
    assert attributes == {"código:": "12345", "marca:": "HP"}


def test_parse_attributes_none(parser, caplog):
    html = "<div>No attributes</div>"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    with caplog.at_level(logging.WARNING):
        attributes = parser._parse_attributes(soup)
    assert attributes == {}
    assert "No attribute rows found on Tecnomega page" in caplog.text


def test_parse_full(parser):
    html = """
    <div class="md:w-2/6"><h1>Test Product</h1></div>
    <p class="text-amber-600">$99.99</p>
    <div class="flex justify-center">
        <img alt="image-current" src="img1.jpg">
    </div>
    <div class="flex justify-between border-b border-slate-300">
        <strong>Marca</strong>
        <span>Dell</span>
    </div>
    """
    result = parser.parse(html)
    assert result == {"name": "Test Product", "price": 99.99, "currency": "USD", "images": ["img1.jpg"], "attributes": {"brand": "Dell"}}

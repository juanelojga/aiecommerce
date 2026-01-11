import pytest

from aiecommerce.services.mercadolibre_category_impl.stock import MercadoLibreStockEngine
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.fixture
def stock_engine():
    return MercadoLibreStockEngine()


class TestMercadoLibreStockEngine:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("SI", True),
            ("si", True),
            (" SI ", True),
            ("NO", False),
            ("no", False),
            ("", False),
            (None, False),
            (123, False),
            ("S", False),
        ],
    )
    def test_is_available(self, stock_engine, value, expected):
        assert stock_engine._is_available(value) == expected

    def test_get_available_quantity_principal_not_available(self, stock_engine):
        product = ProductMasterFactory.build(
            stock_principal="NO",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert stock_engine.get_available_quantity(product) == 0

    def test_get_available_quantity_all_available(self, stock_engine):
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert stock_engine.get_available_quantity(product) == 4

    def test_get_available_quantity_some_available(self, stock_engine):
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
            stock_gye_norte="SI",
            stock_gye_sur="NO",
        )
        assert stock_engine.get_available_quantity(product) == 2

    def test_get_available_quantity_none_available(self, stock_engine):
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="NO",
            stock_sur="NO",
            stock_gye_norte="NO",
            stock_gye_sur="NO",
        )
        assert stock_engine.get_available_quantity(product) == 0

    def test_get_available_quantity_mixed_casing_and_whitespace(self, stock_engine):
        product = ProductMasterFactory.build(
            stock_principal=" si ",
            stock_colon="SI",
            stock_sur=" si",
            stock_gye_norte="NO",
            stock_gye_sur=None,
        )
        assert stock_engine.get_available_quantity(product) == 2

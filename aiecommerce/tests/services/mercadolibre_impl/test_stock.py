import pytest

from aiecommerce.services.mercadolibre_impl.stock import MercadoLibreStockEngine
from aiecommerce.tests.factories import ProductMasterFactory


class TestMercadoLibreStockEngine:
    @pytest.fixture
    def engine(self):
        return MercadoLibreStockEngine()

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("SI", True),
            ("si", True),
            (" SI ", True),
            ("NO", False),
            ("no", False),
            (None, False),
            (123, False),
            ("", False),
            ("Something Else", False),
        ],
    )
    def test_is_available(self, engine, value, expected):
        assert engine._is_available(value) == expected

    @pytest.mark.django_db
    def test_get_available_quantity_principal_not_available(self, engine):
        product = ProductMasterFactory(
            stock_principal="NO",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert engine.get_available_quantity(product) == 0

    @pytest.mark.django_db
    def test_get_available_quantity_principal_none(self, engine):
        product = ProductMasterFactory(
            stock_principal=None,
            stock_colon="SI",
        )
        assert engine.get_available_quantity(product) == 0

    @pytest.mark.django_db
    def test_get_available_quantity_all_branches_available(self, engine):
        product = ProductMasterFactory(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert engine.get_available_quantity(product) == 4

    @pytest.mark.django_db
    def test_get_available_quantity_some_branches_available(self, engine):
        product = ProductMasterFactory(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
            stock_gye_norte="SI",
            stock_gye_sur="NO",
        )
        # Only stock_colon and stock_gye_norte are SI
        assert engine.get_available_quantity(product) == 2

    @pytest.mark.django_db
    def test_get_available_quantity_no_branches_available(self, engine):
        product = ProductMasterFactory(
            stock_principal="SI",
            stock_colon="NO",
            stock_sur="NO",
            stock_gye_norte="NO",
            stock_gye_sur="NO",
        )
        assert engine.get_available_quantity(product) == 0

    @pytest.mark.django_db
    def test_get_available_quantity_with_whitespace_and_lowercase(self, engine):
        product = ProductMasterFactory(
            stock_principal=" si ",
            stock_colon=" SI",
            stock_sur="no",
            stock_gye_norte=None,
            stock_gye_sur="Si ",
        )
        # stock_principal is " si " -> available
        # stock_colon is " SI" -> available
        # stock_sur is "no" -> not available
        # stock_gye_norte is None -> not available
        # stock_gye_sur is "Si " -> available
        assert engine.get_available_quantity(product) == 2

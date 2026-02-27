import pytest

from aiecommerce.models.product import ProductMaster
from aiecommerce.tests.factories import ProductMasterFactory


class TestIsStockAvailable:
    """Tests for the ProductMaster._is_stock_available static method."""

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
    def test_is_stock_available(self, value: str | None, expected: bool) -> None:
        assert ProductMaster._is_stock_available(value) == expected


class TestTotalAvailableStock:
    """Tests for the ProductMaster.total_available_stock property."""

    def test_principal_not_available_returns_zero(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal="NO",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert product.total_available_stock == 0

    def test_all_branches_available(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        assert product.total_available_stock == 4

    def test_some_branches_available(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
            stock_gye_norte="SI",
            stock_gye_sur="NO",
        )
        assert product.total_available_stock == 2

    def test_no_branches_available(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal="SI",
            stock_colon="NO",
            stock_sur="NO",
            stock_gye_norte="NO",
            stock_gye_sur="NO",
        )
        assert product.total_available_stock == 0

    def test_mixed_casing_and_whitespace(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal=" si ",
            stock_colon="SI",
            stock_sur=" si",
            stock_gye_norte="NO",
            stock_gye_sur=None,
        )
        assert product.total_available_stock == 2

    def test_principal_none_returns_zero(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal=None,
            stock_colon="SI",
            stock_sur="SI",
        )
        assert product.total_available_stock == 0

    def test_principal_empty_string_returns_zero(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal="",
            stock_colon="SI",
        )
        assert product.total_available_stock == 0

    def test_all_none_returns_zero(self) -> None:
        product = ProductMasterFactory.build(
            stock_principal=None,
            stock_colon=None,
            stock_sur=None,
            stock_gye_norte=None,
            stock_gye_sur=None,
        )
        assert product.total_available_stock == 0

    def test_consistency_with_stock_engine(self) -> None:
        """Ensure the property produces the same result as MercadoLibreStockEngine."""
        from aiecommerce.services.mercadolibre_category_impl.stock import MercadoLibreStockEngine

        engine = MercadoLibreStockEngine()

        test_cases = [
            {"stock_principal": "SI", "stock_colon": "SI", "stock_sur": "SI", "stock_gye_norte": "SI", "stock_gye_sur": "SI"},
            {"stock_principal": "NO", "stock_colon": "SI", "stock_sur": "SI", "stock_gye_norte": "SI", "stock_gye_sur": "SI"},
            {"stock_principal": "SI", "stock_colon": "NO", "stock_sur": "NO", "stock_gye_norte": "NO", "stock_gye_sur": "NO"},
            {"stock_principal": " si ", "stock_colon": "SI", "stock_sur": " si", "stock_gye_norte": "NO", "stock_gye_sur": None},
            {"stock_principal": None, "stock_colon": "SI", "stock_sur": "SI", "stock_gye_norte": None, "stock_gye_sur": None},
        ]

        for kwargs in test_cases:
            product = ProductMasterFactory.build(**kwargs)
            assert product.total_available_stock == engine.get_available_quantity(product), (
                f"Mismatch for {kwargs}: property={product.total_available_stock}, engine={engine.get_available_quantity(product)}"
            )

import pytest

from aiecommerce.services.mercadolibre_publisher_impl.selector import ProductSelector
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestProductSelector:
    def test_get_product_by_code_success(self):
        # Arrange
        code = "TEST-CODE"
        product = ProductMasterFactory(code=code, is_for_mercadolibre=True)
        # Create another product that shouldn't be matched
        ProductMasterFactory(code=code, is_for_mercadolibre=False)
        ProductMasterFactory(code="OTHER-CODE", is_for_mercadolibre=True)

        # Act
        result = ProductSelector.get_product_by_code(code)

        # Assert
        assert result is not None
        assert result.id == product.id
        assert result.code == code
        assert result.is_for_mercadolibre is True

    def test_get_product_by_code_not_found(self):
        # Arrange
        code = "NON-EXISTENT"

        # Act
        result = ProductSelector.get_product_by_code(code)

        # Assert
        assert result is None

    def test_get_product_by_code_exists_but_not_for_mercadolibre(self):
        # Arrange
        code = "NOT-FOR-ML"
        ProductMasterFactory(code=code, is_for_mercadolibre=False)

        # Act
        result = ProductSelector.get_product_by_code(code)

        # Assert
        assert result is None

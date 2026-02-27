import logging
from typing import ClassVar

from aiecommerce.models.product import ProductMaster

logger = logging.getLogger(__name__)


class MercadoLibreStockEngine:
    """
    Calculates the available stock for a product based on branch availability.

    Delegates to ProductMaster.total_available_stock which contains the
    canonical stock normalization logic.
    """

    # Kept for backward compatibility (used by selectors for queryset filtering).
    BRANCH_FIELDS: ClassVar[list[str]] = ProductMaster.BRANCH_FIELDS

    def _is_available(self, value: str | None) -> bool:
        """
        Normalizes a stock value and checks if it indicates availability ('SI').
        """
        return ProductMaster._is_stock_available(value)

    def get_available_quantity(self, product: ProductMaster) -> int:
        """
        Calculates the available quantity of a product across different branches.

        Delegates to ProductMaster.total_available_stock property.

        Args:
            product: The ProductMaster instance to check.

        Returns:
            The calculated available stock quantity.
        """
        quantity = product.total_available_stock
        if quantity == 0 and not ProductMaster._is_stock_available(product.stock_principal):
            logger.info(
                "Product %s has non-SI principal stock ('%s'). Setting quantity to 0.",
                product.code,
                product.stock_principal,
            )
        return quantity

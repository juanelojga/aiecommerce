import logging
from typing import ClassVar

from aiecommerce.models.product import ProductMaster

logger = logging.getLogger(__name__)


class MercadoLibreStockEngine:
    """
    Calculates the available stock for a product based on branch availability.
    """

    BRANCH_FIELDS: ClassVar[list[str]] = [
        "stock_colon",
        "stock_sur",
        "stock_gye_norte",
        "stock_gye_sur",
    ]

    def _is_available(self, value: str | None) -> bool:
        """
        Normalizes a stock value and checks if it indicates availability ('SI').
        """
        if not value or not isinstance(value, str):
            return False
        return value.strip().upper() == "SI"

    def get_available_quantity(self, product: ProductMaster) -> int:
        """
        Calculates the available quantity of a product across different branches.

        The logic is as follows:
        1. If the main stock ('stock_principal') is not 'SI', the available quantity is 0.
        2. If the main stock is 'SI', the available quantity is the count of branches
           where the stock is also marked as 'SI'.

        Args:
            product: The ProductMaster instance to check.

        Returns:
            The calculated available stock quantity.
        """
        if not self._is_available(product.stock_principal):
            logger.info(
                "Product %s has non-SI principal stock ('%s'). Setting quantity to 0.",
                product.code,
                product.stock_principal,
            )
            return 0

        available_count = 0
        for field in self.BRANCH_FIELDS:
            branch_stock_value = getattr(product, field, None)
            if self._is_available(branch_stock_value):
                available_count += 1

        return available_count

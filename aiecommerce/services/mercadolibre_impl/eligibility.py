import logging
from typing import Dict

from django.db import transaction

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter

logger = logging.getLogger(__name__)


class MercadoLibreEligibilityService:
    """
    Manages the eligibility status of products for Mercado Libre.
    """

    def __init__(self, ml_filter: MercadoLibreFilter) -> None:
        self.ml_filter = ml_filter

    @transaction.atomic
    def update_eligibility_flags(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Updates the 'is_for_mercadolibre' flag on all ProductMaster instances.

        This method identifies products that are eligible for Mercado Libre,
        marks them as such, and unmarks any that are no longer eligible.

        Args:
            dry_run: If True, calculates changes without saving to the database.

        Returns:
            A dictionary with counts of enabled and disabled products.
        """
        sid = transaction.savepoint()
        logger.info("Starting to update Mercado Libre eligibility flags.")

        # 1. Get IDs of all eligible products
        eligible_products_qs = self.ml_filter.get_eligible_products()
        eligible_product_ids = set(eligible_products_qs.values_list("id", flat=True))
        logger.debug(f"Found {len(eligible_product_ids)} eligible products.")

        # 2. Get IDs of products currently marked for Mercado Libre
        currently_marked_ids = set(ProductMaster.objects.filter(is_for_mercadolibre=True).values_list("id", flat=True))
        logger.debug(f"Found {len(currently_marked_ids)} products currently marked for Mercado Libre.")

        # 3. Determine which products to enable and disable
        ids_to_enable = eligible_product_ids - currently_marked_ids
        ids_to_disable = currently_marked_ids - eligible_product_ids

        # 4. Update the database
        enabled_count = 0
        if ids_to_enable:
            enabled_count = ProductMaster.objects.filter(id__in=ids_to_enable).update(is_for_mercadolibre=True)

        disabled_count = 0
        if ids_to_disable:
            disabled_count = ProductMaster.objects.filter(id__in=ids_to_disable).update(is_for_mercadolibre=False)

        result = {"enabled": enabled_count, "disabled": disabled_count}

        if dry_run:
            transaction.savepoint_rollback(sid)
            logger.info("Dry run for eligibility update. Rolling back changes.")
            # In a dry run, the update calls still return the count of rows that *would* be affected.
            # We don't need to change the logic, just ensure the transaction is rolled back.
            # However, to be more explicit about what would happen, we can calculate the counts
            # without performing the update.
            result = {
                "enabled": len(ids_to_enable),
                "disabled": len(ids_to_disable),
            }
        else:
            transaction.savepoint_commit(sid)
            logger.info(
                "Mercado Libre eligibility update complete. Enabled: %d, Disabled: %d.",
                enabled_count,
                disabled_count,
            )
        return result

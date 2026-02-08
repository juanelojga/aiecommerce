"""
This service implements the business logic for Task ML-06.

It provides a price calculation engine for Mercado Libre listings, ensuring
that margins are protected by accounting for various operational costs,
fees, and taxes.
"""

import json
import logging
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


class MercadoLibrePriceEngine:
    """
    Calculates the final selling price for a product on Mercado Libre.

    This engine applies a series of calculations to a base cost to determine
    the final price, considering operational costs, target margins, commissions,
    and taxes, as defined in the project settings.

    Supports tiered commission rates based on product cost ranges, configured
    via the MERCADOLIBRE_COMMISSION_TIERS setting.
    """

    def _get_commission_rate(self, base_cost: Decimal) -> Decimal:
        """
        Determines the appropriate commission rate for the given base cost.

        If MERCADOLIBRE_COMMISSION_TIERS is configured, selects the rate based
        on which tier the base_cost falls into. Otherwise, falls back to the
        legacy MERCADOLIBRE_COMMISSION_RATE setting.

        Tiers are defined as a JSON array of objects with "max" and "rate" fields:
        [
            {"max": 100, "rate": 0.18},
            {"max": 500, "rate": 0.15},
            {"max": null, "rate": 0.10}
        ]

        Args:
            base_cost: The product's base cost to evaluate against tiers.

        Returns:
            The commission rate (as a Decimal) for the given base cost.
        """
        tiers_config = settings.MERCADOLIBRE_COMMISSION_TIERS

        # Fallback to legacy single rate if tiers not configured
        if not tiers_config:
            return Decimal(settings.MERCADOLIBRE_COMMISSION_RATE)

        try:
            tiers = json.loads(tiers_config)

            # Validate that tiers is a list
            if not isinstance(tiers, list) or len(tiers) == 0:
                logger.warning("MERCADOLIBRE_COMMISSION_TIERS is not a valid list. Falling back to MERCADOLIBRE_COMMISSION_RATE.")
                return Decimal(settings.MERCADOLIBRE_COMMISSION_RATE)

            # Find the appropriate tier
            highest_rate = None
            for tier in tiers:
                # Validate tier structure
                if not isinstance(tier, dict) or "rate" not in tier:
                    logger.warning(f"Invalid tier structure: {tier}. Falling back to MERCADOLIBRE_COMMISSION_RATE.")
                    return Decimal(settings.MERCADOLIBRE_COMMISSION_RATE)

                rate = Decimal(str(tier["rate"]))

                # Track the highest rate for fallback on error
                if highest_rate is None or rate > highest_rate:
                    highest_rate = rate

                # Check if this tier matches
                max_value = tier.get("max")
                if max_value is None:
                    # This is the final tier (no upper limit)
                    return rate
                elif base_cost <= Decimal(str(max_value)):
                    return rate

            # If we reach here, use the last tier's rate (shouldn't happen with valid config)
            return highest_rate if highest_rate is not None else Decimal(settings.MERCADOLIBRE_COMMISSION_RATE)

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error parsing MERCADOLIBRE_COMMISSION_TIERS: {e}. Falling back to MERCADOLIBRE_COMMISSION_RATE.")
            return Decimal(settings.MERCADOLIBRE_COMMISSION_RATE)

    def calculate(self, base_cost: Decimal) -> dict[str, Decimal]:
        """
        Calculates the final Mercado Libre price based on a product's base cost.

        The formula is designed to protect margins by accounting for various
        Mercado Libre fees and local taxes.

        Formula:
            1. Internal Cost = base_cost + ML_OPERATIONAL_COST
            2. Desired Net = Internal Cost * (1 + ML_TARGET_MARGIN)
            3. Net Price = (Desired Net + ML_SHIPPING_FEE) / (1 - ML_COMMISSION_RATE)
            4. Final Price = Net Price * (1 + ML_IVA_RATE)

        Args:
            base_cost: The fundamental cost of acquiring the product.

        Returns:
            A dictionary containing the calculated financial figures, rounded to
            two decimal places:
                - final_price: The final price to be published on Mercado Libre.
                - net_price: The price before applying the IVA tax.
                - profit: The estimated profit margin for the sale.
        """
        # Ensure all inputs are Decimals for precision
        base_cost = Decimal(base_cost)
        ml_operational_cost = Decimal(settings.MERCADOLIBRE_OPERATIONAL_COST)
        ml_target_margin = Decimal(settings.MERCADOLIBRE_TARGET_MARGIN)
        ml_shipping_fee = Decimal(settings.MERCADOLIBRE_SHIPPING_FEE)
        ml_commission_rate = self._get_commission_rate(base_cost)
        ml_iva_rate = Decimal(settings.MERCADOLIBRE_IVA_RATE)

        # 1. Calculate Internal Cost
        internal_cost = base_cost + ml_operational_cost

        # 2. Determine Desired Net (revenue after cost of goods)
        desired_net = internal_cost * (Decimal("1") + ml_target_margin)

        # 3. Calculate Net Price (before tax, but accounting for commission and shipping)
        net_price = (desired_net + ml_shipping_fee) / (Decimal("1") - ml_commission_rate)

        # 4. Calculate Final Price (including IVA tax)
        final_price = net_price * (Decimal("1") + ml_iva_rate)

        # The profit is the margin earned on top of the internal cost.
        profit = desired_net - internal_cost

        # Standardize to 2 decimal places for currency representation
        quantizer = Decimal("0.01")
        return {
            "final_price": final_price.quantize(quantizer, rounding=ROUND_HALF_UP),
            "net_price": net_price.quantize(quantizer, rounding=ROUND_HALF_UP),
            "profit": profit.quantize(quantizer, rounding=ROUND_HALF_UP),
        }

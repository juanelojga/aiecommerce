from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from aiecommerce.services.mercadolibre_category_impl.price import MercadoLibrePriceEngine


class TestMercadoLibrePriceEngine(SimpleTestCase):
    def setUp(self):
        self.price_engine = MercadoLibrePriceEngine()

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
    )
    def test_calculate_success(self):
        """
        Test calculation with standard inputs.

        Inputs:
            base_cost = 100.00
            ML_OPERATIONAL_COST = 10.00
            ML_TARGET_MARGIN = 0.20
            ML_SHIPPING_FEE = 5.00
            ML_COMMISSION_RATE = 0.15
            ML_IVA_RATE = 0.12

        Steps:
            1. Internal Cost = 100 + 10 = 110.00
            2. Desired Net = 110 * (1 + 0.20) = 110 * 1.2 = 132.00
            3. Net Price = (132 + 5) / (1 - 0.15) = 137 / 0.85 = 161.17647...
            4. Final Price = 161.17647... * (1 + 0.12) = 161.17647... * 1.12 = 180.5176...
            5. Profit = 132 - 110 = 22.00

        Expected (rounded):
            final_price: 180.52
            net_price: 161.18
            profit: 22.00
        """
        base_cost = Decimal("100.00")
        result = self.price_engine.calculate(base_cost)

        assert result["final_price"] == Decimal("180.52")
        assert result["net_price"] == Decimal("161.18")
        assert result["profit"] == Decimal("22.00")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
    )
    def test_calculate_zero_cost(self):
        """
        Test calculation with zero base cost.

        Inputs:
            base_cost = 0.00
            ML_OPERATIONAL_COST = 10.00
            ML_TARGET_MARGIN = 0.20
            ML_SHIPPING_FEE = 5.00
            ML_COMMISSION_RATE = 0.15
            ML_IVA_RATE = 0.12

        Steps:
            1. Internal Cost = 0 + 10 = 10.00
            2. Desired Net = 10 * 1.2 = 12.00
            3. Net Price = (12 + 5) / 0.85 = 17 / 0.85 = 20.00
            4. Final Price = 20 * 1.12 = 22.40
            5. Profit = 12 - 10 = 2.00

        Expected:
            final_price: 22.40
            net_price: 20.00
            profit: 2.00
        """
        base_cost = Decimal("0.00")
        result = self.price_engine.calculate(base_cost)

        assert result["final_price"] == Decimal("22.40")
        assert result["net_price"] == Decimal("20.00")
        assert result["profit"] == Decimal("2.00")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
    )
    def test_calculate_rounding(self):
        """
        Test rounding behavior (ROUND_HALF_UP).

        If we force a result that ends in .005, it should round up to .01
        """
        # Let's just use a case where division doesn't result in a clean number
        # base_cost = 50.00
        # Internal Cost = 60.00
        # Desired Net = 60 * 1.2 = 72.00
        # Net Price = (72 + 5) / 0.85 = 77 / 0.85 = 90.588235... -> 90.59
        # Final Price = 90.588235... * 1.12 = 101.4588... -> 101.46
        # Profit = 72 - 60 = 12.00

        base_cost = Decimal("50.00")
        result = self.price_engine.calculate(base_cost)

        assert result["final_price"] == Decimal("101.46")
        assert result["net_price"] == Decimal("90.59")
        assert result["profit"] == Decimal("12.00")

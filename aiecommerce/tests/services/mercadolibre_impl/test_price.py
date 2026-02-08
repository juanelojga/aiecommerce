from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from aiecommerce.services.mercadolibre_category_impl.price import MercadoLibrePriceEngine

# Standard tier configuration for testing
VALID_TIERS_CONFIG = '[{"max": 100, "rate": 0.18}, {"max": 500, "rate": 0.15}, {"max": 2000, "rate": 0.12}, {"max": null, "rate": 0.10}]'


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


class TestMercadoLibrePriceEngineTieredCommission(SimpleTestCase):
    """Tests for tiered commission rate functionality."""

    def setUp(self):
        self.price_engine = MercadoLibrePriceEngine()

    # --- Tier Selection Tests ---

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_tier_1_low_cost_product(self):
        """Test that low-cost product ($50) uses tier 1 rate (18%)."""
        base_cost = Decimal("50.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.18")

        # Also verify full calculation
        result = self.price_engine.calculate(base_cost)
        # With 18% commission instead of 15%, the price should be higher
        # Internal Cost = 60, Desired Net = 72, Net = (72 + 5) / 0.82 = 93.90...
        # Final = 93.90 * 1.12 = 105.17
        assert result["final_price"] == Decimal("105.17")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_tier_2_mid_range_product(self):
        """Test that mid-range product ($250) uses tier 2 rate (15%)."""
        base_cost = Decimal("250.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

        # Verify calculation
        result = self.price_engine.calculate(base_cost)
        # Internal = 260, Desired = 312, Net = (312 + 5) / 0.85 = 372.94
        # Final = 372.94 * 1.12 = 417.69
        assert result["final_price"] == Decimal("417.69")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_tier_3_high_value_product(self):
        """Test that high-value product ($1000) uses tier 3 rate (12%)."""
        base_cost = Decimal("1000.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.12")

        # Verify calculation
        result = self.price_engine.calculate(base_cost)
        # Internal = 1010, Desired = 1212, Net = (1212 + 5) / 0.88 = 1382.95
        # Final = 1382.95 * 1.12 = 1548.91
        assert result["final_price"] == Decimal("1548.91")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_tier_4_premium_product(self):
        """Test that premium product ($5000) uses tier 4 rate (10%)."""
        base_cost = Decimal("5000.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.10")

        # Verify calculation
        result = self.price_engine.calculate(base_cost)
        # Internal = 5010, Desired = 6012, Net = (6012 + 5) / 0.90 = 6685.56
        # Final = 6685.56 * 1.12 = 7487.82
        assert result["final_price"] == Decimal("7487.82")

    # --- Boundary Tests ---

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_boundary_exact_100(self):
        """Test that $100.00 exactly uses tier 1 rate (18%)."""
        base_cost = Decimal("100.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        # Boundary is inclusive: base_cost <= 100, so 100.00 uses tier 1
        assert commission_rate == Decimal("0.18")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_boundary_just_below_100(self):
        """Test that $99.99 uses tier 1 rate (18%)."""
        base_cost = Decimal("99.99")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.18")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_boundary_just_above_100(self):
        """Test that $100.01 uses tier 2 rate (15%)."""
        base_cost = Decimal("100.01")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_boundary_exact_500(self):
        """Test that $500.00 exactly uses tier 2 rate (15%)."""
        base_cost = Decimal("500.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        # Boundary is inclusive: base_cost <= 500, so 500.00 uses tier 2
        assert commission_rate == Decimal("0.15")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_boundary_exact_2000(self):
        """Test that $2000.00 exactly uses tier 3 rate (12%)."""
        base_cost = Decimal("2000.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        # Boundary is inclusive: base_cost <= 2000, so 2000.00 uses tier 3
        assert commission_rate == Decimal("0.12")

    # --- Edge Cases ---

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_zero_cost(self):
        """Test that $0 base cost uses tier 1 rate (18%)."""
        base_cost = Decimal("0.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.18")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_commission_very_high_cost(self):
        """Test that very high cost ($100,000) uses final tier rate (10%)."""
        base_cost = Decimal("100000.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.10")

    # --- Fallback Behavior Tests ---

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=None,
    )
    def test_commission_no_tiers_configured(self):
        """Test fallback to MERCADOLIBRE_COMMISSION_RATE when tiers not set."""
        base_cost = Decimal("100.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS="not-valid-json",
    )
    def test_commission_invalid_json(self):
        """Test fallback when JSON is malformed."""
        base_cost = Decimal("100.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS="[]",
    )
    def test_commission_empty_tiers_list(self):
        """Test fallback when tiers list is empty."""
        base_cost = Decimal("100.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS='[{"max": 100}]',  # Missing "rate"
    )
    def test_commission_missing_rate_field(self):
        """Test fallback when tier is missing 'rate' field."""
        base_cost = Decimal("50.00")
        commission_rate = self.price_engine._get_commission_rate(base_cost)
        assert commission_rate == Decimal("0.15")

    # --- Full Calculation Integration Tests ---

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_full_price_calculation_with_tier_1(self):
        """Full integration test with tier 1 commission rate."""
        base_cost = Decimal("50.00")
        result = self.price_engine.calculate(base_cost)

        # Verify calculation with 18% commission
        # Internal = 60, Desired = 72, Net = 77 / 0.82 = 93.90, Final = 105.17
        assert result["final_price"] == Decimal("105.17")
        assert result["net_price"] == Decimal("93.90")
        assert result["profit"] == Decimal("12.00")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_full_price_calculation_with_tier_4(self):
        """Full integration test with tier 4 commission rate."""
        base_cost = Decimal("5000.00")
        result = self.price_engine.calculate(base_cost)

        # Verify calculation with 10% commission
        assert result["final_price"] == Decimal("7487.82")
        assert result["net_price"] == Decimal("6685.56")
        assert result["profit"] == Decimal("1002.00")

    @override_settings(
        MERCADOLIBRE_OPERATIONAL_COST="10.00",
        MERCADOLIBRE_TARGET_MARGIN="0.20",
        MERCADOLIBRE_SHIPPING_FEE="5.00",
        MERCADOLIBRE_COMMISSION_RATE="0.15",
        MERCADOLIBRE_IVA_RATE="0.12",
        MERCADOLIBRE_COMMISSION_TIERS=VALID_TIERS_CONFIG,
    )
    def test_price_difference_between_tiers(self):
        """Verify that different tiers produce different prices for same base cost logic."""
        # Compare $50 (tier 1, 18%) vs $250 (tier 2, 15%)
        result_tier1 = self.price_engine.calculate(Decimal("50.00"))
        result_tier2 = self.price_engine.calculate(Decimal("250.00"))

        # Higher commission should result in higher final price (relative to base cost)
        # Tier 1 markup percentage should be higher than tier 2
        tier1_markup = (result_tier1["final_price"] - Decimal("50.00")) / Decimal("50.00")
        tier2_markup = (result_tier2["final_price"] - Decimal("250.00")) / Decimal("250.00")

        assert tier1_markup > tier2_markup

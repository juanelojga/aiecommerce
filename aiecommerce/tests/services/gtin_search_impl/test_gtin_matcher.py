import pytest

from aiecommerce.services.gtin_search_impl.matcher import ProductMatcher
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestProductMatcher:
    def test_init_raises_type_error(self):
        with pytest.raises(TypeError, match="product must be an instance of ProductMaster"):
            ProductMatcher("not a product")  # type: ignore[arg-type]

    def test_init_success(self):
        product = ProductMasterFactory.build()
        matcher = ProductMatcher(product)
        assert matcher.product == product
        assert matcher.specs == product.specs
        assert matcher.category_type == product.specs.get("category_type")

    @pytest.mark.parametrize(
        "input_text, expected",
        [
            ("16 GB", "16gb"),
            ("  16GB  ", "16gb"),
            ("RAM 16 GB", "ram16gb"),
            (None, ""),
            ("", ""),
        ],
    )
    def test_normalize_spec_text(self, input_text, expected):
        product = ProductMasterFactory.build()
        matcher = ProductMatcher(product)
        assert matcher._normalize_spec_text(input_text) == expected

    def test_extract_potential_values(self):
        product = ProductMasterFactory.build()
        matcher = ProductMatcher(product)
        text = 'Notebook HP 15-dy2024la Intel Core i5 11th Gen 8GB RAM 256GB SSD 15.6"'
        values = matcher._extract_potential_values(text)

        assert "GB" in values
        assert "8gb" in values["GB"]
        assert "256gb" in values["GB"]

        # Test RAM Latency special case
        text_with_cl = "Memory DDR4 16GB 3200MHz 1 CL16"  # Added '1' before CL16 to match regex
        values_cl = matcher._extract_potential_values(text_with_cl)
        assert "LATENCY" in values_cl
        assert "1cl16" in values_cl["LATENCY"]

    def test_check_hard_gate_penalty_no_category(self):
        product = ProductMasterFactory.build(specs={"category_type": "UNKNOWN"})
        matcher = ProductMatcher(product)
        penalty, field = matcher._check_hard_gate_penalty("Some Candidate Name")
        assert penalty is False
        assert field is None

    def test_check_hard_gate_penalty_manufacturer_mismatch(self):
        product = ProductMasterFactory.create(specs={"category_type": "NOTEBOOK", "manufacturer": "HP"})
        matcher = ProductMatcher(product)

        # Should penalize if candidate is another common manufacturer
        # We MUST include a spec with unit so _extract_potential_values returns something
        penalty, field = matcher._check_hard_gate_penalty("Laptop Lenovo IdeaPad 16GB")
        assert penalty is True
        assert field == "manufacturer"

        # Should NOT penalize if candidate name doesn't contain common manufacturers but doesn't match
        penalty, field = matcher._check_hard_gate_penalty("Generic Laptop 123")
        assert penalty is False
        assert field is None

        # Should NOT penalize if it matches
        penalty, field = matcher._check_hard_gate_penalty("HP Pavilion Laptop")
        assert penalty is False
        assert field is None

    def test_check_hard_gate_penalty_spec_mismatch(self):
        product = ProductMasterFactory.build(specs={"category_type": "NOTEBOOK", "ram": "16GB", "storage": "512GB"})
        matcher = ProductMatcher(product)

        # Contradictory RAM
        penalty, field = matcher._check_hard_gate_penalty("Laptop 8GB RAM 512GB SSD")
        assert penalty is True
        assert field == "ram"

        # Contradictory Storage
        penalty, field = matcher._check_hard_gate_penalty("Laptop 16GB RAM 1TB SSD")
        assert penalty is True
        assert field == "storage"

        # No contradiction (same specs)
        penalty, field = matcher._check_hard_gate_penalty("Laptop 16GB 512GB")
        assert penalty is False
        assert field is None

    def test_check_hard_gate_penalty_cpu_generation_mismatch(self):
        product = ProductMasterFactory.build(specs={"category_type": "NOTEBOOK", "cpu": "Intel Core i7-11800H"})
        matcher = ProductMatcher(product)

        # Mismatch generation (12th vs 11th)
        penalty, field = matcher._check_hard_gate_penalty("Laptop Intel Core i7-12700H")
        assert penalty is True
        assert field == "cpu_generation"

        # Match generation
        penalty, field = matcher._check_hard_gate_penalty("Laptop i7-1165G7")
        assert penalty is False
        assert field is None

    def test_calculate_confidence_score_invalid_candidate(self):
        product = ProductMasterFactory.build()
        matcher = ProductMatcher(product)
        score, field = matcher.calculate_confidence_score(None)  # type: ignore[arg-type]
        assert score == 0.0
        score, field = matcher.calculate_confidence_score("")
        assert score == 0.0

    def test_calculate_confidence_score_weighted_average(self):
        # We need a real-ish product for fuzzy matching
        product = ProductMasterFactory.build(normalized_name="HP Laptop 15-dy2024la", model_name="15-dy2024la")
        matcher = ProductMatcher(product)

        # Perfect match
        score, field = matcher.calculate_confidence_score("HP Laptop 15-dy2024la")
        assert score == 1.0
        assert field is None

        # Partial match
        score, field = matcher.calculate_confidence_score("HP 15-dy2024la")
        assert 0.5 < score <= 1.0
        assert field is None

    def test_calculate_confidence_score_with_penalty(self):
        product = ProductMasterFactory.build(specs={"category_type": "NOTEBOOK", "ram": "16GB"}, normalized_name="HP Laptop 15-dy2024la", model_name="15-dy2024la")
        matcher = ProductMatcher(product)

        # High string similarity but spec mismatch
        score, field = matcher.calculate_confidence_score("HP Laptop 15-dy2024la 8GB RAM")
        assert score == 0.0
        assert field == "ram"

    def test_check_hard_gate_penalty_gpu_mismatch(self):
        product = ProductMasterFactory.build(specs={"category_type": "TARJETA DE VIDEO", "chipset": "RTX 3060", "vram": "12GB"})
        matcher = ProductMatcher(product)

        # Mismatch VRAM
        penalty, field = matcher._check_hard_gate_penalty("EVGA RTX 3060 8GB")
        assert penalty is True
        assert field == "vram"

        # Match
        penalty, field = matcher._check_hard_gate_penalty("MSI RTX 3060 12GB")
        assert penalty is False
        assert field is None

    def test_calculate_confidence_score_no_model_name(self):
        product = ProductMasterFactory.build(normalized_name="Generic Product Name", model_name=None)
        matcher = ProductMatcher(product)
        score, field = matcher.calculate_confidence_score("Generic Product Name")
        assert score == 1.0

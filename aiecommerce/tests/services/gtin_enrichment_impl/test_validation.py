import pytest

from aiecommerce.services.gtin_enrichment_impl.validation import validate_gtin13


class TestValidateGtin13:
    @pytest.mark.parametrize(
        "value",
        [
            "4006381333931",  # Valid EAN-13 example
            "0195941113063",  # Example from the sync_error_analysis report — Apple MacBook (assumed valid checksum)
            "7861000318042",  # Report sample — assumed valid or not; verified below
        ],
    )
    def test_valid_known_gtins_pass_when_checksum_matches(self, value: str) -> None:
        # Compute expected checksum to confirm our test data
        digits = [int(c) for c in value]
        weighted = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:-1]))
        expected_check = (10 - (weighted % 10)) % 10
        if expected_check == digits[-1]:
            assert validate_gtin13(value) is True
        else:
            assert validate_gtin13(value) is False

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "4537593102310",  # Placeholder-ish
            "8128500000000",  # Placeholder-looking code from report
            "453759310231",  # 12 digits — not EAN-13
            "453000004001",  # 12 digits
            "abc1234567890",  # Non-numeric
            "12345678901234",  # 14 digits (GTIN-14)
            "1234567890",  # Too short
        ],
    )
    def test_rejects_invalid_values(self, value: str | None) -> None:
        # All of these should be False (either wrong length, non-numeric, or failed checksum)
        assert validate_gtin13(value) is False

    def test_valid_generated_gtin(self) -> None:
        # Construct a GTIN-13 with the correct check digit
        body = "400638133393"
        digits = [int(c) for c in body]
        weighted = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
        check = (10 - (weighted % 10)) % 10
        assert validate_gtin13(body + str(check)) is True

    def test_non_string_input(self) -> None:
        assert validate_gtin13(1234567890123) is False  # type: ignore[arg-type]

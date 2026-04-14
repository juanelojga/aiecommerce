"""GTIN format + checksum validation."""

from __future__ import annotations


def validate_gtin13(value: str | None) -> bool:
    """Return True iff `value` is a valid EAN-13 GTIN (13 digits, mod-10 checksum)."""
    if not value or not isinstance(value, str):
        return False
    if len(value) != 13 or not value.isdigit():
        return False
    digits = [int(c) for c in value]
    check = digits[-1]
    weighted = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:-1]))
    return (10 - (weighted % 10)) % 10 == check

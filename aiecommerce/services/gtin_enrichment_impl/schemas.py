"""Pydantic schemas for GTIN enrichment service."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class GTINSearchResult(BaseModel):
    """Schema for GTIN search response from LLM.

    Note: Includes field_validator for 'source' field to handle responses from
    small language models (e.g., Llama 3.2 1B) that may return nested dict
    structures like {"type": "string", "value": "..."} instead of plain strings.
    """

    gtin: str | None = Field(
        None,
        description="The GTIN/EAN/UPC code found (8-14 digits). Returns None if not found.",
    )
    confidence: str = Field(
        "low",
        description="Confidence level: high, medium, or low",
    )
    source: str | None = Field(
        None,
        description="The source URL or reference where the GTIN was found",
    )

    @field_validator("source", mode="before")
    @classmethod
    def extract_source_value(cls, v: Any) -> str | None:
        """Extract source value from nested dict if present.

        Small language models like Llama 3.2 1B sometimes return schema-like
        structures: {"type": "string", "value": "https://..."} instead of
        plain strings. This validator extracts the actual value.

        Args:
            v: The source field value (could be str, dict, or None)

        Returns:
            The extracted string value, or the original value if not a nested dict
        """
        if isinstance(v, dict) and "value" in v:
            return v["value"]
        return v

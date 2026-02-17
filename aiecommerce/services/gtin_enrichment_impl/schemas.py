"""Pydantic schemas for GTIN enrichment service."""

from pydantic import BaseModel, Field


class GTINSearchResult(BaseModel):
    """Schema for GTIN search response from LLM."""

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

"""
This module provides a robust ProductMatcher service to calculate a confidence
score between a ProductMaster instance and a candidate product name from an API.

Key Features:
- Category-specific critical field validation (e.g., RAM, CPU for notebooks).
- Hard-gate penalty: Returns a score of 0 if a candidate's specs contradict
  the master product's critical specs.
- Unit normalization to handle variations like '16GB' vs. '16 GB'.
- Weighted fuzzy string matching using `rapidfuzz` against normalized names
  and model names.
"""

import re
from typing import Dict, List, Optional, Tuple, Type

from rapidfuzz.fuzz import token_set_ratio

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.specifications_impl.schemas import (
    DesktopSpecs,
    GpuSpecs,
    MotherboardSpecs,
    NotebookSpecs,
    PowerSupplySpecs,
    ProcessorSpecs,
    ProductSpecUnion,
    RamSpecs,
    StorageSpecs,
)

# --- Configuration: Critical Fields & Schema Mapping ---

# Defines which fields are critical for a given category. A mismatch in these
# fields will result in a score of 0.
_SPEC_MAPPING: Dict[str, Tuple[Type[ProductSpecUnion], List[str]]] = {
    "NOTEBOOK": (NotebookSpecs, ["cpu", "ram", "storage"]),
    "COMPUTADORES DESKTOP, AIO, MINIPC": (DesktopSpecs, ["cpu", "ram", "storage"]),
    "PROCESADORES": (ProcessorSpecs, ["socket", "generation"]),
    "MOTHER BOARDS": (MotherboardSpecs, ["socket", "chipset"]),
    "MEMORIA RAM": (RamSpecs, ["capacity", "type", "speed"]),
    "TARJETA DE VIDEO": (GpuSpecs, ["chipset", "vram"]),
    "FUENTES DE PODER": (PowerSupplySpecs, ["wattage", "certification"]),
    "UNIDADES DE ESTADO SOLIDO Y DISCOS DUROS": (StorageSpecs, ["capacity", "type", "interface"]),
}

# Regex to find numbers followed by common units (e.g., 16GB, 650W, 3.2GHz)
# It handles optional spaces and is case-insensitive.
_UNIT_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(GB|TB|MB|W|GHZ|MHZ|CL\d{1,2})", re.IGNORECASE)


class ProductMatcher:
    """
    Calculates a confidence score between a product and a candidate name.
    """

    def __init__(self, product: ProductMaster):
        if not isinstance(product, ProductMaster):
            raise TypeError("product must be an instance of ProductMaster")
        self.product = product
        self.specs = product.specs or {}
        self.category_type = self.specs.get("category_type")

    def _normalize_spec_text(self, text: Optional[str]) -> str:
        """Removes all whitespace and converts to lowercase for spec comparison."""
        if not text:
            return ""
        return re.sub(r"\s+", "", text).lower()

    def _extract_potential_values(self, text: str) -> Dict[str, List[str]]:
        """
        Finds all potential spec values (e.g., '16GB', '2TB') in a string
        and groups them by unit type.
        """
        matches = _UNIT_REGEX.findall(text)
        found_values: Dict[str, List[str]] = {}
        for value, unit in matches:
            unit_key = unit.upper()
            if "CL" in unit_key:  # Special case for RAM Latency
                unit_key = "LATENCY"

            normalized_val = self._normalize_spec_text(f"{value}{unit}")
            if unit_key not in found_values:
                found_values[unit_key] = []
            found_values[unit_key].append(normalized_val)
        return found_values

    def _check_hard_gate_penalty(self, candidate_name: str) -> bool:
        """
        Checks for contradictions in critical fields.
        Returns True if a penalty should be applied (score=0), False otherwise.
        """
        if self.category_type not in _SPEC_MAPPING:
            return False  # No critical fields defined for this category

        _, critical_fields = _SPEC_MAPPING[self.category_type]
        candidate_values = self._extract_potential_values(candidate_name)
        if not candidate_values:
            return False  # No specs found in candidate name to contradict

        for field in critical_fields:
            spec_value_raw = self.specs.get(field)
            if not spec_value_raw:
                continue  # No base spec to compare against

            spec_value_normalized = self._normalize_spec_text(spec_value_raw)
            # Find the unit type of the spec value (e.g., 'GB' from '16GB')
            match = re.search(r"[a-zA-Z]+", spec_value_normalized)
            if not match:
                continue

            unit_key = match.group(0).upper()
            if unit_key not in candidate_values:
                continue  # Candidate name doesn't mention this type of spec

            # Penalty logic: if the candidate mentions this spec type, but
            # does NOT mention the correct value, it's a contradiction.
            candidate_spec_options = candidate_values[unit_key]
            if spec_value_normalized not in candidate_spec_options:
                return True  # PENALTY APPLIED

        return False

    def calculate_confidence_score(self, candidate_name: str) -> float:
        """
        Calculates a confidence score from 0.0 to 1.0.
        A score of 0.0 indicates a definite mismatch.
        """
        if not candidate_name or not isinstance(candidate_name, str):
            return 0.0

        # 1. Hard-gate penalty for critical spec mismatches
        if self._check_hard_gate_penalty(candidate_name):
            return 0.0

        # 2. Weighted fuzzy matching
        name_score = token_set_ratio(candidate_name.lower(), (self.product.normalized_name or "").lower())

        # Weight model_name higher as it's more specific
        if self.product.model_name:
            model_score = token_set_ratio(candidate_name.lower(), self.product.model_name.lower())
            # Weighted average: 60% model name, 40% normalized name
            final_score = (model_score * 0.6) + (name_score * 0.4)
        else:
            final_score = name_score

        # 3. Normalize to 0.0 - 1.0 and return
        return round(final_score / 100, 3)

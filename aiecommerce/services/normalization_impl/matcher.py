from typing import List, Optional

from thefuzz import process

from aiecommerce.models import ProductRawPDF


class FuzzyMatcher:
    """Uses fuzzy string matching to find the best product match."""

    def find_best_match(
        self,
        target_description: str,
        candidates: List[ProductRawPDF],
        threshold: int = 90,
    ) -> Optional[ProductRawPDF]:
        """
        Finds the best match for a target description from a list of candidates.

        Args:
            target_description: The string to match against.
            candidates: A list of ProductRawPDF objects to search within.
            threshold: The minimum similarity score (0-100) to consider a match.

        Returns:
            The best matching ProductRawPDF object or None if no match is found
            above the threshold.
        """
        if not target_description or not candidates:
            return None

        # Create a dictionary of description -> ProductRawPDF object
        choices = {candidate.raw_description: candidate for candidate in candidates if candidate.raw_description}

        # extractOne returns a tuple of (description, score, key)
        # but since our dictionary values are the objects, it's (description, score, ProductRawPDF)
        # We want the object itself.
        result = process.extractOne(target_description, choices.keys())

        if result and result[1] >= threshold:
            # The key is the description, so we look it up in our choices dict
            best_match_description = result[0]
            return choices[best_match_description]

        return None

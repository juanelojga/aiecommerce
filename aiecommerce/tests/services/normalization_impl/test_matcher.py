from unittest.mock import patch

import pytest

from aiecommerce.models.product import ProductRawPDF
from aiecommerce.services.normalization_impl.matcher import FuzzyMatcher

pytestmark = pytest.mark.django_db


class TestFuzzyMatcher:
    def test_returns_none_when_no_target_or_no_candidates(self):
        matcher = FuzzyMatcher()

        # No target
        assert matcher.find_best_match("", []) is None
        assert matcher.find_best_match(None, []) is None  # type: ignore[arg-type]

        # No candidates
        assert matcher.find_best_match("Some target", []) is None

    def test_returns_none_when_all_candidates_without_description(self):
        matcher = FuzzyMatcher()
        candidates = [
            ProductRawPDF(raw_description=None),
            ProductRawPDF(raw_description=None),
        ]

        # extractOne shouldn't find any choice; simulate library returning None
        with patch("aiecommerce.services.normalization_impl.matcher.process.extractOne", return_value=None):
            assert matcher.find_best_match("Target", candidates) is None

    def test_returns_none_when_below_threshold(self):
        matcher = FuzzyMatcher()
        a = ProductRawPDF(raw_description="Alpha product")
        b = ProductRawPDF(raw_description="Beta product")
        candidates = [a, b]

        # thefuzz returns score below default threshold (90)
        with patch(
            "aiecommerce.services.normalization_impl.matcher.process.extractOne",
            return_value=("Alpha product", 75),
        ):
            assert matcher.find_best_match("Alfa prod", candidates) is None

    def test_returns_match_when_score_at_threshold(self):
        matcher = FuzzyMatcher()
        a = ProductRawPDF(raw_description="Alpha product")
        b = ProductRawPDF(raw_description="Beta product")
        candidates = [a, b]

        with patch(
            "aiecommerce.services.normalization_impl.matcher.process.extractOne",
            return_value=("Beta product", 90),  # exactly at default threshold
        ):
            result = matcher.find_best_match("Beta prod", candidates)
            assert result is b

    def test_picks_best_among_multiple(self):
        matcher = FuzzyMatcher()
        a = ProductRawPDF(raw_description="USB Cable 1m")
        b = ProductRawPDF(raw_description="USB Cable 2m")
        c = ProductRawPDF(raw_description="HDMI Cable 1m")
        candidates = [a, b, c]

        # Simulate library selecting "USB Cable 2m" with high score
        with patch(
            "aiecommerce.services.normalization_impl.matcher.process.extractOne",
            return_value=("USB Cable 2m", 96),
        ):
            result = matcher.find_best_match("usb cable long", candidates)
            assert result is b

    def test_respects_custom_threshold(self):
        matcher = FuzzyMatcher()
        a = ProductRawPDF(raw_description="Gaming Mouse")
        b = ProductRawPDF(raw_description="Office Mouse")
        candidates = [a, b]

        # Score equals 80; using custom threshold 81 should fail, 80 should pass
        with patch(
            "aiecommerce.services.normalization_impl.matcher.process.extractOne",
            return_value=("Gaming Mouse", 80),
        ):
            assert matcher.find_best_match("mouse gamer", candidates, threshold=81) is None
            assert matcher.find_best_match("mouse gamer", candidates, threshold=80) is a

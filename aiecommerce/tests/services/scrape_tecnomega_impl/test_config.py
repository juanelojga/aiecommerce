import pytest

from aiecommerce.services.scrape_tecnomega_impl.config import (
    DEFAULT_BASE_URL,
    DEFAULT_CATEGORIES,
    ScrapeConfig,
    _parse_categories,
)
from aiecommerce.services.scrape_tecnomega_impl.exceptions import ScrapeConfigurationError


class TestParseCategories:
    def test_empty_string_returns_default_copy(self):
        result = _parse_categories("")
        assert result == DEFAULT_CATEGORIES
        # ensure it's a copy, not the same list object
        assert result is not DEFAULT_CATEGORIES

    def test_parses_and_trims_values(self):
        value = "notebook, tablets , , phone"
        assert _parse_categories(value) == ["notebook", "tablets", "phone"]

    def test_all_empty_entries_fall_back_to_default(self):
        assert _parse_categories(" , ") == DEFAULT_CATEGORIES


class TestScrapeConfig:
    def test_defaults_without_settings(self, settings):
        # Do not override project settings; verify that defaults reflect current settings
        cfg = ScrapeConfig()
        # If setting is empty or not set, should use DEFAULT_BASE_URL
        setting_base_url = getattr(settings, "TECNOMEGA_STOCK_LIST_BASE_URL", "")
        expected_base = setting_base_url if setting_base_url else DEFAULT_BASE_URL
        expected_categories = _parse_categories(getattr(settings, "TECNOMEGA_SCRAPE_CATEGORIES", ""))

        assert cfg.base_url == expected_base
        assert cfg.categories == expected_categories
        assert cfg.dry_run is False

    def test_respects_settings_and_parses_categories(self, settings):
        # base_url default is bound at import time; to test settings-driven defaults,
        # we need to reload the module after changing settings
        import importlib

        import aiecommerce.services.scrape_tecnomega_impl.config as config_module

        settings.TECNOMEGA_STOCK_LIST_BASE_URL = "https://example.com/search"
        settings.TECNOMEGA_SCRAPE_CATEGORIES = "laptop, desktop ,tablet"

        config_module = importlib.reload(config_module)
        ScrapeConfigReloaded = config_module.ScrapeConfig

        cfg = ScrapeConfigReloaded()
        assert cfg.base_url == "https://example.com/search"
        assert cfg.categories == ["laptop", "desktop", "tablet"]

    def test_empty_base_url_raises(self):
        with pytest.raises(ScrapeConfigurationError, match="Base URL cannot be empty"):
            ScrapeConfig(base_url="")

    def test_empty_categories_list_raises(self):
        with pytest.raises(ScrapeConfigurationError, match="Categories list cannot be empty"):
            ScrapeConfig(categories=[])

    def test_get_base_url_returns_base_url(self):
        cfg = ScrapeConfig(base_url="https://example.org/path")
        assert cfg.get_base_url() == "https://example.org/path"

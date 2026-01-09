from unittest.mock import ANY, MagicMock, patch

import pytest

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_search_impl.ean_api_strategy import EANSearchAPIStrategy

pytestmark = pytest.mark.django_db


class TestEANSearchAPIStrategy:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_matcher(self):
        return MagicMock()

    @pytest.fixture
    def strategy(self, mock_client, mock_matcher):
        return EANSearchAPIStrategy(client=mock_client, matcher=mock_matcher)

    def test_get_query_with_sku(self, strategy):
        product = ProductMaster(sku="SKU123", model_name="Some Model")
        assert strategy._get_query(product, use_sku=True) == "SKU123"

    def test_get_query_with_model_name_and_manufacturer(self, strategy):
        product = ProductMaster(model_name="Inspiron 15", specs={"manufacturer": "Dell"})
        assert strategy._get_query(product, use_sku=False) == "Dell Inspiron 15"

    def test_get_query_with_model_name_only(self, strategy):
        product = ProductMaster(model_name="Inspiron 15", specs={})
        assert strategy._get_query(product, use_sku=False) == "Inspiron 15"

    def test_get_query_with_short_model_name(self, strategy):
        product = ProductMaster(model_name="HP", specs={"manufacturer": "HP"})
        assert strategy._get_query(product, use_sku=False) is None

    def test_get_query_with_no_model_name(self, strategy):
        product = ProductMaster(model_name=None)
        assert strategy._get_query(product, use_sku=False) is None

    def test_get_cache_key(self, strategy):
        query = "Dell Inspiron 15"
        expected_key = "gtin_search:ean_api:dell_inspiron_15"
        assert strategy._get_cache_key(query) == expected_key

    @patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache")
    def test_execute_search_cache_hit(self, mock_cache, strategy, mock_client):
        query = "test query"
        cached_data = [{"name": "Product 1", "ean": "1234567890123"}]
        mock_cache.get.return_value = cached_data

        product = ProductMaster(sku="SKU1")

        with patch.object(strategy, "_process_results") as mock_process:
            strategy._execute_search(product, query)
            mock_process.assert_called_once_with(product, cached_data, False, strategy._get_cache_key(query))
            mock_client.search.assert_not_called()

    @patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache")
    def test_execute_search_cache_miss(self, mock_cache, strategy, mock_client):
        query = "test query"
        mock_cache.get.return_value = None
        api_results = [{"name": "Product 1", "ean": "1234567890123"}]
        mock_client.search.return_value = api_results

        product = ProductMaster(sku="SKU1")

        with patch.object(strategy, "_process_results") as mock_process:
            strategy._execute_search(product, query)
            mock_process.assert_called_once_with(product, api_results, True, strategy._get_cache_key(query))
            mock_client.search.assert_called_once_with(query)

    def test_process_results_golden_match(self, strategy, mock_matcher):
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Golden Product", "ean": "GOLDEN123"}]
        mock_matcher.calculate_confidence_score.return_value = (0.99, None)

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=True, cache_key="some_key")

            assert gtin == "GOLDEN123"
            mock_cache.set.assert_called_once()  # Should cache golden match immediately

    def test_process_results_best_candidate(self, strategy, mock_matcher):
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Bad Match", "ean": "BAD123"}, {"name": "Good Match", "ean": "GOOD123"}]
        # First result: score 0.5, second result: score 0.8
        mock_matcher.calculate_confidence_score.side_effect = [(0.5, None), (0.8, None)]

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=True, cache_key="some_key")

            assert gtin == "GOOD123"
            # Should cache all results at the end
            mock_cache.set.assert_called_once_with("some_key", results, timeout=ANY)

    def test_process_results_no_match_below_threshold(self, strategy, mock_matcher):
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Low Score Product", "ean": "LOW123"}]
        mock_matcher.calculate_confidence_score.return_value = (0.6, None)

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=True, cache_key="some_key")

            assert gtin is None
            mock_cache.set.assert_called_once_with("some_key", results, timeout=ANY)

    def test_process_results_not_live_search_no_caching(self, strategy, mock_matcher):
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Some Product", "ean": "EAN1"}]
        mock_matcher.calculate_confidence_score.return_value = (0.8, None)

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=False, cache_key="some_key")

            assert gtin == "EAN1"
            mock_cache.set.assert_not_called()

    def test_process_results_golden_match_not_live_no_caching(self, strategy, mock_matcher):
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Golden Product", "ean": "GOLDEN123"}]
        mock_matcher.calculate_confidence_score.return_value = (0.99, None)

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=False, cache_key="some_key")

            assert gtin == "GOLDEN123"
            mock_cache.set.assert_not_called()

    def test_process_results_empty_results(self, strategy):
        product = ProductMaster(sku="SKU1")
        results: list[dict] = []

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache") as mock_cache:
            gtin = strategy._process_results(product, results, is_live_search=True, cache_key="some_key")

            assert gtin is None
            mock_cache.set.assert_not_called()

    def test_search_for_gtin_model_name_success(self, strategy):
        product = ProductMaster(sku="SKU1", model_name="Valid Model")

        with patch.object(strategy, "_execute_search") as mock_execute:
            mock_execute.return_value = "GTIN_FROM_MODEL"

            gtin = strategy.search_for_gtin(product)

            assert gtin == "GTIN_FROM_MODEL"
            # Should have called _execute_search with model name query
            assert "valid model" in mock_execute.call_args_list[0][0][1].lower()

    def test_search_for_gtin_sku_fallback(self, strategy):
        product = ProductMaster(sku="SKU123", model_name="Valid Model")

        with patch.object(strategy, "_execute_search") as mock_execute:
            # First call (model name) returns None, second call (SKU) returns GTIN
            mock_execute.side_effect = [None, "GTIN_FROM_SKU"]

            gtin = strategy.search_for_gtin(product)

            assert gtin == "GTIN_FROM_SKU"
            assert mock_execute.call_count == 2
            # Second call should be for SKU
            assert mock_execute.call_args_list[1][0][1] == "SKU123"

    def test_search_for_gtin_no_match(self, strategy):
        product = ProductMaster(sku="SKU123", model_name="Valid Model")

        with patch.object(strategy, "_execute_search", return_value=None) as mock_execute:
            gtin = strategy.search_for_gtin(product)

            assert gtin is None
            assert mock_execute.call_count == 2

    def test_search_for_gtin_short_model_name_only_sku(self, strategy):
        # Model name "HP" is too short (<= 2), so _get_query(use_sku=False) returns None
        product = ProductMaster(sku="SKU_HP", model_name="HP")

        with patch.object(strategy, "_execute_search") as mock_execute:
            mock_execute.return_value = "GTIN_FROM_SKU"

            gtin = strategy.search_for_gtin(product)

            assert gtin == "GTIN_FROM_SKU"
            # Should have skipped model search and gone straight to SKU search
            assert mock_execute.call_count == 1
            assert mock_execute.call_args[0][1] == "SKU_HP"

    def test_get_query_no_specs(self, strategy):
        product = ProductMaster(model_name="Inspiron 15", specs=None)
        assert strategy._get_query(product, use_sku=False) == "Inspiron 15"

    def test_process_results_with_hard_gate_penalty_logging(self, strategy, mock_matcher):
        # This test ensures the logging logic for hard-gate penalty is hit
        product = ProductMaster(sku="SKU1")
        results = [{"name": "Penalty Product", "ean": "EAN1"}]
        # score 0.0 and critical_field "manufacturer"
        mock_matcher.calculate_confidence_score.return_value = (0.0, "manufacturer")

        with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.logger") as mock_logger:
            with patch("aiecommerce.services.gtin_search_impl.ean_api_strategy.cache"):
                strategy._process_results(product, results, is_live_search=True, cache_key="some_key")

                # Check if the penalty message was logged
                penalty_log_called = any("Hard-gate penalty by: manufacturer" in call.args[0] for call in mock_logger.info.call_args_list)
                assert penalty_log_called

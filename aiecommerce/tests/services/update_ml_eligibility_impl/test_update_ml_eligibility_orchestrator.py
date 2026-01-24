from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.services.update_ml_eligibility_impl.orchestrator import UpdateMlEligibilityCandidateOrchestrator


class TestUpdateMlEligibilityCandidateOrchestrator:
    @pytest.fixture
    def mock_selector(self):
        return MagicMock()

    @pytest.fixture
    def orchestrator(self, mock_selector):
        return UpdateMlEligibilityCandidateOrchestrator(selector=mock_selector)

    def test_run_no_products(self, orchestrator, mock_selector):
        queryset = MagicMock()
        queryset.count.return_value = 0
        mock_selector.get_queryset.return_value = queryset

        stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 0, "processed": 0}
        mock_selector.get_queryset.assert_called_once_with(False, False)
        queryset.iterator.assert_not_called()

    def test_run_dry_run_skips_saves_and_sleep(self, orchestrator, mock_selector):
        p1 = MagicMock()
        p1.code = "P1"
        p1.is_for_mercadolibre = False
        p2 = MagicMock()
        p2.code = "P2"
        p2.is_for_mercadolibre = False

        queryset = MagicMock()
        queryset.count.return_value = 2
        queryset.iterator.return_value = [p1, p2]
        mock_selector.get_queryset.return_value = queryset

        with patch("aiecommerce.services.update_ml_eligibility_impl.orchestrator.time.sleep") as mock_sleep:
            stats = orchestrator.run(force=False, dry_run=True, delay=0.1)

        assert stats == {"total": 2, "processed": 0}
        queryset.iterator.assert_called_once_with(chunk_size=100)
        p1.save.assert_not_called()
        p2.save.assert_not_called()
        assert p1.is_for_mercadolibre is False
        assert p2.is_for_mercadolibre is False
        mock_sleep.assert_not_called()

    def test_run_updates_products_and_sleeps(self, orchestrator, mock_selector):
        p1 = MagicMock()
        p1.code = "P1"
        p1.is_for_mercadolibre = False
        p2 = MagicMock()
        p2.code = "P2"
        p2.is_for_mercadolibre = False

        queryset = MagicMock()
        queryset.count.return_value = 2
        queryset.iterator.return_value = [p1, p2]
        mock_selector.get_queryset.return_value = queryset

        with patch("aiecommerce.services.update_ml_eligibility_impl.orchestrator.time.sleep") as mock_sleep:
            stats = orchestrator.run(force=True, dry_run=False, delay=0.1)

        assert stats == {"total": 2, "processed": 2}
        p1.save.assert_called_once_with(update_fields=["is_for_mercadolibre"])
        p2.save.assert_called_once_with(update_fields=["is_for_mercadolibre"])
        assert p1.is_for_mercadolibre is True
        assert p2.is_for_mercadolibre is True
        assert mock_sleep.call_count == 2

    def test_run_no_sleep_when_delay_zero(self, orchestrator, mock_selector):
        p1 = MagicMock()
        p1.code = "P1"

        queryset = MagicMock()
        queryset.count.return_value = 1
        queryset.iterator.return_value = [p1]
        mock_selector.get_queryset.return_value = queryset

        with patch("aiecommerce.services.update_ml_eligibility_impl.orchestrator.time.sleep") as mock_sleep:
            stats = orchestrator.run(force=False, dry_run=False, delay=0)

        assert stats == {"total": 1, "processed": 1}
        p1.save.assert_called_once_with(update_fields=["is_for_mercadolibre"])
        mock_sleep.assert_not_called()

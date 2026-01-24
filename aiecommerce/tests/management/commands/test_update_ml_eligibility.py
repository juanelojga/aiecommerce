import io
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command


@pytest.fixture
def mock_selector(monkeypatch):
    mock_instance = MagicMock()
    mock_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aiecommerce.management.commands.update_ml_eligibility.UpdateMlEligibilityCandidateSelector",
        mock_class,
    )
    return mock_class, mock_instance


@pytest.fixture
def mock_orchestrator(monkeypatch):
    mock_instance = MagicMock()
    mock_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aiecommerce.management.commands.update_ml_eligibility.UpdateMlEligibilityCandidateOrchestrator",
        mock_class,
    )
    return mock_class, mock_instance


def test_update_ml_eligibility_dry_run_no_products(mock_selector, mock_orchestrator):
    mock_selector_class, mock_selector_instance = mock_selector
    mock_orchestrator_class, mock_orchestrator_instance = mock_orchestrator
    mock_orchestrator_instance.run.return_value = {"total": 0, "processed": 0}

    out = io.StringIO()
    call_command("update_ml_eligibility", "--dry-run", stdout=out)

    output = out.getvalue()
    assert "--- DRY RUN MODE ACTIVATED ---" in output
    assert "No products found without images." in output

    mock_selector_class.assert_called_once_with()
    mock_orchestrator_class.assert_called_once_with(mock_selector_instance)
    mock_orchestrator_instance.run.assert_called_once_with(force=False, dry_run=True, delay=0.5)


def test_update_ml_eligibility_success_with_force_and_delay(mock_selector, mock_orchestrator):
    mock_selector_class, mock_selector_instance = mock_selector
    mock_orchestrator_class, mock_orchestrator_instance = mock_orchestrator
    mock_orchestrator_instance.run.return_value = {"total": 5, "processed": 3}

    out = io.StringIO()
    call_command("update_ml_eligibility", "--force", "--delay", "1.25", stdout=out)

    output = out.getvalue()
    assert "Completed. Processed 3/5 products" in output
    assert "Enqueued 3/5 tasks" in output

    mock_selector_class.assert_called_once_with()
    mock_orchestrator_class.assert_called_once_with(mock_selector_instance)
    mock_orchestrator_instance.run.assert_called_once_with(force=True, dry_run=False, delay=1.25)

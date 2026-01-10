import io
from typing import Any, cast
from unittest.mock import MagicMock

from django.core.management import call_command

from aiecommerce.management.commands.enrich_products_specs import Command as EnrichCommand


def _make_command() -> Any:
    cmd = cast(Any, EnrichCommand())
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    return cmd


def test_handle_success(monkeypatch):
    import aiecommerce.management.commands.enrich_products_specs as mod

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"enriched": 5, "total": 10}

    # We need to mock EnrichmentOrchestrator class to return our mock instance
    mock_orchestrator_class = MagicMock(return_value=mock_orchestrator_instance)
    monkeypatch.setattr(mod, "EnrichmentOrchestrator", mock_orchestrator_class)

    # Mock other dependencies to avoid actual initialization if they do anything heavy
    monkeypatch.setattr(mod, "ProductSpecificationsService", MagicMock())
    monkeypatch.setattr(mod, "ProductSpecificationsOrchestrator", MagicMock())
    monkeypatch.setattr(mod, "EnrichmentCandidateSelector", MagicMock())

    cmd = _make_command()

    options = {
        "force": False,
        "dry_run": False,
        "delay": 0.5,
    }

    cmd.handle(**options)

    out = cmd.stdout.getvalue()
    assert "Completed. Processed 5/10 products" in out

    mock_orchestrator_instance.run.assert_called_once_with(force=False, dry_run=False, delay=0.5)


def test_handle_force_and_dry_run(monkeypatch):
    import aiecommerce.management.commands.enrich_products_specs as mod

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"enriched": 2, "total": 2}

    mock_orchestrator_class = MagicMock(return_value=mock_orchestrator_instance)
    monkeypatch.setattr(mod, "EnrichmentOrchestrator", mock_orchestrator_class)

    monkeypatch.setattr(mod, "ProductSpecificationsService", MagicMock())
    monkeypatch.setattr(mod, "ProductSpecificationsOrchestrator", MagicMock())
    monkeypatch.setattr(mod, "EnrichmentCandidateSelector", MagicMock())

    cmd = _make_command()

    options = {
        "force": True,
        "dry_run": True,
        "delay": 1.0,
    }

    cmd.handle(**options)

    out = cmd.stdout.getvalue()
    assert "--- DRY RUN MODE ACTIVATED ---" in out
    assert "Completed. Processed 2/2 products" in out

    mock_orchestrator_instance.run.assert_called_once_with(force=True, dry_run=True, delay=1.0)


def test_call_command():
    # Test using call_command to verify arguments parsing
    from unittest.mock import patch

    with patch("aiecommerce.management.commands.enrich_products_specs.EnrichmentOrchestrator") as mock_orch_class:
        mock_orch_instance = mock_orch_class.return_value
        mock_orch_instance.run.return_value = {"enriched": 0, "total": 0}

        with (
            patch("aiecommerce.management.commands.enrich_products_specs.ProductSpecificationsService"),
            patch("aiecommerce.management.commands.enrich_products_specs.ProductSpecificationsOrchestrator"),
            patch("aiecommerce.management.commands.enrich_products_specs.EnrichmentCandidateSelector"),
        ):
            call_command("enrich_products_specs", "--force", "--dry-run", "--delay", "2.0")

            mock_orch_instance.run.assert_called_once_with(force=True, dry_run=True, delay=2.0)

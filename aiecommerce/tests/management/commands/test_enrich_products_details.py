import io
from typing import Any, cast
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from aiecommerce.management.commands.enrich_products_details import Command as DetailsCommand


def _make_command() -> Any:
    cmd = cast(Any, DetailsCommand())
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    return cmd


def test_handle_success(monkeypatch):
    import aiecommerce.management.commands.enrich_products_details as mod

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"processed": 5, "total": 10}

    mock_orchestrator_class = MagicMock(return_value=mock_orchestrator_instance)
    monkeypatch.setattr(mod, "TecnomegaDetailOrchestrator", mock_orchestrator_class)

    # Mock other dependencies
    monkeypatch.setattr(mod, "TecnomegaDetailSelector", MagicMock())
    monkeypatch.setattr(mod, "TecnomegaDetailFetcher", MagicMock())
    monkeypatch.setattr(mod, "TecnomegaDetailParser", MagicMock())

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


def test_handle_dry_run_and_force(monkeypatch):
    import aiecommerce.management.commands.enrich_products_details as mod

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"processed": 2, "total": 2}

    mock_orchestrator_class = MagicMock(return_value=mock_orchestrator_instance)
    monkeypatch.setattr(mod, "TecnomegaDetailOrchestrator", mock_orchestrator_class)

    monkeypatch.setattr(mod, "TecnomegaDetailSelector", MagicMock())
    monkeypatch.setattr(mod, "TecnomegaDetailFetcher", MagicMock())
    monkeypatch.setattr(mod, "TecnomegaDetailParser", MagicMock())

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
    with patch("aiecommerce.management.commands.enrich_products_details.TecnomegaDetailOrchestrator") as mock_orch_class:
        mock_orch_instance = mock_orch_class.return_value
        mock_orch_instance.run.return_value = {"processed": 0, "total": 0}

        with (
            patch("aiecommerce.management.commands.enrich_products_details.TecnomegaDetailSelector"),
            patch("aiecommerce.management.commands.enrich_products_details.TecnomegaDetailFetcher"),
            patch("aiecommerce.management.commands.enrich_products_details.TecnomegaDetailParser"),
        ):
            call_command("enrich_products_details", "--force", "--dry-run", "--delay", "2.0")

            mock_orch_instance.run.assert_called_once_with(force=True, dry_run=True, delay=2.0)

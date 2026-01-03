from typing import Any, Dict

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


class MockMercadoLibreEligibilityService:
    def __init__(self) -> None:
        self.called_with: Dict[str, Any] = {}

    def update_eligibility_flags(self, dry_run: bool = False) -> Dict[str, int]:
        self.called_with["dry_run"] = dry_run
        if dry_run:
            return {"enabled": 5, "disabled": 2}
        return {"enabled": 10, "disabled": 3}


@pytest.fixture
def mock_service(monkeypatch: Any) -> MockMercadoLibreEligibilityService:
    mock_instance = MockMercadoLibreEligibilityService()
    monkeypatch.setattr(
        "aiecommerce.management.commands.update_ml_eligibility.MercadoLibreEligibilityService",
        lambda x: mock_instance,
    )
    return mock_instance


def test_update_ml_eligibility_dry_run(mock_service: MockMercadoLibreEligibilityService, capsys: Any) -> None:
    # Act
    call_command("update_ml_eligibility", "--dry-run")

    # Assert
    assert mock_service.called_with["dry_run"] is True

    out = capsys.readouterr().out
    assert "--- DRY RUN MODE ACTIVATED ---" in out
    assert "Updating eligibility flags..." in out
    assert "--- DRY RUN RESULTS ---" in out
    assert "Products that would be enabled: 5" in out
    assert "Products that would be disabled: 2" in out
    assert "Operation finished." in out


def test_update_ml_eligibility_normal_run(mock_service: MockMercadoLibreEligibilityService, capsys: Any) -> None:
    # Act
    call_command("update_ml_eligibility")

    # Assert
    assert mock_service.called_with["dry_run"] is False

    out = capsys.readouterr().out
    assert "--- DRY RUN MODE ACTIVATED ---" not in out
    assert "Updating eligibility flags..." in out
    assert "--- UPDATE COMPLETE ---" in out
    assert "Products enabled: 10" in out
    assert "Products disabled: 3" in out
    assert "Operation finished." in out

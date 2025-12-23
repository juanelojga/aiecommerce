from typing import Dict, Optional

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_normalize_products_with_session_id_prints_success(monkeypatch, capsys):
    # Arrange: stub the service class and its return value
    class DummyService:
        def __init__(self) -> None:
            self.called_with: Optional[str] = None

        def normalize_products(self, *, scrape_session_id: Optional[str] = None) -> Dict[str, int]:
            self.called_with = scrape_session_id
            return {
                "processed_count": 10,
                "created_count": 3,
                "updated_count": 6,
                "inactive_count": 1,
            }

    dummy_instance = DummyService()

    # Replace the class with a factory returning our instance
    monkeypatch.setattr(
        "aiecommerce.management.commands.normalize_products.ProductNormalizationService",
        lambda: dummy_instance,
    )

    # Act
    call_command("normalize_products", "--session-id", "abc123")

    # Assert: service called with provided session id
    assert dummy_instance.called_with == "abc123"

    # And output contains success lines and counts
    out = capsys.readouterr().out
    assert "Starting product normalization..." in out
    assert "Normalization process finished successfully." in out
    assert "Processed Web Items: 10" in out
    assert "Products Created: 3" in out
    assert "Products Updated: 6" in out
    assert "Products Marked as Inactive: 1" in out


def test_normalize_products_without_session_id_calls_service_with_none(monkeypatch, capsys):
    class DummyService:
        def __init__(self) -> None:
            self.called_with: Optional[str] = "__unset__"

        def normalize_products(self, *, scrape_session_id: Optional[str] = None) -> Dict[str, int]:
            self.called_with = scrape_session_id
            return {
                "processed_count": 0,
                "created_count": 0,
                "updated_count": 0,
                "inactive_count": 0,
            }

    dummy_instance = DummyService()

    monkeypatch.setattr(
        "aiecommerce.management.commands.normalize_products.ProductNormalizationService",
        lambda: dummy_instance,
    )

    call_command("normalize_products")

    assert dummy_instance.called_with is None

    out = capsys.readouterr().out
    assert "Starting product normalization..." in out
    assert "Normalization process finished successfully." in out


def test_normalize_products_when_service_returns_none_prints_warning(monkeypatch, capsys):
    class DummyService:
        def __init__(self) -> None:
            self.called_with: Optional[str] = "__unset__"

        def normalize_products(self, *, scrape_session_id: Optional[str] = None) -> Optional[Dict[str, int]]:
            self.called_with = scrape_session_id
            return None

    dummy_instance = DummyService()

    monkeypatch.setattr(
        "aiecommerce.management.commands.normalize_products.ProductNormalizationService",
        lambda: dummy_instance,
    )

    call_command("normalize_products")

    assert dummy_instance.called_with is None

    out = capsys.readouterr().out
    assert "Starting product normalization..." in out
    # Warning style prefixes output with the message; ensure core text is present
    assert "Normalization process did not run. Check logs for details." in out

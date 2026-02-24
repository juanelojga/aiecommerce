import io
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError


@pytest.fixture
def mock_auth_service(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.MercadoLibreAuthService", MagicMock(return_value=mock))
    return mock


@pytest.fixture
def mock_token_model(monkeypatch):
    from aiecommerce.models import MercadoLibreToken

    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreToken.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.MercadoLibreToken", mock)
    return mock


@pytest.fixture
def mock_batch_orchestrator(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.BatchPublisherOrchestrator", MagicMock(return_value=mock_instance))
    return mock_instance


@pytest.fixture
def mock_dependencies(monkeypatch):
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.MercadoLibreClient", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.instructor", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.OpenAI", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.MercadolibreAttributeFixer", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.MercadoLibrePublisherService", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.PublisherOrchestrator", MagicMock())


@pytest.fixture
def mock_telegram_task(monkeypatch):
    """Mock the Telegram notification task."""
    mock = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product_batch.send_telegram_notification", mock)
    return mock


def test_publish_ml_product_batch_success_production(mock_token_model, mock_auth_service, mock_batch_orchestrator, mock_dependencies, mock_telegram_task):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_batch_orchestrator.run.return_value = {"success": 5, "errors": 0, "skipped": 0, "published_ids": ["MLB123", "MLB456"]}

    # Run
    out = io.StringIO()
    call_command("publish_ml_product_batch", stdout=out)

    # Assert
    output = out.getvalue()
    assert "--- Starting batch product publication in PRODUCTION mode ---" in output
    assert "5 succeeded" in output
    assert "0 failed" in output
    assert "0 skipped" in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")
    mock_batch_orchestrator.run.assert_called_once_with(dry_run=False, sandbox=False)

    # Verify Telegram notification was triggered
    mock_telegram_task.apply_async.assert_called_once()
    notification_message = mock_telegram_task.apply_async.call_args.kwargs["args"][0]
    assert "✅ Batch Publishing Complete" in notification_message
    assert "PRODUCTION" in notification_message


def test_publish_ml_product_batch_success_sandbox(mock_token_model, mock_auth_service, mock_batch_orchestrator, mock_dependencies, mock_telegram_task):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_test_123"
    mock_token.access_token = "sandbox_token"

    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_batch_orchestrator.run.return_value = {"success": 3, "errors": 1, "skipped": 0, "published_ids": ["MLB789"]}

    # Run
    out = io.StringIO()
    call_command("publish_ml_product_batch", "--sandbox", stdout=out)

    # Assert
    output = out.getvalue()
    assert "--- Starting batch product publication in SANDBOX mode ---" in output
    assert "3 succeeded" in output
    assert "1 failed" in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=True)
    mock_batch_orchestrator.run.assert_called_once_with(dry_run=False, sandbox=True)

    # Verify Telegram notification for errors
    notification_message = mock_telegram_task.apply_async.call_args.kwargs["args"][0]
    assert "⚠️" in notification_message or "SANDBOX" in notification_message


def test_publish_ml_product_batch_dry_run(mock_token_model, mock_auth_service, mock_batch_orchestrator, mock_dependencies, mock_telegram_task):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_batch_orchestrator.run.return_value = {"success": 1, "errors": 0, "skipped": 2, "published_ids": ["MLB123"]}

    # Run
    out = io.StringIO()
    call_command("publish_ml_product_batch", "--dry-run", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Dry run is enabled" in output
    assert "1 succeeded" in output
    assert "2 skipped" in output
    mock_batch_orchestrator.run.assert_called_once_with(dry_run=True, sandbox=False)

    # Verify dry run notification
    notification_message = mock_telegram_task.apply_async.call_args.kwargs["args"][0]
    assert "ℹ️" in notification_message or "Dry Run" in notification_message


def test_publish_ml_product_batch_no_token(mock_token_model, mock_auth_service):
    # Setup
    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = None

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("publish_ml_product_batch")

    assert "No token found for production user. Please authenticate first." in str(excinfo.value)


def test_publish_ml_product_batch_token_error(mock_token_model, mock_auth_service):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid token")

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("publish_ml_product_batch")

    assert "Error retrieving valid token: Invalid token" in str(excinfo.value)


def test_publish_ml_product_batch_unexpected_error(mock_token_model, mock_auth_service, mock_batch_orchestrator, mock_dependencies, mock_telegram_task):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_batch_orchestrator.run.side_effect = Exception("Something went wrong")

    # Run & Assert
    with pytest.raises(Exception) as excinfo:
        call_command("publish_ml_product_batch")

    assert "Something went wrong" in str(excinfo.value)


def test_telegram_notification_failure_does_not_break_command(mock_token_model, mock_auth_service, mock_batch_orchestrator, mock_dependencies, mock_telegram_task):
    """Test that Telegram notification failure doesn't cause command to fail."""
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_batch_orchestrator.run.return_value = {"success": 5, "errors": 0, "skipped": 0, "published_ids": ["MLB999"]}

    # Make notification fail
    mock_telegram_task.apply_async.side_effect = Exception("Telegram API error")

    # Run - should not raise exception
    out = io.StringIO()
    call_command("publish_ml_product_batch", stdout=out)

    output = out.getvalue()
    assert "Batch publication finished" in output
    assert "5 succeeded" in output

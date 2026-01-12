import io
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError


@pytest.fixture
def mock_auth_service(monkeypatch):
    mock = MagicMock()
    # Inside the handle method, MercadoLibreAuthService() is called
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product.MercadoLibreAuthService", MagicMock(return_value=mock))
    return mock


@pytest.fixture
def mock_token_model(monkeypatch):
    from aiecommerce.models import MercadoLibreToken

    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreToken.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product.MercadoLibreToken", mock)
    return mock


@pytest.fixture
def mock_orchestrator(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product.PublisherOrchestrator", MagicMock(return_value=mock_instance))
    return mock_instance


@pytest.fixture
def mock_client_and_publisher(monkeypatch):
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product.MercadoLibreClient", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.publish_ml_product.MercadoLibrePublisherService", MagicMock())


def test_publish_ml_product_success_production(mock_token_model, mock_auth_service, mock_orchestrator, mock_client_and_publisher):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Run
    out = io.StringIO()
    call_command("publish_ml_product", "PROD123", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Starting product publication for 'PROD123' in PRODUCTION mode" in output
    assert "Publication process finished" in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")
    mock_orchestrator.run.assert_called_once_with(product_code="PROD123", dry_run=False, sandbox=False)


def test_publish_ml_product_success_sandbox(mock_token_model, mock_auth_service, mock_orchestrator, mock_client_and_publisher):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_test_123"
    mock_token.access_token = "sandbox_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Run
    out = io.StringIO()
    call_command("publish_ml_product", "PROD123", "--sandbox", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Starting product publication for 'PROD123' in SANDBOX mode" in output
    assert "Publication process finished" in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=True)
    mock_orchestrator.run.assert_called_once_with(product_code="PROD123", dry_run=False, sandbox=True)


def test_publish_ml_product_dry_run(mock_token_model, mock_auth_service, mock_orchestrator, mock_client_and_publisher):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Run
    out = io.StringIO()
    call_command("publish_ml_product", "PROD123", "--dry-run", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Dry run is enabled" in output
    mock_orchestrator.run.assert_called_once_with(product_code="PROD123", dry_run=True, sandbox=False)


def test_publish_ml_product_no_token(mock_token_model, mock_auth_service):
    # Setup
    from aiecommerce.models import MercadoLibreToken

    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("publish_ml_product", "PROD123")

    assert "No token found for site MEC" in str(excinfo.value)


def test_publish_ml_product_token_error(mock_token_model, mock_auth_service):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid token")

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("publish_ml_product", "PROD123")

    assert "Error retrieving valid token for site MEC: Invalid token" in str(excinfo.value)


def test_publish_ml_product_unexpected_error(mock_token_model, mock_auth_service, mock_orchestrator, mock_client_and_publisher):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_orchestrator.run.side_effect = Exception("Something went wrong")

    # Run
    out = io.StringIO()
    call_command("publish_ml_product", "PROD123", stdout=out)

    # Assert
    output = out.getvalue()
    assert "An unexpected error occurred: Something went wrong" in output

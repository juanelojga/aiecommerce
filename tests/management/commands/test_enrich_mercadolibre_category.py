import io
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError


@pytest.fixture
def mock_auth_service(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadoLibreAuthService", MagicMock(return_value=mock))
    return mock


@pytest.fixture
def mock_token_model(monkeypatch):
    from aiecommerce.models import MercadoLibreToken

    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreToken.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadoLibreToken", mock)
    return mock


@pytest.fixture
def mock_orchestrator(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.enrich_mercadolibre_category.MercadolibreEnrichmentCategoryOrchestrator",
        MagicMock(return_value=mock_instance),
    )
    return mock_instance


@pytest.fixture
def mock_dependencies(monkeypatch):
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadolibreCategorySelector", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadolibreCategoryPredictorService", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadolibreCategoryAttributeFetcher", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadoLibrePriceEngine", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadoLibreStockEngine", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadolibreAIAttributeFiller", MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.MercadoLibreClient", MagicMock())

    mock_instructor = MagicMock()
    mock_instructor.from_openai.return_value = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.instructor", mock_instructor)

    mock_openai = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.OpenAI", mock_openai)

    return {"instructor": mock_instructor, "openai": mock_openai}


@pytest.fixture
def openrouter_settings(monkeypatch):
    import aiecommerce.management.commands.enrich_mercadolibre_category as mod

    monkeypatch.setattr(mod.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(mod.settings, "OPENROUTER_BASE_URL", "https://openrouter.test")


def test_enrich_mercadolibre_category_success(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 3, "total": 5}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "Completed. Processed 3/5 products" in output
    assert "Enqueued 3/5 tasks" in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")
    mock_orchestrator.run.assert_called_once_with(force=False, dry_run=False, delay=0.5, category=None)
    mock_dependencies["openai"].assert_called_once_with(api_key="test-key", base_url="https://openrouter.test")
    mock_dependencies["instructor"].from_openai.assert_called_once()


def test_enrich_mercadolibre_category_dry_run_with_category(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 1, "total": 2}

    out = io.StringIO()
    call_command(
        "enrich_mercadolibre_category",
        "--force",
        "--dry-run",
        "--delay",
        "1.5",
        "--category",
        "Electronics",
        stdout=out,
    )

    output = out.getvalue()
    assert "--- DRY RUN MODE ACTIVATED ---" in output
    assert "Completed. Processed 1/2 products" in output

    mock_orchestrator.run.assert_called_once_with(force=True, dry_run=True, delay=1.5, category="Electronics")


def test_enrich_mercadolibre_category_no_products(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 0, "total": 0}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "No products found without categories.." in output
    mock_orchestrator.run.assert_called_once_with(force=False, dry_run=False, delay=0.5, category=None)


def test_enrich_mercadolibre_category_no_token(mock_token_model, mock_auth_service):
    from aiecommerce.models import MercadoLibreToken

    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "No token found for site 'MEC'. Please authenticate first." in str(excinfo.value)


def test_enrich_mercadolibre_category_token_error(mock_token_model, mock_auth_service):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid token")

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "Error retrieving valid token for site 'MEC': Invalid token" in str(excinfo.value)

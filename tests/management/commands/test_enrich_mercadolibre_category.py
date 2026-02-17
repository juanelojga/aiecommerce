import io
from unittest.mock import MagicMock

import instructor
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
    mocks = {
        "MercadolibreCategorySelector": MagicMock(),
        "MercadolibreCategoryPredictorService": MagicMock(),
        "MercadolibreCategoryAttributeFetcher": MagicMock(),
        "MercadoLibrePriceEngine": MagicMock(),
        "MercadoLibreStockEngine": MagicMock(),
        "MercadolibreAIAttributeFiller": MagicMock(),
        "MercadoLibreClient": MagicMock(),
    }

    for name, mock in mocks.items():
        monkeypatch.setattr(f"aiecommerce.management.commands.enrich_mercadolibre_category.{name}", mock)

    # Patch from_openai method instead of the entire instructor module
    mock_from_openai = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.instructor.from_openai", mock_from_openai)

    mock_openai = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.OpenAI", mock_openai)

    mocks.update({"from_openai": mock_from_openai, "openai": mock_openai})
    return mocks


@pytest.fixture
def openrouter_settings(monkeypatch):
    """Configure OpenRouter API settings for testing."""
    import aiecommerce.management.commands.enrich_mercadolibre_category as mod

    monkeypatch.setattr(mod.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(mod.settings, "OPENROUTER_BASE_URL", "https://openrouter.test")


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing log output."""
    mock = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.enrich_mercadolibre_category.logger", mock)
    return mock


def test_enrich_mercadolibre_category_success(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test successful category enrichment with default parameters."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 3, "total": 5}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "Completed: 3/5 products processed" in output
    assert "Warning: 2 products failed to process" in output

    # Verify authentication
    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")

    # Verify orchestrator call
    mock_orchestrator.run.assert_called_once_with(force=False, dry_run=False, delay=0.5, category=None)

    # Verify OpenAI initialization
    mock_dependencies["openai"].assert_called_once_with(api_key="test-key", base_url="https://openrouter.test")
    
    # Verify instructor initialization with JSON mode
    call_args = mock_dependencies["from_openai"].call_args
    assert call_args[1]["mode"] == instructor.Mode.JSON

    # Verify logging
    mock_logger.info.assert_any_call("Starting MercadoLibre category enrichment: force=False, dry_run=False, delay=0.5, category=None, site_id=MEC")
    mock_logger.info.assert_any_call("Successfully authenticated with MercadoLibre (site: MEC, user_id: user_123)")
    mock_logger.info.assert_any_call("Category enrichment complete: 3/5 products processed")


def test_enrich_mercadolibre_category_dry_run_with_category(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test dry-run mode with category filter and custom delay."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 2, "total": 2}

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
    assert "Completed: 2/2 products would be processed" in output
    assert "Warning:" not in output  # No warning when all processed

    mock_orchestrator.run.assert_called_once_with(force=True, dry_run=True, delay=1.5, category="Electronics")
    mock_logger.info.assert_any_call("Starting MercadoLibre category enrichment: force=True, dry_run=True, delay=1.5, category=Electronics, site_id=MEC")
    mock_logger.info.assert_any_call("Category enrichment complete: 2/2 products would be processed")


def test_enrich_mercadolibre_category_no_products(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test handling when no products need enrichment."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 0, "total": 0}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "No products found that need category enrichment." in output
    mock_orchestrator.run.assert_called_once_with(force=False, dry_run=False, delay=0.5, category=None)


def test_enrich_mercadolibre_category_no_token(mock_token_model, mock_auth_service, mock_logger):
    """Test error handling when no authentication token exists."""
    from aiecommerce.models import MercadoLibreToken

    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "No production token found for site 'MEC'" in str(excinfo.value)
    assert "Please run 'python manage.py verify_ml_handshake' to authenticate first" in str(excinfo.value)


def test_enrich_mercadolibre_category_token_error(mock_token_model, mock_auth_service, mock_logger):
    """Test error handling when token refresh fails."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid token")

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "Error retrieving valid token for site 'MEC': Invalid token" in str(excinfo.value)


def test_enrich_mercadolibre_category_custom_site_id(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test using custom site ID parameter."""
    mock_token = MagicMock()
    mock_token.user_id = "user_456"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 1, "total": 1}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", "--site-id", "MLU", stdout=out)

    # Verify site_id was passed to logger
    mock_logger.info.assert_any_call("Starting MercadoLibre category enrichment: force=False, dry_run=False, delay=0.5, category=None, site_id=MLU")
    mock_logger.info.assert_any_call("Successfully authenticated with MercadoLibre (site: MLU, user_id: user_456)")


def test_enrich_mercadolibre_category_missing_openrouter_settings(mock_token_model, mock_auth_service, mock_dependencies, monkeypatch):
    """Test error handling when OpenRouter settings are missing."""
    import aiecommerce.management.commands.enrich_mercadolibre_category as mod

    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Missing API key
    monkeypatch.setattr(mod.settings, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(mod.settings, "OPENROUTER_BASE_URL", "https://openrouter.test")

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be configured in settings" in str(excinfo.value)


def test_enrich_mercadolibre_category_unexpected_exception(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test handling of unexpected exceptions during enrichment."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.side_effect = RuntimeError("Unexpected error during processing")

    with pytest.raises(CommandError) as excinfo:
        call_command("enrich_mercadolibre_category")

    assert "Failed to enrich categories: Unexpected error during processing" in str(excinfo.value)
    mock_logger.exception.assert_called_once()


def test_enrich_mercadolibre_category_all_products_processed(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test successful processing of all products (no failures)."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 5, "total": 5}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "Completed: 5/5 products processed" in output
    assert "Warning:" not in output  # No warning when all products succeed


def test_enrich_mercadolibre_category_partial_success(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test partial processing with some failures."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 7, "total": 10}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", stdout=out)

    output = out.getvalue()
    assert "Completed: 7/10 products processed" in output
    assert "Warning: 3 products failed to process" in output


def test_enrich_mercadolibre_category_force_flag(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test force reprocessing flag."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 2, "total": 2}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", "--force", stdout=out)

    mock_orchestrator.run.assert_called_once_with(force=True, dry_run=False, delay=0.5, category=None)
    mock_logger.info.assert_any_call("Starting MercadoLibre category enrichment: force=True, dry_run=False, delay=0.5, category=None, site_id=MEC")


def test_enrich_mercadolibre_category_dry_run_no_failures(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test that dry-run mode never shows failure warnings."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 3, "total": 5}

    out = io.StringIO()
    call_command("enrich_mercadolibre_category", "--dry-run", stdout=out)

    output = out.getvalue()
    assert "would be processed" in output
    # In dry-run mode, we shouldn't show warnings about failures
    assert "Warning:" not in output


def test_enrich_mercadolibre_category_service_initialization(mock_token_model, mock_auth_service, mock_orchestrator, mock_dependencies, openrouter_settings, mock_logger):
    """Test that all services are initialized correctly."""
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token
    mock_orchestrator.run.return_value = {"processed": 1, "total": 1}

    call_command("enrich_mercadolibre_category")

    # These should have been called during initialization
    assert mock_dependencies["MercadolibreCategorySelector"].called
    assert mock_dependencies["MercadolibreCategoryPredictorService"].called
    assert mock_dependencies["MercadolibreCategoryAttributeFetcher"].called
    assert mock_dependencies["MercadoLibrePriceEngine"].called
    assert mock_dependencies["MercadoLibreStockEngine"].called
    assert mock_dependencies["MercadolibreAIAttributeFiller"].called
    assert mock_dependencies["MercadoLibreClient"].called

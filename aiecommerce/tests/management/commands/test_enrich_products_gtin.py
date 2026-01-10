from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestEnrichProductsGTINCommand:
    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINDiscoveryOrchestrator")
    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINSearchSelector")
    @patch("aiecommerce.management.commands.enrich_products_gtin.build")
    def test_handle_no_products(self, mock_build, mock_selector, mock_orchestrator, capsys):
        # Setup
        mock_instance = mock_orchestrator.return_value
        mock_instance.run.return_value = {"total": 0, "processed": 0}

        # Execute
        call_command("enrich_products_gtin")

        # Verify
        captured = capsys.readouterr()
        assert "No products found without images." in captured.out
        mock_instance.run.assert_called_once_with(force=False, dry_run=False, delay=0.5)

    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINDiscoveryOrchestrator")
    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINSearchSelector")
    @patch("aiecommerce.management.commands.enrich_products_gtin.build")
    def test_handle_dry_run(self, mock_build, mock_selector, mock_orchestrator, capsys):
        # Setup
        mock_instance = mock_orchestrator.return_value
        mock_instance.run.return_value = {"total": 5, "processed": 0}

        # Execute
        call_command("enrich_products_gtin", "--dry-run")

        # Verify
        captured = capsys.readouterr()
        assert "--- DRY RUN MODE ACTIVATED ---" in captured.out
        mock_instance.run.assert_called_once_with(force=False, dry_run=True, delay=0.5)

    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINDiscoveryOrchestrator")
    @patch("aiecommerce.management.commands.enrich_products_gtin.GTINSearchSelector")
    @patch("aiecommerce.management.commands.enrich_products_gtin.build")
    @patch("aiecommerce.management.commands.enrich_products_gtin.GoogleGTINStrategy")
    def test_handle_success(self, mock_strategy, mock_build, mock_selector, mock_orchestrator, capsys):
        # Setup
        mock_instance = mock_orchestrator.return_value
        mock_instance.run.return_value = {"total": 10, "processed": 7}

        # Execute
        call_command("enrich_products_gtin", "--force", "--delay", "1.0")

        # Verify
        captured = capsys.readouterr()
        assert "Completed. Processed 7/10 products" in captured.out
        assert "Enqueued 7/10 tasks" in captured.out
        mock_instance.run.assert_called_once_with(force=True, dry_run=False, delay=1.0)

    @patch("aiecommerce.management.commands.enrich_products_gtin.settings")
    @patch("aiecommerce.management.commands.enrich_products_gtin.build")
    def test_google_api_client_initialization(self, mock_build, mock_settings):
        # Setup
        mock_settings.GOOGLE_API_KEY = "fake_key"
        mock_settings.GOOGLE_SEARCH_ENGINE_ID = "fake_id"

        # To avoid running the whole thing, we just test the logic inside handle if possible
        # but call_command is easier.
        with patch("aiecommerce.management.commands.enrich_products_gtin.GTINDiscoveryOrchestrator") as mock_orchestrator:
            mock_orchestrator.return_value.run.return_value = {"total": 0, "processed": 0}
            call_command("enrich_products_gtin")

            mock_build.assert_called_once_with("customsearch", "v1", developerKey="fake_key")

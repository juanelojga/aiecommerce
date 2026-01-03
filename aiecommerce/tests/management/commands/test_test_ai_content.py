from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestTestAIContentCommand:
    @patch("aiecommerce.management.commands.test_ai_content.TitleGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.DescriptionGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.AIContentOrchestrator")
    def test_handle_success_dry_run(self, mock_orchestrator_class, mock_desc_gen, mock_title_gen, capsys):
        # Setup
        product = ProductMasterFactory(code="TEST-PROD-01", description="Original Desc", category="Category 1")
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.process_product_content.return_value = {"success": True}

        # We need to simulate the product having seo_title and seo_description after processing
        # since the command prints them from the product object.
        product.seo_title = "Generated Title"
        product.seo_description = "Generated Description"
        product.save()

        # Execute
        call_command("test_ai_content", "TEST-PROD-01")

        # Verify
        captured = capsys.readouterr()
        assert "Processing product: TEST-PROD-01" in captured.out
        assert "Category: Category 1" in captured.out
        assert "Original Description: Original Desc" in captured.out
        assert "GENERATED SEO TITLE (15 chars): Generated Title" in captured.out
        assert "GENERATED SEO DESCRIPTION: Generated Description" in captured.out
        assert "[DRY RUN] Content was not saved." in captured.out

        mock_orchestrator.process_product_content.assert_called_once_with(product, dry_run=True, force_refresh=False)

    @patch("aiecommerce.management.commands.test_ai_content.TitleGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.DescriptionGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.AIContentOrchestrator")
    def test_handle_success_no_dry_run(self, mock_orchestrator_class, mock_desc_gen, mock_title_gen, capsys):
        # Setup
        product = ProductMasterFactory(code="TEST-PROD-02")
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.process_product_content.return_value = {"success": True}

        # Execute
        call_command("test_ai_content", "TEST-PROD-02", "--no-dry-run")

        # Verify
        captured = capsys.readouterr()
        assert "Content has been saved to the database." in captured.out
        mock_orchestrator.process_product_content.assert_called_once_with(product, dry_run=False, force_refresh=False)

    @patch("aiecommerce.management.commands.test_ai_content.TitleGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.DescriptionGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.AIContentOrchestrator")
    def test_handle_success_force(self, mock_orchestrator_class, mock_desc_gen, mock_title_gen, capsys):
        # Setup
        product = ProductMasterFactory(code="TEST-PROD-03")
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.process_product_content.return_value = {"success": True}

        # Execute
        call_command("test_ai_content", "TEST-PROD-03", "--force")

        # Verify
        mock_orchestrator.process_product_content.assert_called_once_with(product, dry_run=True, force_refresh=True)

    def test_handle_product_not_found(self):
        # Execute & Verify
        with pytest.raises(CommandError) as excinfo:
            call_command("test_ai_content", "NON-EXISTENT")

        assert 'Product with code "NON-EXISTENT" does not exist.' in str(excinfo.value)

    @patch("aiecommerce.management.commands.test_ai_content.TitleGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.DescriptionGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.AIContentOrchestrator")
    def test_handle_skipped(self, mock_orchestrator_class, mock_desc_gen, mock_title_gen, capsys):
        # Setup
        product = ProductMasterFactory(code="TEST-PROD-04")
        mock_orchestrator = mock_orchestrator_class.return_value
        # Orchestrator returns None or something that indicates skip (though current code checks result and result.get("error"))
        mock_orchestrator.process_product_content.return_value = None

        # Execute
        call_command("test_ai_content", "TEST-PROD-04")

        # Verify
        captured = capsys.readouterr()
        assert "Content generation was skipped. Use --force to override." in captured.out
        mock_orchestrator.process_product_content.assert_called_once_with(product, dry_run=True, force_refresh=False)

    @patch("aiecommerce.management.commands.test_ai_content.TitleGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.DescriptionGeneratorService")
    @patch("aiecommerce.management.commands.test_ai_content.AIContentOrchestrator")
    def test_handle_error(self, mock_orchestrator_class, mock_desc_gen, mock_title_gen, capsys):
        # Setup
        product = ProductMasterFactory(code="TEST-PROD-05")
        mock_orchestrator = mock_orchestrator_class.return_value
        mock_orchestrator.process_product_content.return_value = {"error": "Something went wrong"}

        # Execute
        call_command("test_ai_content", "TEST-PROD-05")

        # Verify
        captured = capsys.readouterr()
        assert "Content generation was skipped. Use --force to override." in captured.out
        mock_orchestrator.process_product_content.assert_called_once_with(product, dry_run=True, force_refresh=False)

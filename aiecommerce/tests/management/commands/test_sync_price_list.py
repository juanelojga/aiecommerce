import io
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from aiecommerce.services.price_list_impl.exceptions import IngestionError


@override_settings(PRICE_LIST_BASE_URL="")
def test_missing_base_url_raises_command_error():
    with pytest.raises(CommandError) as exc:
        call_command("sync_price_list")
    assert "PRICE_LIST_BASE_URL is not set" in str(exc.value)


@override_settings(PRICE_LIST_BASE_URL="https://example.com/base")
def test_success_path_uses_settings_base_url_and_reports_count():
    fake_result = {"status": "success", "count": 10}

    # Patch the symbol where it is used (inside the management command module)
    with patch("aiecommerce.management.commands.sync_price_list.PriceListIngestionUseCase") as MockUseCase:
        instance = MockUseCase.return_value
        instance.execute.return_value = fake_result

        out = io.StringIO()
        call_command("sync_price_list", stdout=out)
        output = out.getvalue()

        # Ensure the use case was created and executed with the correct args
        instance.execute.assert_called_once_with("https://example.com/base", dry_run=False)

        assert "Starting price list ingestion from: https://example.com/base" in output
        assert "Successfully ingested 10 records." in output


@override_settings(PRICE_LIST_BASE_URL="https://example.com/base")
def test_dry_run_outputs_preview_and_count_json():
    preview = [{"sku": "A1"}, {"sku": "B2"}]
    fake_result = {"status": "dry_run", "count": 7, "preview": preview}

    # Patch the symbol where it is used (inside the management command module)
    with patch("aiecommerce.management.commands.sync_price_list.PriceListIngestionUseCase") as MockUseCase:
        instance = MockUseCase.return_value
        instance.execute.return_value = fake_result

        out = io.StringIO()
        call_command("sync_price_list", "--dry-run", stdout=out)
        output = out.getvalue()

        instance.execute.assert_called_once_with("https://example.com/base", dry_run=True)

        assert "-- DRY RUN --" in output
        assert "Total items that would be ingested: 7" in output
        assert "Showing first 5 items (preview):" in output
        # The preview should be JSON-dumped
        assert '\n  {\n    "sku": "A1"\n  },\n  {\n    "sku": "B2"\n  }\n]' in output or '"sku": "A1"' in output
        assert "Dry run complete. No database changes were made." in output


def test_cli_argument_base_url_overrides_settings():
    # Settings has a different URL, but CLI arg should win
    with override_settings(PRICE_LIST_BASE_URL="https://settings-url.invalid"):
        # Patch the symbol where it is used (inside the management command module)
        with patch("aiecommerce.management.commands.sync_price_list.PriceListIngestionUseCase") as MockUseCase:
            instance = MockUseCase.return_value
            instance.execute.return_value = {"status": "success", "count": 1}

            out = io.StringIO()
            call_command(
                "sync_price_list",
                "--base-url",
                "https://cli-url.example/base",
                stdout=out,
            )

            instance.execute.assert_called_once_with("https://cli-url.example/base", dry_run=False)


@override_settings(PRICE_LIST_BASE_URL="https://example.com/base")
def test_ingestion_error_is_wrapped_into_command_error():
    # Patch the symbol where it is used (inside the management command module)
    with patch("aiecommerce.management.commands.sync_price_list.PriceListIngestionUseCase") as MockUseCase:
        instance = MockUseCase.return_value
        instance.execute.side_effect = IngestionError("failed to parse")

        with pytest.raises(CommandError) as exc:
            call_command("sync_price_list")
        assert "An error occurred during ingestion: failed to parse" in str(exc.value)


@override_settings(PRICE_LIST_BASE_URL="https://example.com/base")
def test_unexpected_exception_is_wrapped_into_command_error():
    # Patch the symbol where it is used (inside the management command module)
    with patch("aiecommerce.management.commands.sync_price_list.PriceListIngestionUseCase") as MockUseCase:
        instance = MockUseCase.return_value
        instance.execute.side_effect = RuntimeError("boom")

        with pytest.raises(CommandError) as exc:
            call_command("sync_price_list")
        assert "An unexpected error occurred: boom" in str(exc.value)

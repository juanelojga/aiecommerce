from unittest.mock import MagicMock, patch

from aiecommerce.services.telegram_impl.formatters import (
    format_batch_publish_stats,
    format_incorrect_ml_images_stats,
    format_remediation_stats,
)


class TestFormatIncorrectMlImagesStats:
    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_dry_run_header_and_would_refresh_line(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 5, "skipped": 0}, dry_run=True)
        assert "ℹ️" in result
        assert "Dry Run" in result
        assert "Would refresh: 5" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_queued_header_when_queued_nonzero(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 3, "skipped": 0}, dry_run=False)
        assert "🖼" in result
        assert "Chains queued: 3" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_nothing_to_do_header_when_queued_zero(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 0, "skipped": 0}, dry_run=False)
        assert "✅" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_skipped_line_shown_when_nonzero(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 1, "skipped": 2}, dry_run=False)
        assert "Skipped" in result
        assert "2" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_skipped_line_hidden_when_zero(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 1, "skipped": 0}, dry_run=False)
        assert "Skipped" not in result

    def test_empty_stats_defaults_to_zero_without_error(self) -> None:
        result = format_incorrect_ml_images_stats({})
        assert "Chains queued: 0" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_timestamp_present_in_output(self, mock_datetime: MagicMock) -> None:
        mock_datetime.now.return_value.strftime.return_value = "2026-04-16 10:00:00"
        result = format_incorrect_ml_images_stats({"queued": 1, "skipped": 0})
        assert "2026-04-16 10:00:00" in result


class TestFormatRemediationStats:
    def test_includes_all_counts(self) -> None:
        stats = {"total": 90, "gtin": 53, "price": 14, "other": 23, "failed": 0}
        result = format_remediation_stats(stats)
        assert "ML Listing Error Remediation" in result
        assert "Total processed: 90" in result
        assert "GTIN cleared + listing removed: 53" in result
        assert "Price errors removed: 14" in result
        assert "Other errors removed: 23" in result
        assert "Failed" not in result

    def test_header_switches_to_warning_when_failures(self) -> None:
        stats = {"total": 5, "gtin": 2, "price": 1, "other": 1, "failed": 1}
        result = format_remediation_stats(stats)
        assert "⚠️" in result
        assert "Failed: 1" in result

    def test_empty_stats_defaults(self) -> None:
        assert "Total processed: 0" in format_remediation_stats({})


class TestFormatBatchPublishStats:
    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_success_only(self, mock_datetime: MagicMock) -> None:
        """Test formatting with only successful publications."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 25, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=["MLB123", "MLB456"])

        assert "✅ Batch Publishing Complete" in result
        assert "2026-02-08 22:15:00" in result
        assert "PRODUCTION" in result
        assert "✅ Success: 25" in result
        assert "❌ Errors" not in result
        assert "⏭️ Skipped" not in result
        assert "<code>MLB123</code>" in result
        assert "<code>MLB456</code>" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_with_errors(self, mock_datetime: MagicMock) -> None:
        """Test formatting with errors present."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 18, "errors": 7, "skipped": 3}
        result = format_batch_publish_stats(stats, "SANDBOX", dry_run=False)

        assert "⚠️ Batch Publishing Complete (with errors)" in result
        assert "SANDBOX" in result
        assert "✅ Success: 18" in result
        assert "❌ Errors: 7" in result
        assert "⏭️ Skipped: 3" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_dry_run(self, mock_datetime: MagicMock) -> None:
        """Test formatting for dry run mode."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 30, "errors": 0, "skipped": 2}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=True)

        assert "ℹ️ Batch Publishing Dry Run" in result
        assert "(Dry Run - No actual publishing)" in result
        assert "✅ Would Publish: 30" in result
        assert "⏭️ Would Skip: 2" in result
        assert "No actual products were published" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_with_many_product_ids(self, mock_datetime: MagicMock) -> None:
        """Test that only first 20 product IDs are shown."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        product_ids = [f"MLB{i:09d}" for i in range(1, 51)]  # 50 product IDs
        stats = {"success": 50, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=product_ids)

        assert "<code>MLB000000001</code>" in result
        assert "<code>MLB000000020</code>" in result
        assert "<code>MLB000000021</code>" not in result
        assert "...and 30 more" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_with_exactly_20_product_ids(self, mock_datetime: MagicMock) -> None:
        """Test that with exactly 20 IDs, no 'more' message is shown."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        product_ids = [f"MLB{i:09d}" for i in range(1, 21)]  # Exactly 20 IDs
        stats = {"success": 20, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=product_ids)

        assert "<code>MLB000000020</code>" in result
        assert "...and" not in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_no_product_ids(self, mock_datetime: MagicMock) -> None:
        """Test formatting when no product IDs are provided."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 10, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=None)

        assert "✅ Success: 10" in result
        assert "Published IDs:" not in result
        assert "<code>" not in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_empty_product_ids_list(self, mock_datetime: MagicMock) -> None:
        """Test formatting with empty product IDs list."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 0, "errors": 5, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=[])

        assert "❌ Errors: 5" in result
        assert "Published IDs:" not in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_skipped_only_shown_when_nonzero(self, mock_datetime: MagicMock) -> None:
        """Test that skipped count only shown when > 0."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 10, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False)

        assert "⏭️ Skipped" not in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_html_tags(self, mock_datetime: MagicMock) -> None:
        """Test that HTML tags are properly used."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 5, "errors": 0, "skipped": 0}
        result = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False, product_ids=["MLB123"])

        assert "<b>" in result
        assert "</b>" in result
        assert "<code>MLB123</code>" in result

    @patch("aiecommerce.services.telegram_impl.formatters.datetime")
    def test_format_production_vs_sandbox(self, mock_datetime: MagicMock) -> None:
        """Test that mode is correctly displayed."""
        mock_datetime.now.return_value.strftime.return_value = "2026-02-08 22:15:00"

        stats = {"success": 5, "errors": 0, "skipped": 0}

        result_prod = format_batch_publish_stats(stats, "PRODUCTION", dry_run=False)
        result_sandbox = format_batch_publish_stats(stats, "SANDBOX", dry_run=False)

        assert "<b>Mode:</b> PRODUCTION" in result_prod
        assert "<b>Mode:</b> SANDBOX" in result_sandbox

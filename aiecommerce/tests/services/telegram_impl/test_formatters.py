from unittest.mock import MagicMock, patch

from aiecommerce.services.telegram_impl.formatters import format_batch_publish_stats


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

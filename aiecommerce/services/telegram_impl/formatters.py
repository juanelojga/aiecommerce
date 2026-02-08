from datetime import datetime


def format_batch_publish_stats(
    stats: dict[str, int],
    mode: str,
    dry_run: bool = False,
    product_ids: list[str] | None = None,
) -> str:
    """
    Format batch publishing statistics into a readable Telegram message.

    Args:
        stats: Dictionary with 'success', 'errors', and 'skipped' counts
        mode: Either "PRODUCTION" or "SANDBOX"
        dry_run: Whether this was a dry run
        product_ids: List of successfully published product IDs

    Returns:
        HTML-formatted string ready for Telegram
    """
    success_count = stats.get("success", 0)
    error_count = stats.get("errors", 0)
    skipped_count = stats.get("skipped", 0)

    # Determine header emoji based on results
    if dry_run:
        header_emoji = "ℹ️"
        header_text = "Batch Publishing Dry Run"
    elif error_count > 0:
        header_emoji = "⚠️"
        header_text = "Batch Publishing Complete (with errors)"
    else:
        header_emoji = "✅"
        header_text = "Batch Publishing Complete"

    # Build message
    lines = [
        f"<b>{header_emoji} {header_text}</b>",
        "",
        f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"<b>Mode:</b> {mode}",
    ]

    if dry_run:
        lines.append("<i>(Dry Run - No actual publishing)</i>")

    lines.append("")
    lines.append("<b>Results:</b>")

    # Add stats with emojis
    if dry_run:
        lines.append(f"✅ Would Publish: {success_count}")
        if skipped_count > 0:
            lines.append(f"⏭️ Would Skip: {skipped_count}")
    else:
        if success_count > 0:
            lines.append(f"✅ Success: {success_count}")
        if error_count > 0:
            lines.append(f"❌ Errors: {error_count}")
        if skipped_count > 0:
            lines.append(f"⏭️ Skipped: {skipped_count}")

    # Add product IDs if available
    if product_ids and len(product_ids) > 0 and not dry_run:
        lines.append("")
        lines.append("<b>Published IDs:</b>")

        # Show up to 20 IDs
        display_ids = product_ids[:20]
        for product_id in display_ids:
            lines.append(f"<code>{product_id}</code>")

        # Show count of remaining IDs
        remaining = len(product_ids) - 20
        if remaining > 0:
            lines.append(f"<i>...and {remaining} more</i>")

    elif dry_run:
        lines.append("")
        lines.append("<i>No actual products were published.</i>")

    return "\n".join(lines)

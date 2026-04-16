from datetime import datetime


def format_remediation_stats(stats: dict[str, int]) -> str:
    """Format ML error-remediation run stats into an HTML Telegram message."""
    total = stats.get("total", 0)
    gtin = stats.get("gtin", 0)
    price = stats.get("price", 0)
    other = stats.get("other", 0)
    failed = stats.get("failed", 0)

    header_emoji = "⚠️" if failed > 0 else "🧹"
    lines = [
        f"<b>{header_emoji} ML Listing Error Remediation</b>",
        "",
        f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "<b>Results:</b>",
        f"📦 Total processed: {total}",
        f"🔖 GTIN cleared + listing removed: {gtin}",
        f"💲 Price errors removed: {price}",
        f"🗑 Other errors removed: {other}",
    ]
    if failed > 0:
        lines.append(f"❌ Failed: {failed}")
    return "\n".join(lines)


def format_incorrect_ml_images_stats(stats: dict[str, int], dry_run: bool = False) -> str:
    """Format the refresh-incorrect-ML-images run stats into an HTML Telegram message."""
    queued = stats.get("queued", 0)
    skipped = stats.get("skipped", 0)

    if dry_run:
        header = "ℹ️ <b>ML Image Refresh (Dry Run)</b>"
    elif queued > 0:
        header = "🖼 <b>ML Image Refresh Queued</b>"
    else:
        header = "✅ <b>ML Image Refresh — Nothing to do</b>"

    lines = [
        header,
        "",
        f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "<b>Results:</b>",
    ]
    if dry_run:
        lines.append(f"🔍 Would refresh: {queued}")
    else:
        lines.append(f"🔄 Chains queued: {queued}")
    if skipped > 0:
        lines.append(f"⏭️ Skipped (no product code): {skipped}")
    return "\n".join(lines)


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

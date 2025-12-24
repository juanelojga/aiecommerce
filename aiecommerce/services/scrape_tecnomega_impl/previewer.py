from typing import Any, Sequence

from django.core.management.base import BaseCommand


class ProductPreviewer:
    """Handles the previewing of scraped products during a dry run."""

    def __init__(self, command: BaseCommand):
        self.command = command

    def show_preview(self, category: str, items: Sequence[Any], limit: int = 5) -> None:
        """Prints a detailed preview for a list of items."""
        if not items:
            return

        self.command.stdout.write(
            self.command.style.WARNING(f"\n--- [DRY RUN] Detailed Preview (First {limit} items for '{category}') ---")
        )

        for i, item in enumerate(items[:limit], 1):
            self.command.stdout.write(self.command.style.SUCCESS(f"Item #{i}:"))

            data = item if isinstance(item, dict) else vars(item)

            if isinstance(data, dict):
                for key, value in data.items():
                    if not key.startswith("_"):
                        self.command.stdout.write(f"  {key}: {value}")
            else:
                self.command.stdout.write(f"  {item}")

            self.command.stdout.write("")

        self.command.stdout.write(self.command.style.WARNING("----------------------------------------------------------\n"))

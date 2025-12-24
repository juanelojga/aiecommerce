from typing import List

from django.core.management.base import BaseCommand


class ScrapeReporter:
    """Handles reporting for the scrape command."""

    def __init__(self, command: BaseCommand):
        self.command = command
        self.total_scraped_count = 0
        self.failed_categories: List[str] = []

    def track_success(self, category: str, count: int) -> None:
        """Tracks a successfully processed category."""
        self.command.stdout.write(self.command.style.SUCCESS(f"Successfully processed {count} items for category '{category}'."))
        self.total_scraped_count += count

    def track_failure(self, category: str, error: Exception) -> None:
        """Tracks a failed category."""
        self.command.stderr.write(self.command.style.ERROR(f"Failed to process category '{category}': {error}"))
        self.failed_categories.append(category)

    def print_summary(self, dry_run: bool) -> None:
        """Prints the final execution summary."""
        self.command.stdout.write(self.command.style.NOTICE("--------------------\n"))
        self.command.stdout.write(self.command.style.NOTICE("Scrape process finished."))
        self.command.stdout.write(f"Total items processed: {self.total_scraped_count}")

        if self.failed_categories:
            self.command.stderr.write(
                self.command.style.ERROR(f"Completed with errors. Failed categories: {', '.join(self.failed_categories)}")
            )
        else:
            self.command.stdout.write(self.command.style.SUCCESS("All categories processed successfully."))

        if dry_run:
            self.command.stdout.write(self.command.style.WARNING("Dry run complete. No database changes were made."))

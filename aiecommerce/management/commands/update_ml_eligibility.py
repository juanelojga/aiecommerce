from typing import Any

from django.core.management.base import BaseCommand

from aiecommerce.services.update_ml_eligibility_impl.orchestrator import UpdateMlEligibilityCandidateOrchestrator
from aiecommerce.services.update_ml_eligibility_impl.selector import UpdateMlEligibilityCandidateSelector


class Command(BaseCommand):
    help = "Updates the 'is_for_mercadolibre' flag on all ProductMaster instances."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--force", action="store_true", help="Includes products that doesn't have stock")
        parser.add_argument("--dry-run", action="store_true", help="Show which products would be processed, but do not enqueue any tasks.")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between products")

    def handle(self, *args: Any, **options: Any) -> None:
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        # Initialize the selector and the main batch orchestrator
        selector = UpdateMlEligibilityCandidateSelector()
        orchestrator = UpdateMlEligibilityCandidateOrchestrator(selector)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        if stats["total"] == 0:
            self.stdout.write(self.style.WARNING("No products found."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
            self.stdout.write(self.style.SUCCESS(f"Enqueued {stats['processed']}/{stats['total']} tasks"))

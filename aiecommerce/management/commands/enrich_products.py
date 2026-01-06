import json
import time
from typing import Any

from django.core.management.base import BaseCommand

from aiecommerce.services.enrichment_impl.orchestrator import EnrichmentOrchestrator
from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector
from aiecommerce.services.enrichment_impl.service import (
    ConfigurationError,
    ProductEnrichmentService,
)


class Command(BaseCommand):
    help = "Enriches ProductMaster records with structured specs using AI"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess products that already have specs",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="API calls are performed, but no data is saved to the database.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="Delay in seconds between processing each product.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        try:
            self.stdout.write(self.style.HTTP_INFO("Initializing services..."))

            service = ProductEnrichmentService()
            selector = EnrichmentCandidateSelector()
            orchestrator = EnrichmentOrchestrator(service)

        except ConfigurationError as e:
            self.stdout.write(self.style.ERROR(f"Configuration Error: {e}"))
            return

        products_queryset = selector.get_queryset(force, dry_run)
        total_count = products_queryset.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No products need enrichment."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_count} products to enrich."))

        processed_count = 0
        success_count = 0

        for product in products_queryset.iterator(chunk_size=100):
            desc_preview = (product.description or "")[:60]
            self.stdout.write(f"[{product.id}] {desc_preview}...")

            success, specs = orchestrator.process_product(product, dry_run)

            if success and specs:
                success_count += 1
                cat_type = specs.get("category_type", "UNKNOWN")
                self.stdout.write(self.style.SUCCESS(f"   -> Enriched as: {cat_type}"))
                if dry_run:
                    formatted_json = json.dumps(specs, indent=2)
                    self.stdout.write(self.style.MIGRATE_HEADING(formatted_json))
            else:
                self.stdout.write(self.style.ERROR("   -> Failed to extract specs"))

            processed_count += 1
            time.sleep(delay)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {processed_count} products ({success_count} successful)."))

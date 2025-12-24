import json
import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q, QuerySet

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl import ProductEnrichmentService
from aiecommerce.services.enrichment_impl.exceptions import EnrichmentError
from aiecommerce.services.enrichment_impl.service import ConfigurationError


class Command(BaseCommand):
    help = "Enriches ProductMaster records with structured specs using AI"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--category",
            type=str,
            help="Filter by specific category (case-insensitive)",
        )
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

    def _build_queryset(self, **options: Any) -> QuerySet[ProductMaster, ProductMaster]:
        """Encapsulates all filtering logic for the command."""
        category_filter = options["category"]
        force = options["force"]
        dry_run = options["dry_run"]

        query = ProductMaster.objects.filter(is_active=True)

        if category_filter:
            query = query.filter(category__icontains=category_filter)

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))
            self.stdout.write("Fetching first 3 products for testing...")
            return query.order_by("id")[:3]

        if not force:
            query = query.filter(Q(specs__isnull=True) | Q(specs={}))

        return query.order_by("id")

    def _enrich_single_product(self, product: ProductMaster, service: ProductEnrichmentService, dry_run: bool) -> bool:
        """Handles the invocation, persistence, and user feedback for a single item."""
        desc_preview = (product.description or "")[:60]
        self.stdout.write(f"[{product.id}] {desc_preview}...")
        try:
            # 1. CALL SERVICE
            extracted_specs = service.enrich_product_specs(product)

            # 2. HANDLE RESPONSE
            if not extracted_specs:
                self.stdout.write(self.style.ERROR("   -> Failed to extract specs (no data returned)"))
                return False

            product.specs = extracted_specs.model_dump(exclude_none=True)
            cat_type = product.specs.get("category_type", "UNKNOWN")
            self.stdout.write(self.style.SUCCESS(f"   -> Enriched as: {cat_type}"))

            if dry_run:
                formatted_json = json.dumps(product.specs, indent=2)
                self.stdout.write(self.style.MIGRATE_HEADING(formatted_json))
            else:
                # 3. SAVE (only if not a dry run)
                product.save(update_fields=["specs"])

            return True

        except EnrichmentError as e:
            self.stdout.write(self.style.ERROR(f"   -> Service Error: {e}"))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   -> An unexpected error occurred: {e}"))
            return False

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]
        delay = options["delay"]

        try:
            self.stdout.write(self.style.HTTP_INFO("Initializing Enrichment Service..."))
            service = ProductEnrichmentService()
        except ConfigurationError as e:
            self.stdout.write(self.style.ERROR(f"Configuration Error: {e}"))
            return

        products_queryset = self._build_queryset(**options)

        # Acknowledging .count() can be expensive, but useful for user feedback.
        total_count = products_queryset.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No products need enrichment."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_count} products to enrich."))

        # --- EXECUTION LOOP ---
        processed_count = 0
        success_count = 0

        for product in products_queryset.iterator(chunk_size=10):
            if self._enrich_single_product(product, service, dry_run):
                success_count += 1
            processed_count += 1
            time.sleep(delay)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {processed_count} products ({success_count} successful)."))

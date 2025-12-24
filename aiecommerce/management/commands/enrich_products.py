import json
import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl import ProductEnrichmentService
from aiecommerce.services.enrichment_impl.service import ConfigurationError


class Command(BaseCommand):
    help = "Enriches ProductMaster records with structured specs using AI"

    def add_arguments(self, parser):
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
            help="Test mode: Processes 3 products, prints results, DOES NOT save to DB.",
        )

    def handle(self, *args, **options):
        category_filter = options["category"]
        force = options["force"]
        dry_run = options["dry_run"]

        try:
            self.stdout.write(self.style.HTTP_INFO("Initializing Enrichment Service..."))
            service = ProductEnrichmentService()
        except ConfigurationError as e:
            self.stdout.write(self.style.ERROR(f"Configuration Error: {e}"))
            return

        # --- QUERY CONSTRUCTION ---
        query = ProductMaster.objects.filter(is_active=True)

        if category_filter:
            query = query.filter(category__icontains=category_filter)

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))
            self.stdout.write("Fetching first 3 products for testing (Database will NOT be modified)...")
            products_queryset = query.order_by("id")[:3]
        else:
            if not force:
                query = query.filter(Q(specs__isnull=True) | Q(specs={}))

            products_queryset = query.order_by("id")
            total_count = products_queryset.count()

            if total_count == 0:
                self.stdout.write(self.style.SUCCESS("No products need enrichment."))
                return

            self.stdout.write(self.style.SUCCESS(f"Found {total_count} products to enrich."))

        # --- EXECUTION LOOP ---
        processed_count = 0
        success_count = 0

        for product in products_queryset.iterator(chunk_size=10):
            self.stdout.write(f"[{product.id}] {product.description[:60]}...")

            # 1. CALL SERVICE
            extracted_specs = service.enrich_product_specs(product)

            # 2. HANDLE RESPONSE
            if extracted_specs:
                success_count += 1
                # Convert Pydantic model to a dict for storing in JSONField
                product.specs = extracted_specs.model_dump(exclude_none=True)
                cat_type = product.specs.get("category_type", "UNKNOWN")
                self.stdout.write(self.style.SUCCESS(f"   -> Enriched as: {cat_type}"))

                if dry_run:
                    # Print the full JSON for inspection
                    formatted_json = json.dumps(product.specs, indent=2)
                    self.stdout.write(self.style.MIGRATE_HEADING(formatted_json))
                else:
                    # 3. SAVE (only if not a dry run)
                    product.save(update_fields=["specs"])

            else:
                self.stdout.write(self.style.ERROR("   -> Failed to extract specs"))

            processed_count += 1
            time.sleep(0.5)  # Rate limiting

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {processed_count} products ({success_count} successful)."))

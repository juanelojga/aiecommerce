import json
import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from aiecommerce.models import ProductMaster
from aiecommerce.services.enrichment_impl import ProductEnrichmentService


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

        self.stdout.write(self.style.HTTP_INFO("Initializing Enrichment Service..."))
        service = ProductEnrichmentService()

        # --- QUERY CONSTRUCTION ---
        query = ProductMaster.objects.filter(is_active=True)

        if category_filter:
            query = query.filter(category__icontains=category_filter)

        # Logic:
        # If dry-run: We grab the first 3 products we find (doesn't matter if they have specs).
        # If normal run: We grab ALL products missing specs (unless --force is used).

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))
            self.stdout.write("Fetching first 3 products for testing (Database will NOT be modified)...")
            # Just grab 3 random active products
            products_queryset = query.order_by("id")[:3]

        else:
            # Normal Mode
            if not force:
                # Filter for empty specs (None or {})
                query = query.filter(Q(specs__isnull=True) | Q(specs={}))

            products_queryset = query.order_by("id")
            total_count = products_queryset.count()

            if total_count == 0:
                self.stdout.write(self.style.SUCCESS("No products need enrichment."))
                return

            self.stdout.write(self.style.SUCCESS(f"Found {total_count} products to enrich."))

        # --- EXECUTION LOOP ---
        # We use iterator() with chunk_size=10 to handle memory efficiently ("10 by 10")
        processed_count = 0

        for product in products_queryset.iterator(chunk_size=10):
            self.stdout.write(f"[{product.id}] {product.description[:60]}...")

            # CALL SERVICE
            # pass save=False if dry_run
            is_success = service.enrich_product_specs(product, save=(not dry_run))

            if is_success:
                cat_type = product.specs.get("category_type", "UNKNOWN")
                self.stdout.write(self.style.SUCCESS(f"   -> Enriched as: {cat_type}"))

                if dry_run:
                    # Print the full JSON in dry run so you can inspect it
                    formatted_json = json.dumps(product.specs, indent=2)
                    self.stdout.write(self.style.MIGRATE_HEADING(formatted_json))
            else:
                self.stdout.write(self.style.ERROR("   -> Failed to extract specs"))

            processed_count += 1

            # Simple rate limiting (2 products per second)
            time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {processed_count} products."))

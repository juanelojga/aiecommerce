"""Django management command to enrich products with GTIN codes."""

from django.core.management.base import BaseCommand

from aiecommerce.services.gtin_enrichment_impl import (
    GTINEnrichmentCandidateSelector,
    GTINSearchService,
)


class Command(BaseCommand):
    """Management command to enrich products with GTIN codes using LLM search."""

    help = "Enriches ProductMaster records with GTIN codes using AI-powered search"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--limit",
            type=int,
            default=15,
            help="Number of products to process (default: 15)",
        )

    def handle(self, *args, **options):
        """Execute the GTIN enrichment command."""
        limit = options["limit"]

        self.stdout.write(self.style.NOTICE(f"Starting GTIN enrichment for up to {limit} products..."))

        # Initialize services
        selector = GTINEnrichmentCandidateSelector()
        gtin_service = GTINSearchService()

        # Fetch products that need GTIN enrichment
        products = selector.get_batch(limit=limit)
        product_count = products.count()

        if product_count == 0:
            self.stdout.write(self.style.WARNING("No products found that need GTIN enrichment."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {product_count} product(s) to process.\n"))

        # Track statistics
        found_count = 0
        not_found_count = 0
        error_count = 0

        # Process each product
        for index, product in enumerate(products, start=1):
            self.stdout.write(f"[{index}/{product_count}] Processing product: {product.code}")

            try:
                # Search for GTIN
                gtin, strategy = gtin_service.search_gtin(product)

                if gtin:
                    # Update product with found GTIN
                    product.gtin = gtin
                    product.gtin_source = strategy
                    product.save()
                    found_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ GTIN found: {gtin} (strategy: {strategy})"))
                else:
                    # Mark as NOT_FOUND
                    product.gtin_source = strategy  # Should be "NOT_FOUND"
                    product.save()
                    not_found_count += 1
                    self.stdout.write(self.style.WARNING(f"  ✗ GTIN not found (marked as {strategy})"))

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing product {product.code}: {e}"))

        # Display summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("GTIN Enrichment Complete"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total processed:  {product_count}")
        self.stdout.write(self.style.SUCCESS(f"GTIN found:       {found_count}"))
        self.stdout.write(self.style.WARNING(f"GTIN not found:   {not_found_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors:           {error_count}"))
        self.stdout.write("=" * 60)

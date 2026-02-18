"""Management command to enrich ProductMaster records with GTIN codes.

This command finds products that are missing a GTIN and attempts to locate a
valid GTIN code using an external search service driven by an LLM (via
OpenRouter/OpenAI). When a GTIN is discovered the product is updated with the
code and the discovery strategy is recorded on the model.

Requirements:
- `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` must be configured in Django
    settings.
- Uses `GTINEnrichmentCandidateSelector` to select candidate products and
    `GTINSearchService` to perform the LLM-backed search.

Usage example:
        python manage.py enrich_products_gtin --limit 50
"""

import instructor
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI

from aiecommerce.services.gtin_enrichment_impl import (
    GTINEnrichmentCandidateSelector,
    GTINSearchService,
)


class Command(BaseCommand):
    """Orchestrates GTIN enrichment using a candidate selector and search service.

    The command selects a batch of candidate products, initializes the LLM
    client (via OpenRouter) and `GTINSearchService`, runs searches for each
    product, and persists any discovered GTINs. Progress and a final summary
    are printed to stdout.
    """

    help = "Enriches ProductMaster records with GTIN codes using AI-powered search"

    def add_arguments(self, parser):
        """Configure command-line arguments used by this management command."""
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of products to process (default: 10)",
        )

    def handle(self, *args, **options):
        """Run the enrichment workflow.

        Steps performed:
        1. Validate required settings (API key and base URL).
        2. Initialize candidate selector and search service client.
        3. Iterate over candidate products, search for GTINs, and update the DB.
        4. Print a summary with counts for found, not-found and errors.
        """
        limit = options["limit"]

        self.stdout.write(self.style.NOTICE(f"Starting GTIN enrichment for up to {limit} products..."))

        # Prepare the candidate selector used to fetch products needing GTINs
        selector = GTINEnrichmentCandidateSelector()

        # Read OpenRouter settings required to construct the OpenAI client
        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL

        if not api_key or not base_url:
            raise CommandError("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be configured in settings")

        # Wrap OpenAI client with `instructor` helper configured to return JSON
        openai_client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url),
            mode=instructor.Mode.JSON,
        )

        # Service responsible for running searches and selecting GTIN candidates
        gtin_service = GTINSearchService(client=openai_client)

        # Fetch products that need GTIN enrichment
        products = selector.get_batch(limit=limit)
        product_count = products.count()

        if product_count == 0:
            self.stdout.write(self.style.WARNING("No products found that need GTIN enrichment."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {product_count} product(s) to process.\n"))

        # Counters for run statistics reported at the end
        found_count = 0
        not_found_count = 0
        error_count = 0

        # Process each product
        for index, product in enumerate(products, start=1):
            self.stdout.write(f"[{index}/{product_count}] Processing product: {product.code}")

            try:
                # Ask the search service to look for a GTIN for the product
                gtin, strategy = gtin_service.search_gtin(product)

                if gtin:
                    # Persist discovered GTIN and the strategy used to find it
                    product.gtin = gtin
                    product.gtin_source = strategy
                    product.save()
                    found_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ GTIN found: {gtin} (strategy: {strategy})"))
                else:
                    # Mark product as explicitly not found (strategy typically "NOT_FOUND")
                    product.gtin_source = strategy
                    product.save()
                    not_found_count += 1
                    self.stdout.write(self.style.WARNING(f"  ✗ GTIN not found (marked as {strategy})"))

            except Exception as e:
                # Catch unexpected errors per-product but continue processing
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

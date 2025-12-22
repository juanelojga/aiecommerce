import logging
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aiecommerce.services.scrape_tecnomega_impl.fetcher import HtmlFetcher
from aiecommerce.services.scrape_tecnomega_impl.mapper import ProductMapper
from aiecommerce.services.scrape_tecnomega_impl.parser import HtmlParser
from aiecommerce.services.scrape_tecnomega_impl.persister import ProductPersister

# Configure logger for the command
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrapes product data from TECNOMEGA based on predefined categories."

    # Categories to be scraped. The string is used as the 'search' query parameter.
    CATEGORIES_TO_SCRAPE = [
        "audifonos",
        "teclados",
        "monitores",
        "impresoras",
        "laptops",
        "proyectores",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving any data to the database.",
        )

        parser.add_argument(
            "--base-url",
            type=str,
            help="Optional override for the TECNOMEGA base URL.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        base_url = options.get("base_url") or getattr(settings, "TECNOMEGA_BASE_URL", None)

        if not base_url:
            raise CommandError("TECNOMEGA_BASE_URL is not set. Define it in your settings or use --base-url.")

        if dry_run:
            self.stdout.write(self.style.WARNING("-- DRY RUN MODE --"))

        self.stdout.write(self.style.NOTICE(f"Starting scrape process for {base_url}"))

        scrape_session_id = str(uuid.uuid4())
        self.stdout.write(self.style.NOTICE(f"Scrape Session ID: {scrape_session_id}"))

        # 1. Initialize Services
        try:
            fetcher = HtmlFetcher(base_url=base_url)
            parser = HtmlParser()
            mapper = ProductMapper()
            persister = ProductPersister()
        except Exception as e:
            raise CommandError(f"Failed to initialize services: {e}")

        total_scraped_count = 0
        failed_categories = []

        # 2. Iterate, Fetch, Parse, Map, Persist for each category
        for category in self.CATEGORIES_TO_SCRAPE:
            self.stdout.write(self.style.HTTP_INFO(f"Processing category: '{category}'..."))
            try:
                # Execute the flow: Fetch -> Parse -> Map -> Persist
                html_content = fetcher.fetch_html(params={"search": category})
                raw_products = parser.parse(html_content)
                if not raw_products:
                    self.stdout.write(self.style.WARNING(f"No products found for category '{category}'."))
                    continue

                product_models = mapper.map_to_models(
                    raw_products=raw_products,
                    scrape_session_id=scrape_session_id,
                    search_term=category,
                )
                persister.persist(products=product_models, dry_run=dry_run)

                total_scraped_count += len(product_models)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully processed {len(product_models)} items for category '{category}'.")
                )

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to process category '{category}': {e}"))
                logger.error(f"Error processing category {category}", exc_info=True)
                failed_categories.append(category)
                # Continue to the next category as per requirements

        # 3. Final Report
        self.stdout.write(self.style.NOTICE("--------------------"))
        self.stdout.write(self.style.NOTICE("Scrape process finished."))
        self.stdout.write(f"Total items processed: {total_scraped_count}")

        if failed_categories:
            self.stderr.write(
                self.style.ERROR(f"Completed with errors. Failed categories: {', '.join(failed_categories)}")
            )
        else:
            self.stdout.write(self.style.SUCCESS("All categories processed successfully."))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete. No database changes were made."))

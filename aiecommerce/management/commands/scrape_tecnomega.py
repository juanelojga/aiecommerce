import logging
import uuid
from typing import Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aiecommerce.services.scrape_tecnomega_impl.fetcher import HtmlFetcher
from aiecommerce.services.scrape_tecnomega_impl.mapper import ProductMapper
from aiecommerce.services.scrape_tecnomega_impl.parser import HtmlParser
from aiecommerce.services.scrape_tecnomega_impl.persister import ProductPersister

# Configure logger for the command
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrapes product data from TECNOMEGA based on provided categories."

    def add_arguments(self, parser):
        # Change: Categories are now positional arguments (nargs='*')
        # If none are provided, it defaults to ["notebook"]
        parser.add_argument(
            "--categories",
            nargs="*",
            default=["notebook"],
            help="List of categories to scrape. Defaults to 'notebook' if not provided.",
        )

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
        categories = options["categories"]
        base_url = options.get("base_url") or getattr(settings, "STOCK_LIST_BASE_URL", None)

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

        # 2. Iterate through provided categories (or default)
        for category in categories:
            self.stdout.write(self.style.HTTP_INFO(f"Processing category: '{category}'..."))

            success, count = self._process_category(
                category=category,
                scrape_session_id=scrape_session_id,
                dry_run=dry_run,
                fetcher=fetcher,
                parser=parser,
                mapper=mapper,
                persister=persister,
            )

            if success:
                total_scraped_count += count
            else:
                failed_categories.append(category)

        # 3. Final Report
        self._print_summary(total_scraped_count, failed_categories, dry_run)

    def _process_category(
        self,
        category: str,
        scrape_session_id: str,
        dry_run: bool,
        fetcher: HtmlFetcher,
        parser: HtmlParser,
        mapper: ProductMapper,
        persister: ProductPersister,
    ) -> Tuple[bool, int]:
        """
        Helper method to handle the Fetch -> Parse -> Map -> Persist flow for a single category.
        Returns a tuple: (success: bool, count: int)
        """
        try:
            html_content = fetcher.fetch_html(params={"buscar": category})
            raw_products = parser.parse(html_content)

            if not raw_products:
                self.stdout.write(self.style.WARNING(f"No products found for category '{category}'."))
                return True, 0

            product_models = mapper.map_to_models(
                raw_products=raw_products,
                scrape_session_id=scrape_session_id,
                search_term=category,
            )

            # --- NEW SECTION: PRINT PREVIEW IF DRY RUN ---
            if dry_run and product_models:
                self.stdout.write(self.style.WARNING(f"\n--- [DRY RUN] Preview (First 5 items for '{category}') ---"))
                for i, item in enumerate(product_models[:5], 1):
                    # Uses the __str__ representation of your model/object
                    self.stdout.write(f"{i}. {item}")
                self.stdout.write(self.style.WARNING("----------------------------------------------------------\n"))
            # ---------------------------------------------

            persister.persist(products=product_models, dry_run=dry_run)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed {len(product_models)} items for category '{category}'.")
            )
            return True, len(product_models)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to process category '{category}': {e}"))
            logger.error(f"Error processing category {category}", exc_info=True)
            return False, 0

    def _print_summary(self, total_count: int, failed_categories: list[str], dry_run: bool) -> None:
        """Helper to print the final execution summary."""
        self.stdout.write(self.style.NOTICE("--------------------"))
        self.stdout.write(self.style.NOTICE("Scrape process finished."))
        self.stdout.write(f"Total items processed: {total_count}")

        if failed_categories:
            self.stderr.write(
                self.style.ERROR(f"Completed with errors. Failed categories: {', '.join(failed_categories)}")
            )
        else:
            self.stdout.write(self.style.SUCCESS("All categories processed successfully."))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete. No database changes were made."))

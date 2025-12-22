import logging
import uuid
from typing import Any, Dict, List, Optional, cast

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aiecommerce.services.scrape_tecnomega_impl.fetcher import HtmlFetcher
from aiecommerce.services.scrape_tecnomega_impl.mapper import ProductMapper
from aiecommerce.services.scrape_tecnomega_impl.parser import HtmlParser
from aiecommerce.services.scrape_tecnomega_impl.persister import ProductPersister
from aiecommerce.services.scrape_tecnomega_impl.previewer import ProductPreviewer
from aiecommerce.services.scrape_tecnomega_impl.reporter import ScrapeReporter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrapes product data from TECNOMEGA based on provided categories."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--categories",
            nargs="*",
            default=["notebook"],
            help="Optional: List of categories to scrape. Defaults to 'notebook' if not provided.",
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

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        # Extract and cast CLI options to precise types for mypy safety
        dry_run: bool = bool(options.get("dry_run", False))
        categories: List[str] = cast(List[str], options.get("categories", ["notebook"]))
        base_url_opt: Optional[str] = cast(Optional[str], options.get("base_url"))
        settings_base_url: Optional[str] = cast(Optional[str], getattr(settings, "TECNOMEGA_STOCK_LIST_BASE_URL", None))
        base_url: Optional[str] = base_url_opt or settings_base_url

        if not base_url:
            raise CommandError("TECNOMEGA_STOCK_LIST_BASE_URL is not set. Define it in settings or use --base-url.")

        if dry_run:
            self.stdout.write(self.style.WARNING("-- DRY RUN MODE --"))

        self.stdout.write(self.style.NOTICE(f"Starting scrape process for {base_url}"))
        scrape_session_id = str(uuid.uuid4())
        self.stdout.write(self.style.NOTICE(f"Scrape Session ID: {scrape_session_id}"))

        try:
            fetcher = HtmlFetcher(base_url=base_url)
            parser = HtmlParser()
            mapper = ProductMapper()
            persister = ProductPersister()
            previewer = ProductPreviewer(self)
            reporter = ScrapeReporter(self)
        except Exception as e:
            raise CommandError(f"Failed to initialize services: {e}")

        for category in categories:
            self.stdout.write(self.style.HTTP_INFO(f"Processing category: '{category}'..."))
            self._process_category(
                category,
                scrape_session_id,
                dry_run,
                fetcher,
                parser,
                mapper,
                persister,
                previewer,
                reporter,
            )

        reporter.print_summary(dry_run)

    def _process_category(
        self,
        category: str,
        scrape_session_id: str,
        dry_run: bool,
        fetcher: HtmlFetcher,
        parser: HtmlParser,
        mapper: ProductMapper,
        persister: ProductPersister,
        previewer: ProductPreviewer,
        reporter: ScrapeReporter,
    ) -> None:
        try:
            html_content = fetcher.fetch_html(params={"buscar": category})
            raw_products = parser.parse(html_content)

            if not raw_products:
                self.stdout.write(self.style.WARNING(f"No products found for category '{category}'."))
                reporter.track_success(category, 0)
                return

            product_models = mapper.map_to_models(raw_products, scrape_session_id, category)

            if dry_run:
                previewer.show_preview(category, product_models)

            persister.persist(product_models, dry_run)
            reporter.track_success(category, len(product_models))

        except Exception as e:
            logger.error(f"Error processing category {category}", exc_info=True)
            reporter.track_failure(category, e)

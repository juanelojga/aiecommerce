import logging
from typing import List

from aiecommerce.models import ProductRawWeb

from .config import ScrapeConfig
from .fetcher import HtmlFetcher
from .mapper import ProductMapper
from .parser import HtmlParser
from .persister import ProductPersister
from .previewer import ProductPreviewer
from .reporter import ScrapeReporter

# Configure logger
logger = logging.getLogger(__name__)


class ScrapeCoordinator:
    """Orchestrates the scraping workflow, decoupling services from the command."""

    def __init__(
        self,
        config: ScrapeConfig,
        fetcher: HtmlFetcher,
        parser: HtmlParser,
        mapper: ProductMapper,
        persister: ProductPersister,
        reporter: ScrapeReporter,
        previewer: ProductPreviewer,
    ):
        self.config = config
        self.fetcher = fetcher
        self.parser = parser
        self.mapper = mapper
        self.persister = persister
        self.reporter = reporter
        self.previewer = previewer
        import uuid
        from datetime import datetime

        # Format: 20251222T143022_a1b2c3d4
        self.scrape_session_id = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{str(uuid.uuid4())[:8]}"
        logger.info(f"Coordinator initialized with config: {config}")
        logger.info(f"Scrape Session ID: {self.scrape_session_id}")

    def run(self) -> None:
        """Executes the entire scrape-and-save workflow."""
        logger.info("Starting scrape run...")
        try:
            self._process_categories()
        except Exception as e:
            logger.exception(f"An unexpected error occurred during the scrape run: {e}")
        finally:
            self.reporter.print_summary(self.config.dry_run)
            logger.info("Scrape run finished.")

    def _process_categories(self) -> None:
        """Iterates through categories and processes them."""
        for category in self.config.categories:
            logger.info(f"Processing category: {category}")
            try:
                products_for_category = self._process_single_category(category)
                self.reporter.track_success(category, len(products_for_category))
            except Exception as e:
                logger.error(f"Failed to process category {category}. Error: {e}", exc_info=True)
                self.reporter.track_failure(category, e)

    def _process_single_category(self, category: str) -> List[ProductRawWeb]:
        """Fetches, parses, maps, and persists products for one category."""
        url = self.config.get_base_url()

        html_content = self.fetcher.fetch(url, category)
        if not html_content:
            logger.warning(f"No content fetched for category {category} from {url}")
            return []

        raw_dtos = self.parser.parse(html_content)
        if not raw_dtos:
            return []

        product_entities = [self.mapper.to_entity(dto, self.scrape_session_id, category) for dto in raw_dtos]

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would save {len(product_entities)} products for category '{category}'.")
            self.previewer.show_preview(category, product_entities)
            return product_entities

        logger.info(f"Persisting {len(product_entities)} products for category '{category}'.")
        return self.persister.save_bulk(product_entities)

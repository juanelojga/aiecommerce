import logging
from typing import Any, Dict, List, cast

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.services.scrape_tecnomega_impl.config import (
    DEFAULT_CATEGORIES,
    ScrapeConfig,
    ScrapeConfigurationError,
)
from aiecommerce.services.scrape_tecnomega_impl.coordinator import ScrapeCoordinator
from aiecommerce.services.scrape_tecnomega_impl.fetcher import HtmlFetcher
from aiecommerce.services.scrape_tecnomega_impl.mapper import ProductMapper
from aiecommerce.services.scrape_tecnomega_impl.parser import HtmlParser
from aiecommerce.services.scrape_tecnomega_impl.persister import ProductPersister
from aiecommerce.services.scrape_tecnomega_impl.previewer import ProductPreviewer
from aiecommerce.services.scrape_tecnomega_impl.reporter import ScrapeReporter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    A thin wrapper around the ScrapeCoordinator to orchestrate product scraping
    from a Django management command.
    """

    help = "Scrapes product data from TECNOMEGA by orchestrating a coordinator."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--categories",
            nargs="*",
            help=("Optional: List of categories to scrape. " f"Defaults to: {', '.join(DEFAULT_CATEGORIES)}"),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving any data to the database.",
        )

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        self.stdout.write(self.style.NOTICE("Initializing scrape process..."))

        try:
            # 1. Create Configuration from CLI arguments
            config = self._create_config(options)

            if config.dry_run:
                self.stdout.write(self.style.WARNING("-- DRY RUN MODE --"))

            # 2. Wire up dependencies
            fetcher = HtmlFetcher()
            parser = HtmlParser()
            mapper = ProductMapper()
            persister = ProductPersister()
            # Services requiring command output can be passed `self`
            reporter = ScrapeReporter(self)
            previewer = ProductPreviewer(self)

            # 3. Instantiate and run the coordinator
            self.stdout.write(self.style.NOTICE(f"Starting scrape for categories: {config.categories}"))

            coordinator = ScrapeCoordinator(
                config=config,
                fetcher=fetcher,
                parser=parser,
                mapper=mapper,
                persister=persister,
                reporter=reporter,
                previewer=previewer,
            )
            coordinator.run()

            self.stdout.write(self.style.SUCCESS("Scrape process completed successfully."))

        except ScrapeConfigurationError as e:
            raise CommandError(f"Configuration error: {e}")
        except Exception as e:
            logger.exception("An unexpected error occurred during the handle execution.")
            raise CommandError(f"An unexpected error occurred: {e}")

    def _create_config(self, options: Dict[str, Any]) -> ScrapeConfig:
        """Builds the ScrapeConfig dataclass from command options."""
        dry_run: bool = bool(options.get("dry_run", False))
        # Use provided categories, otherwise None will make the dataclass use its default
        categories: List[str] | None = cast(List[str] | None, options.get("categories"))

        # Explicitly annotate to avoid mypy inferring Dict[str, bool]
        config_kwargs: Dict[str, Any] = {
            "dry_run": dry_run,
        }
        if categories is not None:
            config_kwargs["categories"] = categories

        return ScrapeConfig(**config_kwargs)

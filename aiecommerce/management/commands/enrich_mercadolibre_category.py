import logging
from typing import Any

import instructor
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_category_impl.ai_attribute_filler import MercadolibreAIAttributeFiller
from aiecommerce.services.mercadolibre_category_impl.attribute_fetcher import MercadolibreCategoryAttributeFetcher
from aiecommerce.services.mercadolibre_category_impl.category_predictor import MercadolibreCategoryPredictorService
from aiecommerce.services.mercadolibre_category_impl.orchestrator import MercadolibreEnrichmentCategoryOrchestrator
from aiecommerce.services.mercadolibre_category_impl.price import MercadoLibrePriceEngine
from aiecommerce.services.mercadolibre_category_impl.selector import MercadolibreCategorySelector
from aiecommerce.services.mercadolibre_category_impl.stock import MercadoLibreStockEngine
from aiecommerce.services.mercadolibre_impl import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Enqueues tasks to fetch and process categories for MercadoLibre products that do not have them."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--force", action="store_true", help="Reprocess products that already have categories")
        parser.add_argument("--dry-run", action="store_true", help="Show which products would be processed without making any changes")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between processing products (default: 0.5)")
        parser.add_argument("--category", type=str, help="Filter by specific product category name")
        parser.add_argument("--site-id", type=str, default="MEC", help="MercadoLibre site ID (default: MEC for Ecuador)")

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Execute the MercadoLibre category enrichment process.

        This command:
        1. Authenticates with MercadoLibre API
        2. Selects products that need category enrichment
        3. Predicts appropriate categories using AI
        4. Fetches required attributes for each category
        5. Fills attributes using AI when necessary
        6. Updates product listings with enriched data
        """
        force: bool = options["force"]
        dry_run: bool = options["dry_run"]
        delay: float = options["delay"]
        category: str | None = options["category"]
        site_id: str = options["site_id"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        logger.info(f"Starting MercadoLibre category enrichment: force={force}, dry_run={dry_run}, delay={delay}, category={category}, site_id={site_id}")

        try:
            # Authenticate with MercadoLibre
            token_instance = self._get_valid_token(site_id=site_id, sandbox=False)

            # Initialize services
            client = MercadoLibreClient(access_token=token_instance.access_token)
            orchestrator = self._initialize_orchestrator(client=client, site_id=site_id)

            # Run the enrichment batch
            stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay, category=category)

            # Report results
            self._report_results(stats=stats, dry_run=dry_run)

        except CommandError:
            # Re-raise CommandError to preserve error message formatting
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during category enrichment: {e}")
            raise CommandError(f"Failed to enrich categories: {e}")

    def _get_valid_token(self, site_id: str, sandbox: bool = False) -> MercadoLibreToken:
        """
        Retrieve and validate MercadoLibre authentication token.

        Args:
            site_id: MercadoLibre site identifier (e.g., 'MEC' for Ecuador)
            sandbox: Whether to use test user credentials

        Returns:
            Valid MercadoLibreToken instance

        Raises:
            CommandError: If token cannot be retrieved or validated
        """
        auth_service = MercadoLibreAuthService()

        try:
            # Find the latest token for the specified environment
            token_instance = MercadoLibreToken.objects.filter(is_test_user=sandbox).latest("created_at")

            # Ensure token is valid (refreshes if needed)
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)

            logger.info(f"Successfully authenticated with MercadoLibre (site: {site_id}, user_id: {token_instance.user_id})")
            return token_instance

        except MercadoLibreToken.DoesNotExist:
            mode = "sandbox" if sandbox else "production"
            raise CommandError(f"No {mode} token found for site '{site_id}'. Please run 'python manage.py verify_ml_handshake' to authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token for site '{site_id}': {e}")

    def _initialize_orchestrator(self, client: MercadoLibreClient, site_id: str) -> MercadolibreEnrichmentCategoryOrchestrator:
        """
        Initialize the enrichment orchestrator with all required services.

        Args:
            client: Authenticated MercadoLibre API client
            site_id: MercadoLibre site identifier

        Returns:
            Configured orchestrator instance
        """
        # Product selector
        selector = MercadolibreCategorySelector()

        # MercadoLibre API services
        category_predictor = MercadolibreCategoryPredictorService(client=client, site_id=site_id)
        attribute_fetcher = MercadolibreCategoryAttributeFetcher(client=client)

        # Business logic engines
        price_engine = MercadoLibrePriceEngine()
        stock_engine = MercadoLibreStockEngine()

        # AI attribute filler
        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL

        if not api_key or not base_url:
            raise CommandError("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be configured in settings")

        openai_client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url), mode=instructor.Mode.JSON)
        attribute_filler = MercadolibreAIAttributeFiller(client=openai_client)

        return MercadolibreEnrichmentCategoryOrchestrator(
            selector=selector,
            category_predictor=category_predictor,
            price_engine=price_engine,
            stock_engine=stock_engine,
            attribute_fetcher=attribute_fetcher,
            attribute_filler=attribute_filler,
        )

    def _report_results(self, stats: dict[str, int], dry_run: bool) -> None:
        """
        Display enrichment results to the user.

        Args:
            stats: Dictionary containing 'total' and 'processed' counts
            dry_run: Whether this was a dry run
        """
        total = stats.get("total", 0)
        processed = stats.get("processed", 0)

        if total == 0:
            self.stdout.write(self.style.WARNING("No products found that need category enrichment."))
            return

        mode = "would be processed" if dry_run else "processed"
        self.stdout.write(self.style.SUCCESS(f"\nCompleted: {processed}/{total} products {mode}"))

        if not dry_run and processed < total:
            failed = total - processed
            self.stdout.write(self.style.WARNING(f"Warning: {failed} products failed to process"))

        logger.info(f"Category enrichment complete: {processed}/{total} products {mode}")

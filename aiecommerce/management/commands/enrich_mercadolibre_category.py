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


class Command(BaseCommand):
    help = "Enqueues tasks to fetch and process categories for mercadolibre products that do not have them."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reprocess products that already have specs")
        parser.add_argument("--dry-run", action="store_true", help="Show which products would be processed, but do not enqueue any tasks.")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between products")

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        site_id = "MEC"

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        # Initialize the selector and the main batch orchestrator
        selector = MercadolibreCategorySelector()

        auth_service = MercadoLibreAuthService()
        try:
            # We first try to find the latest token to get a user_id
            token_instance = MercadoLibreToken.objects.filter(is_test_user=False).latest("created_at")
            # Then we use the auth_service to ensure it is valid (refreshes if needed)
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError(f"No token found for site '{site_id}'. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token for site '{site_id}': {e}")

        client = MercadoLibreClient(access_token=token_instance.access_token)

        category_predictor = MercadolibreCategoryPredictorService(client=client, site_id=site_id)
        attribute_fetcher = MercadolibreCategoryAttributeFetcher(client=client)

        price_engine = MercadoLibrePriceEngine()
        stock_engine = MercadoLibreStockEngine()

        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL

        open_client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))
        attribute_filler = MercadolibreAIAttributeFiller(client=open_client)

        orchestrator = MercadolibreEnrichmentCategoryOrchestrator(
            selector=selector,
            category_predictor=category_predictor,
            price_engine=price_engine,
            stock_engine=stock_engine,
            attribute_fetcher=attribute_fetcher,
            attribute_filler=attribute_filler,
        )

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        if stats["total"] == 0:
            self.stdout.write(self.style.WARNING("No products found without images."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
            self.stdout.write(self.style.SUCCESS(f"Enqueued {stats['processed']}/{stats['total']} tasks"))

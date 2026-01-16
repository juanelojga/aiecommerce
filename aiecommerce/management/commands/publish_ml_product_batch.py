import logging

import instructor
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_category_impl.attribute_fixer import MercadolibreAttributeFixer
from aiecommerce.services.mercadolibre_impl import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl import BatchPublisherOrchestrator
from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator
from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Publishes a batch of products to Mercado Libre.
    """

    help = "Publishes all products with 'Pending' status to Mercado Libre."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Prepare the payload and log it, but do not actually send it to Mercado Libre.",
        )
        parser.add_argument(
            "--sandbox",
            action="store_true",
            help="Use the Mercado Libre sandbox environment (test user).",
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        sandbox = options["sandbox"]

        mode = "SANDBOX" if sandbox else "PRODUCTION"

        auth_service = MercadoLibreAuthService()
        try:
            token_instance = MercadoLibreToken.objects.filter(is_test_user=sandbox).latest("created_at")
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError(f"No token found for {'sandbox' if sandbox else 'production'} user. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token: {e}")

        self.stdout.write(self.style.SUCCESS(f"--- Starting batch product publication in {mode} mode ---"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run is enabled. No data will be sent to Mercado Libre."))

        try:
            client = MercadoLibreClient(access_token=token_instance.access_token)
            open_client = instructor.from_openai(OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url=settings.OPENROUTER_BASE_URL))
            attribute_fixer = MercadolibreAttributeFixer(client=open_client)
            publisher = MercadoLibrePublisherService(client=client, attribute_fixer=attribute_fixer)
            publisher_orchestrator = PublisherOrchestrator(publisher=publisher)

            batch_orchestrator = BatchPublisherOrchestrator(publisher_orchestrator=publisher_orchestrator)
            batch_orchestrator.run(dry_run=dry_run, sandbox=sandbox)
            self.stdout.write(self.style.SUCCESS("--- Batch publication process finished ---"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            logger.exception("Failed to publish batch of products")

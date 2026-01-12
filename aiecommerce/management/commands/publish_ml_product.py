import logging

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator
from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Publishes a single product to Mercado Libre.
    """

    help = "Publishes a single product to Mercado Libre by its product code."

    def add_arguments(self, parser) -> None:
        parser.add_argument("product_code", type=str, help="The code of the ProductMaster to publish.")
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
        product_code = options["product_code"]
        dry_run = options["dry_run"]
        sandbox = options["sandbox"]

        mode = "SANDBOX" if sandbox else "PRODUCTION"

        auth_service = MercadoLibreAuthService()
        try:
            # We first try to find the latest token to get a user_id
            token_instance = MercadoLibreToken.objects.filter(is_test_user=sandbox).latest("created_at")
            # Then we use the auth_service to ensure it is valid (refreshes if needed)
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError("No token found for site MEC. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token for site MEC: {e}")

        self.stdout.write(self.style.SUCCESS(f"--- Starting product publication for '{product_code}' in {mode} mode ---"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run is enabled. No data will be sent to Mercado Libre."))

        try:
            client = MercadoLibreClient(access_token=token_instance.access_token)
            publisher = MercadoLibrePublisherService(client=client)

            orchestrator = PublisherOrchestrator(publisher=publisher)
            orchestrator.run(product_code=product_code, dry_run=dry_run, sandbox=sandbox)
            self.stdout.write(self.style.SUCCESS("--- Publication process finished ---"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            logger.exception(f"Failed to publish product {product_code}")

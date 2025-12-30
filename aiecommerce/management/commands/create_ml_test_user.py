import logging

from django.core.management.base import BaseCommand

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Creates a new Mercado Libre test user.
    """

    help = "Creates a new Mercado Libre test user using a production token for authorization."

    def add_arguments(self, parser):
        parser.add_argument(
            "--site",
            type=str,
            default="MEC",
            help="The site ID for the test user (default: MEC for ECUADOR)",
        )

    def handle(self, *args, **options) -> None:
        site_id = options["site"]
        self.stdout.write(self.style.SUCCESS(f"--- Starting Mercado Libre Test User Creation for site {site_id} ---"))

        # 1. Get a production token to authorize the request
        self.stdout.write("Fetching a production token to authorize the request...")
        prod_token = MercadoLibreToken.objects.filter(is_test_user=False).first()
        if not prod_token:
            self.stdout.write(self.style.ERROR("No production Mercado Libre token found."))
            self.stdout.write(self.style.WARNING("Please ensure a non-test user has authenticated via OAuth2."))
            return

        self.stdout.write(f"Using token for user_id: {prod_token.user_id}")

        # 2. Initialize the client with the production token
        client = MercadoLibreClient(access_token=prod_token.access_token)

        # 3. Call the create_test_user API
        self.stdout.write(f"Calling the create_test_user API for site {site_id}...")
        try:
            test_user_data = client.post("/users/test_user", json={"site_id": site_id})
            self.stdout.write(self.style.SUCCESS("Successfully created test user."))
        except MLAPIError as e:
            self.stdout.write(self.style.ERROR(f"API call failed: {e}"))
            self.stdout.write(self.style.WARNING("Failed to create test user. Check API logs for details."))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            return

        # 4. Output the credentials
        self.stdout.write(self.style.SUCCESS("--- Test User Created Successfully ---"))
        self.stdout.write(f"ID: {test_user_data.get('id')}")
        self.stdout.write(f"Nickname: {test_user_data.get('nickname')}")
        self.stdout.write(f"Password: {test_user_data.get('password')}")
        self.stdout.write(f"Site Status: {test_user_data.get('site_status')}")
        self.stdout.write("You can now use these credentials to log in to the Mercado Libre sandbox environment.")

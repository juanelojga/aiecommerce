import logging

from django.core.management.base import BaseCommand

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
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

        # 1. Get a production token to authorize the request
        prod_token = MercadoLibreToken.objects.filter(is_test_user=False).first()
        if not prod_token:
            self.stdout.write(self.style.ERROR("No production Mercado Libre token found."))
            return

        auth_service = MercadoLibreAuthService()
        valid_token = auth_service.get_valid_token(user_id=prod_token.user_id)

        # 2. Initialize the client with the production token
        client = MercadoLibreClient(access_token=valid_token.access_token)

        # 3. Call the create_test_user API
        try:
            test_user_data = client.post("/users/test_user", json={"site_id": site_id})

        except MLAPIError as e:
            self.stdout.write(self.style.ERROR(f"API call failed: {e}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            return

        # 4. Output the credentials
        import json

        output = {
            "id": test_user_data.get("id"),
            "nickname": test_user_data.get("nickname"),
            "password": test_user_data.get("password"),
            "site_status": test_user_data.get("site_status"),
        }
        self.stdout.write(json.dumps(output, indent=4))

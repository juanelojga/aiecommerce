import logging

from django.core.management.base import BaseCommand

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLTokenError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Verifies the Mercado Libre API handshake by fetching user data.
    """

    help = "Verifies the Mercado Libre API handshake for a specific user or the first available one."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--user-id",
            type=str,
            help="The Mercado Libre User ID to verify. If not provided, the first available token will be used.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all users with available Mercado Libre tokens and exit.",
        )
        parser.add_argument(
            "--sandbox",
            action="store_true",
            help="Use sandbox environment for verification.",
        )

    def handle(self, *args, **options) -> None:
        if options["list"]:
            self._list_tokens()
            return

        self.stdout.write(self.style.SUCCESS("--- Starting Mercado Libre Handshake Verification ---"))

        user_id = options.get("user_id")
        is_sandbox_mode = options["sandbox"]
        mode = "SANDBOX" if is_sandbox_mode else "PRODUCTION"

        # 1. Get the user_id if not provided
        if not user_id:
            token_record = MercadoLibreToken.objects.filter(is_test_user=is_sandbox_mode).first()
            if not token_record:
                self.stdout.write(self.style.ERROR(f"No {mode} tokens found in the database. Cannot verify handshake."))
                self.stdout.write(self.style.WARNING(f"Please ensure at least one user has gone through the OAuth2 flow at /mercadolibre/auth/ for {mode} environment."))
                return
            user_id = token_record.user_id
            self.stdout.write(f"No User ID provided. Using first available {mode} user: {user_id}")
        else:
            self.stdout.write(f"Verifying handshake for User ID: {user_id} in {mode} mode")

        # 2. Initialize the auth service and get a valid token
        auth_service = MercadoLibreAuthService()
        try:
            self.stdout.write(f"Attempting to retrieve a valid {mode} token for user_id: {user_id}...")
            token_record = auth_service.get_valid_token(user_id=str(user_id), use_sandbox=is_sandbox_mode)
            self.stdout.write(self.style.SUCCESS(f"Successfully retrieved a valid {mode} token."))
        except MLTokenError as e:
            self.stdout.write(self.style.ERROR(f"Failed to get {mode} token: {e}"))
            self.stdout.write(self.style.WARNING(f"Please ensure user {user_id} has gone through the OAuth2 flow at /mercadolibre/auth/ for {mode} environment."))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            return

        # 3. Initialize the API client with the token
        self.stdout.write(f"Initializing Mercado Libre client for {mode}...")
        client = MercadoLibreClient(access_token=token_record.access_token)

        # 4. Call the /users/me endpoint
        self.stdout.write(f"Attempting to fetch data from the /users/me endpoint in {mode}...")
        try:
            user_data = client.get("users/me")
            self.stdout.write(self.style.SUCCESS(f"--- Handshake Verified Successfully in {mode} Mode! ---"))
            self.stdout.write("Received the following user data:")
            self.stdout.write(str(user_data))
        except MLAPIError as e:
            self.stdout.write(self.style.ERROR(f"API call failed in {mode} mode: {e}"))
            self.stdout.write(self.style.WARNING(f"The handshake failed in {mode} mode. Check your credentials and HTTPS setup."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected API error occurred in {mode} mode: {e}"))

        self.stdout.write(self.style.SUCCESS("--- Verification Complete ---"))

    def _list_tokens(self) -> None:
        tokens = MercadoLibreToken.objects.all()
        if not tokens.exists():
            self.stdout.write(self.style.WARNING("No Mercado Libre tokens found in the database."))
            return

        self.stdout.write(self.style.SUCCESS("Available Mercado Libre Tokens:"))
        for token in tokens:
            status = "EXPIRED" if token.is_expired() else "VALID"
            self.stdout.write(f"- User ID: {token.user_id} (Status: {status}, Expires: {token.expires_at})")

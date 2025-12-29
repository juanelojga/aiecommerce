import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLTokenError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Verifies the Mercado Libre API handshake by fetching user data.
    """

    help = "Verifies the Mercado Libre API handshake for the first available user."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Starting Mercado Libre Handshake Verification ---"))

        # 1. Get the first user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No users found in the database. Cannot verify handshake."))
            return

        self.stdout.write(f"Found user: {user.username} (ID: {user.id})")

        # 2. Initialize the auth service and get a valid token
        auth_service = MercadoLibreAuthService()
        try:
            self.stdout.write(f"Attempting to retrieve a valid token for user_id: {user.id}...")
            token_record = auth_service.get_valid_token(user_id=str(user.id))
            self.stdout.write(self.style.SUCCESS("Successfully retrieved a valid token."))
        except MLTokenError as e:
            self.stdout.write(self.style.ERROR(f"Failed to get token: {e}"))
            self.stdout.write(self.style.WARNING("Please ensure the user has gone through the OAuth2 flow at /mercadolibre/auth/"))
            return

        # 3. Initialize the API client with the token
        self.stdout.write("Initializing Mercado Libre client...")
        client = MercadoLibreClient(access_token=token_record.access_token)

        # 4. Call the /users/me endpoint
        self.stdout.write("Attempting to fetch data from the /users/me endpoint...")
        try:
            user_data = client.get("users/me")
            self.stdout.write(self.style.SUCCESS("--- Handshake Verified Successfully! ---"))
            self.stdout.write("Received the following user data:")
            self.stdout.write(str(user_data))
        except MLAPIError as e:
            self.stdout.write(self.style.ERROR(f"API call failed: {e}"))
            self.stdout.write(self.style.WARNING("The handshake failed. Check your credentials and HTTPS setup."))

        self.stdout.write(self.style.SUCCESS("--- Verification Complete ---"))

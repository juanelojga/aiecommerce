import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError

logger = logging.getLogger(__name__)


class MercadoLibreAuthService:
    """Orchestrates the Mercado Libre OAuth2 token lifecycle."""

    def __init__(self, client: Optional[MercadoLibreClient] = None):
        self.client = client or MercadoLibreClient()

    def get_valid_token(self, user_id: str) -> MercadoLibreToken:
        """
        Retrieves a valid token for a user, refreshing it if it's expired.
        """
        try:
            token_record = MercadoLibreToken.objects.get(user_id=user_id)
        except MercadoLibreToken.DoesNotExist:
            logger.error(f"No Mercado Libre token found for user_id: {user_id}")
            raise MLTokenError(f"No token record for user_id: {user_id}")

        if token_record.is_expired():
            logger.info(f"Token for user {user_id} is expired. Refreshing now.")
            return self.refresh_token_for_user(token_record)

        return token_record

    def refresh_token_for_user(self, token_record: MercadoLibreToken) -> MercadoLibreToken:
        """
        Performs the token refresh flow and updates the database record.
        Strictly overwrites the existing token data.
        """
        try:
            token_data = self.client.refresh_token(token_record.refresh_token)
            logger.info(f"Successfully refreshed token for user {token_record.user_id}")
        except Exception as e:
            logger.error(f"Failed to refresh ML token for user {token_record.user_id}: {e}")
            raise MLTokenError(f"Token refresh failed for user {token_record.user_id}") from e

        # Overwrite existing token details with the new ones
        token_record.access_token = token_data["access_token"]
        token_record.refresh_token = token_data["refresh_token"]  # ML returns a new refresh token
        token_record.expires_at = timezone.now() + timedelta(seconds=token_data["expires_in"])
        token_record.save()

        return token_record

    def init_token_from_code(self, code: str, redirect_uri: str) -> MercadoLibreToken:
        """
        Handles the initial token exchange from an authorization code and creates the record.
        """
        try:
            token_data = self.client.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
            logger.info(f"Successfully exchanged code for token for user {token_data.get('user_id')}")
        except Exception as e:
            logger.error(f"Failed to exchange ML code for token: {e}")
            raise MLTokenError("Code exchange failed") from e

        user_id = token_data["user_id"]
        expires_at = timezone.now() + timedelta(seconds=token_data["expires_in"])

        # Use update_or_create to handle re-authentication seamlessly
        token_record, created = MercadoLibreToken.objects.update_or_create(
            user_id=user_id,
            defaults={
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": expires_at,
            },
        )
        logger.info(f"Token record {'created' if created else 'updated'} for user {user_id}.")
        return token_record

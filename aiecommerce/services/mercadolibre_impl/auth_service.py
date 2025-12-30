import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import (
    MLAPIError,
    MLTokenError,
    MLTokenExchangeError,
    MLTokenRefreshError,
    MLTokenValidationError,
)

logger = logging.getLogger(__name__)


class MercadoLibreAuthService:
    """Orchestrates the Mercado Libre OAuth2 token lifecycle."""

    def __init__(self, client: Optional[MercadoLibreClient] = None, clock=timezone):
        self.client = client or MercadoLibreClient()
        self.clock = clock

    def get_valid_token(self, user_id: str, use_sandbox: bool = False) -> MercadoLibreToken:
        """
        Retrieves a valid token, refreshing it if it's expired.
        - If use_sandbox is True, ignores user_id and fetches the first available test user token.
        - Otherwise, fetches the token for the specified user_id.
        Uses database-level locking to prevent race conditions during refresh.
        """
        with transaction.atomic():
            try:
                if use_sandbox:
                    token_record = MercadoLibreToken.objects.select_for_update().filter(is_test_user=True).first()
                    if not token_record:
                        logger.error("No sandbox (test user) token found in the database.")
                        raise MLTokenError("No sandbox token record available.")
                else:
                    token_record = MercadoLibreToken.objects.select_for_update().get(user_id=user_id)
            except MercadoLibreToken.DoesNotExist:
                logger.error(f"No Mercado Libre token found for user_id: {user_id}")
                raise MLTokenError(f"No token record for user_id: {user_id}")

            if self._is_token_expired(token_record):
                logger.debug(f"Token for user {token_record.user_id} is expired or nearing expiration. Refreshing.")
                return self.refresh_token_for_user(token_record)

            return token_record

    def _is_token_expired(self, token_record: MercadoLibreToken) -> bool:
        """Checks if the token is expired or close to expiring (buffer of 5 minutes)."""
        # We use the injected clock instead of hard dependency on timezone.now()
        return self.clock.now() >= (token_record.expires_at - timedelta(minutes=5))

    def refresh_token_for_user(self, token_record: MercadoLibreToken) -> MercadoLibreToken:
        """
        Performs the token refresh flow and updates the database record.
        Strictly overwrites the existing token data.
        """
        try:
            token_data = self.client.refresh_token(token_record.refresh_token)
            self._validate_token_data(token_data)
            logger.debug(f"Successfully retrieved new token data for user {token_record.user_id}")
        except (MLAPIError, MLTokenValidationError) as e:
            logger.error(f"Failure while refreshing ML token for user {token_record.user_id}: {e}")
            raise MLTokenRefreshError(f"Token refresh failed for user {token_record.user_id}") from e
        except Exception as e:
            logger.exception(f"Unexpected error refreshing ML token for user {token_record.user_id}")
            raise MLTokenRefreshError("An unexpected error occurred during token refresh") from e

        # Update token details
        token_record.access_token = token_data["access_token"]
        token_record.refresh_token = token_data["refresh_token"]
        token_record.expires_at = self.clock.now() + timedelta(seconds=token_data["expires_in"])
        token_record.save()

        logger.info(f"Token record updated for user {token_record.user_id} after refresh.")
        return token_record

    def init_token_from_code(self, code: str, redirect_uri: str) -> MercadoLibreToken:
        """
        Handles the initial token exchange from an authorization code and creates the record.
        """
        try:
            token_data = self.client.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
            self._validate_token_data(token_data)
            logger.debug(f"Successfully exchanged code for token for user {token_data.get('user_id')}")
        except (MLAPIError, MLTokenValidationError) as e:
            logger.error(f"Failure while exchanging ML code: {e}")
            raise MLTokenExchangeError("Code exchange failed") from e
        except Exception as e:
            logger.exception("Unexpected error during ML code exchange")
            raise MLTokenExchangeError("An unexpected error occurred during code exchange") from e

        user_id = token_data["user_id"]
        expires_at = self.clock.now() + timedelta(seconds=token_data["expires_in"])

        token_record, created = MercadoLibreToken.objects.update_or_create(
            user_id=user_id,
            defaults={
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": expires_at,
            },
        )
        logger.info(f"Token record {'created' if created else 'updated'} for user {user_id} from code.")
        return token_record

    def _validate_token_data(self, token_data: Dict[str, Any]) -> None:
        """Validates that the token response contains all required fields."""
        required_fields = ["access_token", "refresh_token", "expires_in", "user_id"]
        missing_fields = [field for field in required_fields if field not in token_data]
        if missing_fields:
            raise MLTokenValidationError(f"Token response missing required fields: {', '.join(missing_fields)}")

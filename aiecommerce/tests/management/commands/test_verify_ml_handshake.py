import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLTokenError


@pytest.mark.django_db
class TestVerifyMLHandshakeCommand:
    def test_list_tokens_empty(self):
        out = io.StringIO()
        call_command("verify_ml_handshake", "--list", stdout=out)
        output = out.getvalue()
        assert "No Mercado Libre tokens found in the database." in output

    def test_list_tokens_with_data(self):
        MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )
        out = io.StringIO()
        call_command("verify_ml_handshake", "--list", stdout=out)
        output = out.getvalue()
        assert "Available Mercado Libre Tokens:" in output
        assert "- User ID: user123 (Status: VALID" in output

    def test_handle_no_tokens_no_user_id(self):
        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()
        assert "No tokens found in the database. Cannot verify handshake." in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_token_error(self, MockAuthService):
        # Create a token so it doesn't fail at step 1
        MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )

        mock_instance = MockAuthService.return_value
        mock_instance.get_valid_token.side_effect = MLTokenError("Token missing")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()

        assert "Attempting to retrieve a valid token for user_id: user123..." in output
        assert "Failed to get token: Token missing" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_api_error(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )

        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.side_effect = MLAPIError("API Error")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()

        assert "Attempting to fetch data from the /users/me endpoint..." in output
        assert "API call failed: API Error" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_success(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )

        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.return_value = {"id": 123, "nickname": "TESTUSER"}

        out = io.StringIO()
        call_command("verify_ml_handshake", "--user-id", "user123", stdout=out)
        output = out.getvalue()

        assert "Verifying handshake for User ID: user123" in output
        assert "Successfully retrieved a valid token." in output
        assert "--- Handshake Verified Successfully! ---" in output
        assert "{'id': 123, 'nickname': 'TESTUSER'}" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_unexpected_error(self, MockAuthService):
        MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )
        MockAuthService.return_value.get_valid_token.side_effect = Exception("Unexpected")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()
        assert "An unexpected error occurred: Unexpected" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_unexpected_api_error(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1)
        )
        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.side_effect = Exception("Unexpected API boom")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()
        assert "An unexpected API error occurred: Unexpected API boom" in output

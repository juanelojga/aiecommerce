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
        MercadoLibreToken.objects.create(user_id="user123", access_token="access", refresh_token="refresh", expires_at=timezone.now() + timedelta(hours=1))
        out = io.StringIO()
        call_command("verify_ml_handshake", "--list", stdout=out)
        output = out.getvalue()
        assert "Available Mercado Libre Tokens:" in output
        assert "- User ID: user123 (Status: VALID" in output

    def test_handle_no_tokens_no_user_id(self):
        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()
        assert "No PRODUCTION tokens found in the database. Cannot verify handshake." in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_token_error(self, MockAuthService):
        # Create a token so it doesn't fail at step 1
        MercadoLibreToken.objects.create(
            user_id="user123",
            access_token="access",
            refresh_token="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )

        mock_instance = MockAuthService.return_value
        mock_instance.get_valid_token.side_effect = MLTokenError("Token missing")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()

        assert "No User ID provided. Using first available PRODUCTION user: user123" in output
        assert "Attempting to retrieve a valid PRODUCTION token for user_id: user123..." in output
        assert "Failed to get PRODUCTION token: Token missing" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_api_error(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="user123",
            access_token="access",
            refresh_token="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )

        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.side_effect = MLAPIError("API Error")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()

        assert "Attempting to fetch data from the /users/me endpoint in PRODUCTION..." in output
        assert "API call failed in PRODUCTION mode: API Error" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_success(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="user123",
            access_token="access",
            refresh_token="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )

        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.return_value = {"id": 123, "nickname": "TESTUSER"}

        out = io.StringIO()
        call_command("verify_ml_handshake", "--user-id", "user123", stdout=out)
        output = out.getvalue()

        assert "Verifying handshake for User ID: user123 in PRODUCTION mode" in output
        assert "Attempting to retrieve a valid PRODUCTION token for user_id: user123..." in output
        assert "Successfully retrieved a valid PRODUCTION token." in output
        assert "--- Handshake Verified Successfully in PRODUCTION Mode! ---" in output
        assert "{'id': 123, 'nickname': 'TESTUSER'}" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_unexpected_error(self, MockAuthService):
        MercadoLibreToken.objects.create(
            user_id="user123",
            access_token="access",
            refresh_token="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
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
            user_id="user123",
            access_token="access",
            refresh_token="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )
        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.side_effect = Exception("Unexpected API boom")

        out = io.StringIO()
        call_command("verify_ml_handshake", stdout=out)
        output = out.getvalue()
        assert "An unexpected API error occurred in PRODUCTION mode: Unexpected API boom" in output

    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreClient")
    @patch("aiecommerce.management.commands.verify_ml_handshake.MercadoLibreAuthService")
    def test_handle_sandbox_success(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="testuser456",
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=True,
        )

        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.get.return_value = {"id": 456, "nickname": "SANDBOXUSER"}

        out = io.StringIO()
        call_command("verify_ml_handshake", "--user-id", "testuser456", "--sandbox", stdout=out)
        output = out.getvalue()

        assert "Verifying handshake for User ID: testuser456 in SANDBOX mode" in output
        assert "Attempting to retrieve a valid SANDBOX token for user_id: testuser456..." in output
        assert "Successfully retrieved a valid SANDBOX token." in output
        assert "--- Handshake Verified Successfully in SANDBOX Mode! ---" in output
        assert "{'id': 456, 'nickname': 'SANDBOXUSER'}" in output

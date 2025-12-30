import io
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError


@pytest.mark.django_db
class TestCreateMLTestUserCommand:
    def test_no_production_token(self):
        out = io.StringIO()
        call_command("create_ml_test_user", stdout=out)
        output = out.getvalue()
        assert "No production Mercado Libre token found." in output

    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreClient")
    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreAuthService")
    def test_create_test_user_success(self, MockAuthService, MockClient):
        # Setup production token
        token = MercadoLibreToken.objects.create(
            user_id="prod_user",
            access_token="prod_access",
            refresh_token="prod_refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )

        MockAuthService.return_value.get_valid_token.return_value = token

        test_user_response = {
            "id": 123456,
            "nickname": "TETING_USER",
            "password": "password123",
            "site_status": "active",
            "other_field": "ignore_me",
        }
        MockClient.return_value.post.return_value = test_user_response

        out = io.StringIO()
        call_command("create_ml_test_user", "--site", "MLM", stdout=out)
        output = out.getvalue()

        # Check if the output is the expected JSON
        decoded_output = json.loads(output)
        assert decoded_output["id"] == 123456
        assert decoded_output["nickname"] == "TETING_USER"
        assert decoded_output["password"] == "password123"
        assert decoded_output["site_status"] == "active"
        assert "other_field" not in decoded_output

        # Verify client call
        MockClient.return_value.post.assert_called_once_with("/users/test_user", json={"site_id": "MLM"})

    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreClient")
    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreAuthService")
    def test_create_test_user_default_site(self, MockAuthService, MockClient):
        # Setup production token
        token = MercadoLibreToken.objects.create(
            user_id="prod_user",
            access_token="prod_access",
            refresh_token="prod_refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )
        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.post.return_value = {"id": 123}

        out = io.StringIO()
        call_command("create_ml_test_user", stdout=out)

        # Verify client call with default site "MEC"
        MockClient.return_value.post.assert_called_once_with("/users/test_user", json={"site_id": "MEC"})

    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreClient")
    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreAuthService")
    def test_create_test_user_api_error(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="prod_user",
            access_token="prod_access",
            refresh_token="prod_refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )
        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.post.side_effect = MLAPIError("API Error message")

        out = io.StringIO()
        call_command("create_ml_test_user", stdout=out)
        output = out.getvalue()

        assert "API call failed: API Error message" in output

    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreClient")
    @patch("aiecommerce.management.commands.create_ml_test_user.MercadoLibreAuthService")
    def test_create_test_user_unexpected_error(self, MockAuthService, MockClient):
        token = MercadoLibreToken.objects.create(
            user_id="prod_user",
            access_token="prod_access",
            refresh_token="prod_refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            is_test_user=False,
        )
        MockAuthService.return_value.get_valid_token.return_value = token
        MockClient.return_value.post.side_effect = Exception("Boom!")

        out = io.StringIO()
        call_command("create_ml_test_user", stdout=out)
        output = out.getvalue()

        assert "An unexpected error occurred: Boom!" in output

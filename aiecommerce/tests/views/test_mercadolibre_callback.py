import json
from unittest.mock import patch

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from aiecommerce.views.mercadolibre_callback import MercadoLibreCallbackView


class MercadoLibreCallbackViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = MercadoLibreCallbackView.as_view()
        self.url = "/mercadolibre/callback/"  # Assuming a URL, but we'll use RequestFactory directly

    @patch("aiecommerce.views.mercadolibre_callback.MercadoLibreAuthService")
    def test_get_success(self, mock_auth_service_class):
        # Setup mock
        mock_auth_service_instance = mock_auth_service_class.return_value

        # Create request with code
        request = self.factory.get(self.url, {"code": "test_code"})

        # Execute view
        response = self.view(request)
        assert isinstance(response, HttpResponse)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"status": "success", "message": "Mercado Libre account linked successfully."})

        # Verify service call
        mock_auth_service_instance.init_token_from_code.assert_called_once_with(
            code="test_code", redirect_uri=settings.MERCADOLIBRE_REDIRECT_URI
        )

    def test_get_missing_code(self):
        # Create request without code
        request = self.factory.get(self.url)

        # Execute view
        response = self.view(request)
        assert isinstance(response, HttpResponse)

        # Assertions
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"status": "error", "message": "Authorization code not provided."})

    @patch("aiecommerce.views.mercadolibre_callback.MercadoLibreAuthService")
    def test_get_service_failure(self, mock_auth_service_class):
        # Setup mock to raise exception
        mock_auth_service_instance = mock_auth_service_class.return_value
        mock_auth_service_instance.init_token_from_code.side_effect = Exception("Service failure")

        # Create request with code
        request = self.factory.get(self.url, {"code": "test_code"})

        # Execute view
        response = self.view(request)
        assert isinstance(response, HttpResponse)

        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.content), {"status": "error", "message": "Service failure"})

from urllib.parse import parse_qs, urlparse

from django.test import RequestFactory, TestCase, override_settings

from aiecommerce.views.mercadolibre_login import MercadoLibreLoginView


class MercadoLibreLoginViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = MercadoLibreLoginView.as_view()
        self.url = "/mercadolibre/login/"

    @override_settings(
        MERCADOLIBRE_BASE_URL="https://auth.mercadolibre.com.ec",
        MERCADOLIBRE_CLIENT_ID="123456789",
        MERCADOLIBRE_REDIRECT_URI="https://myapp.com/callback",
    )
    def test_redirect_url_construction(self):
        # Create request
        request = self.factory.get(self.url)

        # Execute view
        response = self.view(request)

        # Assertions
        self.assertEqual(response.status_code, 302)

        # Use getattr to avoid Mypy error with HttpResponseBase
        redirect_url = getattr(response, "url")
        parsed_url = urlparse(redirect_url)

        # Check base URL
        self.assertEqual(f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}", "https://auth.mercadolibre.com.ec/authorization")

        # Check query parameters
        query_params = parse_qs(parsed_url.query)
        self.assertEqual(query_params.get("response_type"), ["code"])
        self.assertEqual(query_params.get("client_id"), ["123456789"])
        self.assertEqual(query_params.get("redirect_uri"), ["https://myapp.com/callback"])

    def test_permanent_is_false(self):
        # The view should not be a permanent redirect
        request = self.factory.get(self.url)
        response = self.view(request)
        self.assertEqual(response.status_code, 302)

        view_instance = MercadoLibreLoginView()
        self.assertFalse(view_instance.permanent)

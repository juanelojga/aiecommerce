from urllib.parse import urlencode

from django.conf import settings
from django.views.generic import RedirectView


class MercadoLibreLoginView(RedirectView):
    """
    Redirects the user to the Mercado Libre authorization page.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs) -> str:
        """Construct the full authorization URL for Mercado Libre OAuth.

        Returns:
            The complete authorization URL with query parameters.
        """
        auth_url = f"{settings.MERCADOLIBRE_AUTH_URL}/authorization"
        params = {
            "response_type": "code",
            "client_id": settings.MERCADOLIBRE_CLIENT_ID,
            "redirect_uri": settings.MERCADOLIBRE_REDIRECT_URI,
        }
        return f"{auth_url}?{urlencode(params)}"

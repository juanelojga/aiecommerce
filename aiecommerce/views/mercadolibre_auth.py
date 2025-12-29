import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.views.generic import RedirectView

from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService

logger = logging.getLogger(__name__)


class MercadoLibreLoginView(RedirectView):
    """
    Redirects the user to the Mercado Libre authorization page.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        """Constructs the full authorization URL."""
        auth_url = "https://auth.mercadolibre.com.ec/authorization"
        params = {
            "response_type": "code",
            "client_id": settings.MERCADOLIBRE_CLIENT_ID,
            "redirect_uri": settings.MERCADOLIBRE_REDIRECT_URI,
        }
        return f"{auth_url}?{urlencode(params)}"


class MercadoLibreCallbackView(View):
    """
    Handles the callback from Mercado Libre after user authorization.
    Exchanges the authorization code for an access token.
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        code = request.GET.get("code")
        if not code:
            logger.warning("Mercado Libre callback requested without a code.")
            return JsonResponse({"status": "error", "message": "Authorization code not provided."}, status=400)

        try:
            auth_service = MercadoLibreAuthService()
            auth_service.init_token_from_code(code=code, redirect_uri=settings.MERCADOLIBRE_REDIRECT_URI)
            logger.info("Successfully processed Mercado Libre authorization code.")
            return JsonResponse({"status": "success", "message": "Mercado Libre account linked successfully."})
        except Exception as e:
            logger.exception("Failed to process Mercado Libre authorization code.")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

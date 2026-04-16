from __future__ import annotations

import logging

from celery import shared_task

from aiecommerce.models import MercadoLibreToken
from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl import MercadoLibrePictureUpdateService

logger = logging.getLogger(__name__)


def _get_production_access_token() -> str:
    """Fetch a valid production ML access token via MercadoLibreAuthService."""
    latest = MercadoLibreToken.objects.filter(is_test_user=False).order_by("-created_at").first()
    if latest is None:
        raise MLTokenError("No production Mercado Libre token found.")
    refreshed = MercadoLibreAuthService().get_valid_token(user_id=latest.user_id)
    return refreshed.access_token


@shared_task
def update_ml_listing_pictures_task(product_code: str) -> None:
    """Push the current ProductImage set for product_code to its active ML listing."""
    try:
        listing = MercadoLibreListing.objects.select_related("product_master").get(
            product_master__code=product_code,
            status=MercadoLibreListing.Status.ACTIVE,
        )
    except MercadoLibreListing.DoesNotExist:
        logger.warning("No ACTIVE MercadoLibreListing for product %r; skipping picture update.", product_code)
        return

    access_token = _get_production_access_token()
    client = MercadoLibreClient(access_token=access_token)
    MercadoLibrePictureUpdateService(ml_client=client).update_pictures(listing)

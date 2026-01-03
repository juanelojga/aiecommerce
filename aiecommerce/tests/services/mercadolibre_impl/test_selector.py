from unittest.mock import MagicMock, patch

import pytest
from django.db.models import QuerySet
from model_bakery import baker

from aiecommerce.models.product import ProductImage, ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter
from aiecommerce.services.mercadolibre_impl.selector import ImageCandidateSelector

pytestmark = pytest.mark.django_db


def test_get_pending_image_products_returns_only_eligible_products_without_images():
    """
    Tests that the selector correctly identifies products that are eligible
    and have no associated ProductImage objects.
    """
    # Arrange
    # 1. Create products
    eligible_with_images = baker.make(ProductMaster)
    baker.make(ProductImage, product=eligible_with_images)

    eligible_without_images = baker.make(ProductMaster)

    # This product will not be returned by the mock filter, so it shouldn't be in the final result
    baker.make(ProductMaster)

    all_eligible_products = ProductMaster.objects.filter(
        pk__in=[
            eligible_with_images.pk,
            eligible_without_images.pk,
        ]
    )

    # 2. Mock the MercadoLibreFilter
    mock_filter = MagicMock(spec=MercadoLibreFilter)
    mock_filter.get_eligible_products.return_value = all_eligible_products

    # Act
    # 3. Instantiate the selector with the mock filter and get pending products
    with patch("aiecommerce.services.mercadolibre_impl.selector.logger") as mock_logger:
        selector = ImageCandidateSelector(ml_filter=mock_filter)
        pending_products = selector.get_pending_image_products()

    # Assert
    # 4. Verify the results
    assert isinstance(pending_products, QuerySet)
    mock_filter.get_eligible_products.assert_called_once()

    # It should only return the product without associated images
    assert pending_products.count() == 1
    product = pending_products.first()
    assert product is not None
    assert product.pk == eligible_without_images.pk

    # 5. Verify logging
    mock_logger.info.assert_called_once_with("Found 1 products pending image search.")

from unittest.mock import MagicMock

import pytest
from django.db.models import QuerySet
from model_bakery import baker

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter
from aiecommerce.services.mercadolibre_impl.selector import ImageCandidateSelector

pytestmark = pytest.mark.django_db


def test_get_pending_image_products_returns_only_eligible_products_without_images():
    """
    Tests that the selector correctly identifies products that are eligible
    and are missing an image URL.
    """
    # Arrange
    # 1. Create a base set of products that our mock filter will return
    eligible_with_url = baker.make(ProductMaster, image_url="http://example.com/image.jpg")
    eligible_with_null_url = baker.make(ProductMaster, image_url=None)
    eligible_with_empty_url = baker.make(ProductMaster, image_url="")

    # This product will not be returned by the mock filter, so it shouldn't be in the final result
    baker.make(ProductMaster, image_url=None)

    all_eligible_products = ProductMaster.objects.filter(
        pk__in=[
            eligible_with_url.pk,
            eligible_with_null_url.pk,
            eligible_with_empty_url.pk,
        ]
    )

    # 2. Mock the MercadoLibreFilter
    mock_filter = MagicMock(spec=MercadoLibreFilter)
    mock_filter.get_eligible_products.return_value = all_eligible_products

    # Act
    # 3. Instantiate the selector with the mock filter and get pending products
    selector = ImageCandidateSelector(ml_filter=mock_filter)
    pending_products = selector.get_pending_image_products()

    # Assert
    # 4. Verify the results
    assert isinstance(pending_products, QuerySet)
    mock_filter.get_eligible_products.assert_called_once()

    # It should only return the two products without an image URL from the eligible list
    assert pending_products.count() == 2

    pending_pks = {product.pk for product in pending_products}
    assert eligible_with_null_url.pk in pending_pks
    assert eligible_with_empty_url.pk in pending_pks
    assert eligible_with_url.pk not in pending_pks

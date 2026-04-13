"""Tests for POST /api/v1/products/{id}/refresh-images/."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from aiecommerce.tests.factories import ProductMasterFactory

API_KEY = "test-secret-key"

pytestmark = [pytest.mark.django_db]

_api_settings = override_settings(API_KEY=API_KEY, API_ALLOWED_IPS=[])


def _url(pk: int) -> str:
    return f"/api/v1/products/{pk}/refresh-images/"


def _auth_client() -> APIClient:
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=API_KEY)
    return client


@_api_settings
@patch("aiecommerce.api.v1.views.product.refresh_product_images")
def test_refresh_images_returns_202_with_task_id(mock_refresh):
    mock_refresh.return_value = "task-abc"
    product = ProductMasterFactory(code="API-1")

    response = _auth_client().post(_url(product.pk))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data == {"task_id": "task-abc", "product_code": "API-1"}
    mock_refresh.assert_called_once_with("API-1")


@_api_settings
@patch("aiecommerce.api.v1.views.product.refresh_product_images")
def test_refresh_images_returns_404_for_unknown_product(mock_refresh):
    response = _auth_client().post(_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_refresh.assert_not_called()


@_api_settings
@patch("aiecommerce.api.v1.views.product.refresh_product_images")
def test_refresh_images_requires_authentication(mock_refresh):
    product = ProductMasterFactory(code="API-2")

    response = APIClient().post(_url(product.pk))

    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    mock_refresh.assert_not_called()


@_api_settings
@patch("aiecommerce.api.v1.views.product.refresh_product_images")
def test_refresh_images_rejects_get(mock_refresh):
    product = ProductMasterFactory(code="API-3")

    response = _auth_client().get(_url(product.pk))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    mock_refresh.assert_not_called()

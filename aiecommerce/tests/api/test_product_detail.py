"""Tests for GET /api/v1/products/{id}/ — Product Technical Details endpoint."""

from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from aiecommerce.tests.factories import ProductMasterFactory

API_KEY = "test-secret-key"
PRODUCTS_URL = "/api/v1/products/"

pytestmark = [
    pytest.mark.django_db,
]

_api_settings = override_settings(API_KEY=API_KEY, API_ALLOWED_IPS=[])


def _auth_client() -> APIClient:
    """Return an APIClient pre-configured with a valid API key."""
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=API_KEY)
    return client


def _detail_url(product_id: int) -> str:
    """Return the detail URL for a given product ID."""
    return f"{PRODUCTS_URL}{product_id}/"


class TestProductDetailEndpoint:
    """Integration tests for the product technical details retrieve endpoint."""

    # -- Basic response -------------------------------------------------------

    @_api_settings
    def test_retrieve_product_returns_200(self) -> None:
        """GET /api/v1/products/{id}/ returns 200 for an existing product."""
        product = ProductMasterFactory(is_active=True)
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert response.status_code == status.HTTP_200_OK

    @_api_settings
    def test_response_contains_all_technical_fields(self) -> None:
        """The response includes every field in the technical profile."""
        product = ProductMasterFactory(
            code="ABC123",
            sku="MPN-001",
            normalized_name="HP ProBook 440 G10",
            model_name="ProBook 440 G10",
            description="Business laptop with Intel i7.",
            seo_title="HP ProBook 440 G10 Business Laptop",
            seo_description="A powerful business laptop featuring Intel i7.",
            price="1299.99",
            category="notebook",
            gtin="1234567890123",
            specs={"processor": "Intel i7-1355U", "ram": "16GB", "tdp": "15W"},
            image_url="https://example.com/image.jpg",
            is_active=True,
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
            stock_gye_norte="SI",
            stock_gye_sur="NO",
        )
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        data = response.data
        assert data["id"] == product.pk
        assert data["code"] == "ABC123"
        assert data["sku"] == "MPN-001"
        assert data["normalized_name"] == "HP ProBook 440 G10"
        assert data["model_name"] == "ProBook 440 G10"
        assert data["description"] == "Business laptop with Intel i7."
        assert data["seo_title"] == "HP ProBook 440 G10 Business Laptop"
        assert data["seo_description"] == "A powerful business laptop featuring Intel i7."
        assert data["price"] == "1299.99"
        assert data["category"] == "notebook"
        assert data["gtin"] == "1234567890123"
        assert data["specs"] == {"processor": "Intel i7-1355U", "ram": "16GB", "tdp": "15W"}
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["total_available_stock"] == 2  # colon + gye_norte

    # -- specs field ----------------------------------------------------------

    @_api_settings
    def test_specs_json_field_returned_as_dict(self) -> None:
        """The specs JSONField is serialized as a JSON object (dict)."""
        specs_data = {
            "socket": "LGA1700",
            "tdp": "125W",
            "dimensions": {"height_mm": 37.5, "width_mm": 150},
        }
        product = ProductMasterFactory(specs=specs_data, is_active=True)
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert isinstance(response.data["specs"], dict)
        assert response.data["specs"] == specs_data

    @_api_settings
    def test_empty_specs_returned_as_empty_dict(self) -> None:
        """Products with no specs return an empty dict."""
        product = ProductMasterFactory(specs={}, is_active=True)
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert response.data["specs"] == {}

    # -- Stock computation ----------------------------------------------------

    @_api_settings
    def test_total_available_stock_computed_correctly(self) -> None:
        """total_available_stock mirrors the model property logic."""
        product = ProductMasterFactory(
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
            is_active=True,
        )
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert response.data["total_available_stock"] == 4

    @_api_settings
    def test_total_available_stock_zero_when_principal_unavailable(self) -> None:
        """Stock is 0 when stock_principal is not 'SI'."""
        product = ProductMasterFactory(
            stock_principal="NO",
            stock_colon="SI",
            stock_sur="SI",
            is_active=True,
        )
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert response.data["total_available_stock"] == 0

    # -- Error cases ----------------------------------------------------------

    @_api_settings
    def test_retrieve_nonexistent_product_returns_404(self) -> None:
        """GET /api/v1/products/{id}/ returns 404 for an unknown ID."""
        client = _auth_client()

        response = client.get(_detail_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @_api_settings
    def test_retrieve_requires_authentication(self) -> None:
        """Unauthenticated requests are rejected with 403."""
        product = ProductMasterFactory(is_active=True)
        client = APIClient()  # No credentials

        response = client.get(_detail_url(product.pk))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # -- Edge cases -----------------------------------------------------------

    @_api_settings
    def test_inactive_product_is_still_retrievable(self) -> None:
        """Agents may need specs for inactive products; retrieve should not filter by is_active."""
        product = ProductMasterFactory(
            is_active=False,
            specs={"socket": "AM5"},
        )
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["specs"] == {"socket": "AM5"}

    @_api_settings
    def test_response_is_not_paginated(self) -> None:
        """The detail endpoint returns a flat object, not a paginated wrapper."""
        product = ProductMasterFactory(is_active=True)
        client = _auth_client()

        response = client.get(_detail_url(product.pk))

        assert "results" not in response.data
        assert "count" not in response.data
        assert "id" in response.data

"""Tests for GET /api/v1/products/ — Product Catalog list endpoint."""

from __future__ import annotations

import datetime

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


class TestProductListEndpoint:
    """Integration tests for the product catalog list endpoint."""

    # -- Basic response -------------------------------------------------------

    @_api_settings
    def test_list_products_returns_200(self) -> None:
        """GET /api/v1/products/ returns 200 with paginated results."""
        ProductMasterFactory(is_active=True)
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data

    @_api_settings
    def test_response_contains_expected_fields(self) -> None:
        """Each product in the response includes the specified fields."""
        ProductMasterFactory(
            code="ABC123",
            sku="MPN-001",
            normalized_name="Test Laptop",
            price="999.99",
            category="notebook",
            is_active=True,
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
        )
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        assert response.status_code == status.HTTP_200_OK
        product = response.data["results"][0]
        expected_fields = {"id", "code", "sku", "normalized_name", "price", "category", "total_available_stock"}
        assert expected_fields == set(product.keys())

    # -- total_available_stock annotation --------------------------------------

    @_api_settings
    def test_total_available_stock_all_branches_available(self) -> None:
        """Stock annotation counts branches when stock_principal is SI."""
        ProductMasterFactory(
            is_active=True,
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="SI",
            stock_gye_norte="SI",
            stock_gye_sur="SI",
        )
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        product = response.data["results"][0]
        assert product["total_available_stock"] == 4

    @_api_settings
    def test_total_available_stock_principal_not_si(self) -> None:
        """Stock is 0 when stock_principal is not SI, regardless of branches."""
        ProductMasterFactory(
            is_active=True,
            stock_principal="NO",
            stock_colon="SI",
            stock_sur="SI",
        )
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        product = response.data["results"][0]
        assert product["total_available_stock"] == 0

    @_api_settings
    def test_annotation_matches_property(self) -> None:
        """DB annotation result matches the Python @property for several cases."""
        p1 = ProductMasterFactory(
            is_active=True,
            stock_principal="SI",
            stock_colon="SI",
            stock_sur="NO",
            stock_gye_norte=None,
            stock_gye_sur="SI",
        )
        p2 = ProductMasterFactory(
            is_active=True,
            stock_principal="NO",
            stock_colon="SI",
        )
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        results = {r["id"]: r["total_available_stock"] for r in response.data["results"]}
        assert results[p1.id] == p1.total_available_stock
        assert results[p2.id] == p2.total_available_stock

    # -- Filtering: category --------------------------------------------------

    @_api_settings
    def test_filter_by_category(self) -> None:
        """?category=notebook returns only products in that category (case-insensitive)."""
        ProductMasterFactory(is_active=True, category="notebook")
        ProductMasterFactory(is_active=True, category="monitor")
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"category": "NOTEBOOK"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["category"] == "notebook"

    # -- Filtering: has_stock -------------------------------------------------

    @_api_settings
    def test_filter_has_stock_true(self) -> None:
        """?has_stock=true returns only products with total_available_stock > 0."""
        ProductMasterFactory(is_active=True, stock_principal="SI", stock_colon="SI")
        ProductMasterFactory(is_active=True, stock_principal="NO")
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"has_stock": "true"})

        assert response.data["count"] == 1
        assert response.data["results"][0]["total_available_stock"] > 0

    @_api_settings
    def test_filter_has_stock_false(self) -> None:
        """?has_stock=false returns only products with total_available_stock == 0."""
        ProductMasterFactory(is_active=True, stock_principal="SI", stock_colon="SI")
        ProductMasterFactory(is_active=True, stock_principal="NO")
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"has_stock": "false"})

        assert response.data["count"] == 1
        assert response.data["results"][0]["total_available_stock"] == 0

    # -- Filtering: is_active -------------------------------------------------

    @_api_settings
    def test_filter_is_active_false(self) -> None:
        """?is_active=false returns only inactive products."""
        ProductMasterFactory(is_active=True)
        ProductMasterFactory(is_active=False)
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"is_active": "false"})

        assert response.data["count"] == 1

    @_api_settings
    def test_filter_is_active_true(self) -> None:
        """?is_active=true returns only active products."""
        ProductMasterFactory(is_active=True)
        ProductMasterFactory(is_active=False)
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"is_active": "true"})

        assert response.data["count"] == 1

    # -- Ordering -------------------------------------------------------------

    @_api_settings
    def test_ordering_by_last_bundled_date_ascending(self) -> None:
        """Default ordering is last_bundled_date ascending (oldest first)."""
        old = ProductMasterFactory(
            is_active=True,
            last_bundled_date=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        )
        new = ProductMasterFactory(
            is_active=True,
            last_bundled_date=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        )
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"ordering": "last_bundled_date"})

        results = response.data["results"]
        assert results[0]["id"] == old.id
        assert results[1]["id"] == new.id

    # -- Authentication -------------------------------------------------------

    @override_settings(API_KEY="real-key", API_ALLOWED_IPS=[])
    def test_unauthenticated_request_returns_403(self) -> None:
        """A request without a valid API key is rejected."""
        ProductMasterFactory(is_active=True)
        client = APIClient()  # no credentials

        response = client.get(PRODUCTS_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # -- Empty results --------------------------------------------------------

    @_api_settings
    def test_empty_catalog_returns_empty_list(self) -> None:
        """When no products exist, the endpoint returns an empty page."""
        client = _auth_client()

        response = client.get(PRODUCTS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["results"] == []

    # -- Combined filters -----------------------------------------------------

    @_api_settings
    def test_combined_filters(self) -> None:
        """Filters can be combined: category + has_stock + is_active."""
        ProductMasterFactory(is_active=True, category="CPU", stock_principal="SI", stock_colon="SI")
        ProductMasterFactory(is_active=True, category="CPU", stock_principal="NO")
        ProductMasterFactory(is_active=False, category="CPU", stock_principal="SI", stock_colon="SI")
        ProductMasterFactory(is_active=True, category="RAM", stock_principal="SI", stock_colon="SI")
        client = _auth_client()

        response = client.get(PRODUCTS_URL, {"category": "CPU", "has_stock": "true", "is_active": "true"})

        assert response.data["count"] == 1
        product = response.data["results"][0]
        assert product["category"] == "CPU"
        assert product["total_available_stock"] > 0

from typing import List, Optional, cast

import pytest

from aiecommerce.models import ProductMaster, ProductRawPDF
from aiecommerce.services.normalization_impl.matcher import FuzzyMatcher
from aiecommerce.services.normalization_impl.service import ProductNormalizationService
from aiecommerce.tests.factories import (
    ProductMasterFactory,
    ProductRawWebFactory,
)

pytestmark = pytest.mark.django_db


class DummyMatch:
    distributor_price: Optional[float]
    category_header: Optional[str]

    def __init__(self, price: Optional[float] = None, category: Optional[str] = None) -> None:
        self.distributor_price = price
        self.category_header = category


class DummyMatcher(FuzzyMatcher):
    def __init__(self, price: Optional[float] = None, category: Optional[str] = None) -> None:
        self._match: Optional[DummyMatch] = DummyMatch(price=price, category=category) if (price is not None or category is not None) else None

    # Match FuzzyMatcher signature: (str, List[ProductRawPDF], int) -> Optional[ProductRawPDF]
    def find_best_match(
        self,
        target_description: str,
        candidates: List[ProductRawPDF],
        threshold: int = 90,
    ) -> Optional[ProductRawPDF]:
        # We only need to return an object with the same attributes used by the service.
        # Use typing.cast so mypy accepts DummyMatch as ProductRawPDF for testing purposes.
        return cast(Optional[ProductRawPDF], self._match)


def _service_with_match(price: Optional[float] = None, category: Optional[str] = None) -> ProductNormalizationService:
    return ProductNormalizationService(matcher=DummyMatcher(price=price, category=category))


def test_creates_product_master_with_stock_fields_from_web():
    session_id = "S-001"

    web = ProductRawWebFactory(
        scrape_session_id=session_id,
        distributor_code="SKU-123",
        raw_description="Awesome Widget",
        stock_principal="Si",
        stock_colon="No",
        stock_sur="Si",
        stock_gye_norte="No",
        stock_gye_sur="Si",
    )

    service = _service_with_match(price=123.45, category="Widgets")
    result = service.normalize_products(scrape_session_id=session_id)

    assert result["processed_count"] == 1
    assert result["created_count"] == 1
    assert result["updated_count"] == 0
    assert result["inactive_count"] == 0

    pm = ProductMaster.objects.get(code=web.distributor_code)
    assert pm.description == web.raw_description
    assert pm.stock_principal == "Si"
    assert pm.stock_colon == "No"
    assert pm.stock_sur == "Si"
    assert pm.stock_gye_norte == "No"
    assert pm.stock_gye_sur == "Si"
    # also ensure price/category can be sourced from the matcher
    assert pm.price is not None
    assert pm.category == "Widgets"


def test_updates_product_master_when_stock_values_change():
    # Existing master with old stock values
    master = ProductMasterFactory(
        code="SKU-999",
        stock_principal="No",
        stock_colon="No",
        stock_sur="No",
        stock_gye_norte="No",
        stock_gye_sur="No",
        is_active=True,
    )

    session_id = "S-002"
    # New web scrape with changed stock flags
    web = ProductRawWebFactory(
        scrape_session_id=session_id,
        distributor_code=master.code,
        raw_description="Updated Desc",
        stock_principal="Si",
        stock_colon="Si",
        stock_sur="No",
        stock_gye_norte="Si",
        stock_gye_sur="No",
    )

    service = _service_with_match()  # price/category not relevant for this test
    result = service.normalize_products(scrape_session_id=session_id)

    assert result["processed_count"] == 1
    assert result["created_count"] == 0
    assert result["updated_count"] == 1
    assert result["inactive_count"] >= 0  # could be 0 or more depending on existing data

    master.refresh_from_db()
    assert master.description == web.raw_description
    assert master.stock_principal == "Si"
    assert master.stock_colon == "Si"
    assert master.stock_sur == "No"
    assert master.stock_gye_norte == "Si"
    assert master.stock_gye_sur == "No"
    assert master.is_active is True


def test_marks_missing_products_inactive_after_run():
    # Two products exist; only one appears in the new session
    present = ProductMasterFactory(code="SKU-A", is_active=True)
    missing = ProductMasterFactory(code="SKU-B", is_active=True)

    session_id = "S-003"
    ProductRawWebFactory(
        scrape_session_id=session_id,
        distributor_code=present.code,
        raw_description="Present product",
        stock_principal="Si",
    )

    service = _service_with_match()
    result = service.normalize_products(scrape_session_id=session_id)

    assert result["processed_count"] == 1
    assert result["inactive_count"] == 1

    missing.refresh_from_db()
    present.refresh_from_db()
    assert missing.is_active is False
    assert present.is_active is True

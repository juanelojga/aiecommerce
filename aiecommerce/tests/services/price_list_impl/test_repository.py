import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from aiecommerce.models.product import ProductRawPDF
from aiecommerce.services.price_list_impl.repository import ProductRawRepository
from aiecommerce.tests.factories import ProductRawPDFFactory


@pytest.mark.django_db
def test_save_bulk_with_empty_input_does_nothing_and_returns_zero() -> None:
    # Preload some data to ensure early return does not truncate
    ProductRawPDFFactory.create_batch(2)
    initial_count = ProductRawPDF.objects.count()

    repo = ProductRawRepository()
    created = repo.save_bulk([])

    assert created == 0
    assert ProductRawPDF.objects.count() == initial_count


@pytest.mark.django_db
def test_save_bulk_truncates_then_inserts_and_sets_uniform_created_at(monkeypatch: pytest.MonkeyPatch) -> None:
    # Existing rows should be removed
    ProductRawPDFFactory.create_batch(3)

    fixed_now = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

    def _fake_now() -> datetime.datetime:
        return fixed_now

    # Patch timezone.now used inside repository
    monkeypatch.setattr(timezone, "now", _fake_now)

    payload = [
        {
            "raw_description": "Item A",
            "distributor_price": Decimal("10.50"),
            "category_header": "Cat 1",
        },
        {
            "raw_description": "Item B",
            "distributor_price": Decimal("99.99"),
            "category_header": "Cat 2",
        },
    ]

    repo = ProductRawRepository()
    created = repo.save_bulk(payload)

    # returns number of created rows
    assert created == 2

    # old rows removed, only new rows present
    rows = list(ProductRawPDF.objects.order_by("id"))
    assert len(rows) == 2
    assert {r.raw_description for r in rows} == {"Item A", "Item B"}

    # created_at is set uniformly to fixed_now
    assert all(r.created_at == fixed_now for r in rows)


@pytest.mark.django_db
def test_save_bulk_accepts_large_input_counts_correctly() -> None:
    # Generate a moderate batch to ensure count matches length
    data = [
        {
            "raw_description": f"Row {i}",
            "distributor_price": Decimal("1.00") * (i + 1),
            "category_header": "Bulk",
        }
        for i in range(25)
    ]

    repo = ProductRawRepository()
    created = repo.save_bulk(data)

    assert created == 25
    assert ProductRawPDF.objects.count() == 25

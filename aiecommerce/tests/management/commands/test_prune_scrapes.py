import io
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from django.utils import timezone

from aiecommerce.management.commands.prune_scrapes import Command as PruneCommand
from aiecommerce.models.product import ProductRawWeb


def _make_command() -> Any:
    # Cast to Any to avoid OutputWrapper type issues in tests
    cmd = cast(Any, PruneCommand())
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    return cmd


@pytest.mark.django_db
def test_prunes_records_older_than_48_hours(monkeypatch):
    # Freeze timezone.now()
    fixed_now = timezone.make_aware(datetime(2025, 1, 10, 12, 0, 0))
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    # Create three records; created_at is auto_now_add, so update after creation
    old_obj = ProductRawWeb.objects.create(distributor_code="OLD")
    edge_obj = ProductRawWeb.objects.create(distributor_code="EDGE")
    new_obj = ProductRawWeb.objects.create(distributor_code="NEW")

    ProductRawWeb.objects.filter(id=old_obj.id).update(created_at=fixed_now - timedelta(hours=49))
    ProductRawWeb.objects.filter(id=edge_obj.id).update(created_at=fixed_now - timedelta(hours=48))
    ProductRawWeb.objects.filter(id=new_obj.id).update(created_at=fixed_now - timedelta(hours=1))

    cmd = _make_command()
    cmd.handle()

    out = cmd.stdout.getvalue()
    assert "Starting to prune old scrape records" in out
    assert "Successfully pruned 1 old scrape records." in out

    remaining = list(ProductRawWeb.objects.order_by("distributor_code").values_list("distributor_code", flat=True))
    assert remaining == ["EDGE", "NEW"]


@pytest.mark.django_db
def test_no_records_to_prune(monkeypatch):
    fixed_now = timezone.make_aware(datetime(2025, 1, 10, 12, 0, 0))
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    # Create only recent records
    a = ProductRawWeb.objects.create(distributor_code="A")
    b = ProductRawWeb.objects.create(distributor_code="B")
    ProductRawWeb.objects.filter(id=a.id).update(created_at=fixed_now - timedelta(hours=2))
    ProductRawWeb.objects.filter(id=b.id).update(created_at=fixed_now - timedelta(hours=12))

    cmd = _make_command()
    cmd.handle()

    out = cmd.stdout.getvalue()
    assert "Starting to prune old scrape records" in out
    assert "No old scrape records to prune." in out

    assert ProductRawWeb.objects.count() == 2

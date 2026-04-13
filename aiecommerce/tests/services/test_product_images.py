"""Tests for the product_images service (refresh + S3 cleanup)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from aiecommerce.models.product import ProductImage, ProductMaster
from aiecommerce.services.product_images import (
    _delete_s3_objects_for_product,
    refresh_product_images,
)
from aiecommerce.tests.factories import ProductImageFactory, ProductMasterFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_boto3_client():
    with patch("aiecommerce.services.product_images.boto3.client") as mock:
        yield mock


@pytest.fixture
def mock_task_delay():
    with patch(
        "aiecommerce.services.product_images.process_highres_image_task.delay"
    ) as mock:
        result = MagicMock()
        result.id = "task-xyz"
        mock.return_value = result
        yield mock


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    AWS_S3_REGION_NAME="us-east-1",
)
def test_refresh_product_images_deletes_rows_and_enqueues(mock_boto3_client, mock_task_delay):
    product = ProductMasterFactory(code="REFRESH-1")
    ProductImageFactory.create_batch(3, product=product)

    s3_client = mock_boto3_client.return_value
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": [{"Key": "products/REFRESH-1/a.jpg"}]}]
    s3_client.get_paginator.return_value = paginator
    s3_client.delete_objects.return_value = {"Deleted": [{"Key": "products/REFRESH-1/a.jpg"}]}

    task_id = refresh_product_images("REFRESH-1")

    assert task_id == "task-xyz"
    assert ProductImage.objects.filter(product=product).count() == 0
    mock_task_delay.assert_called_once_with("REFRESH-1")
    paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="products/REFRESH-1/")
    s3_client.delete_objects.assert_called_once()


def test_refresh_product_images_raises_for_missing_product(mock_task_delay):
    with pytest.raises(ProductMaster.DoesNotExist):
        refresh_product_images("NOPE")
    mock_task_delay.assert_not_called()


@override_settings(AWS_STORAGE_BUCKET_NAME="")
def test_delete_s3_objects_skips_when_bucket_not_configured(mock_boto3_client, caplog):
    caplog.set_level("WARNING")
    count = _delete_s3_objects_for_product("ANY")
    assert count == 0
    mock_boto3_client.assert_not_called()
    assert "AWS_STORAGE_BUCKET_NAME not configured" in caplog.text


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    AWS_S3_REGION_NAME="us-east-1",
)
def test_delete_s3_objects_handles_empty_prefix(mock_boto3_client):
    s3_client = mock_boto3_client.return_value
    paginator = MagicMock()
    paginator.paginate.return_value = [{}]
    s3_client.get_paginator.return_value = paginator

    count = _delete_s3_objects_for_product("EMPTY")

    assert count == 0
    s3_client.delete_objects.assert_not_called()


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    AWS_S3_REGION_NAME="us-east-1",
)
def test_delete_s3_objects_batches_in_chunks_of_1000(mock_boto3_client):
    s3_client = mock_boto3_client.return_value
    contents = [{"Key": f"products/BIG/img_{i}.jpg"} for i in range(2500)]
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": contents}]
    s3_client.get_paginator.return_value = paginator
    s3_client.delete_objects.side_effect = lambda Bucket, Delete: {"Deleted": Delete["Objects"]}

    count = _delete_s3_objects_for_product("BIG")

    assert count == 2500
    assert s3_client.delete_objects.call_count == 3
    # First two batches = 1000, last = 500
    sizes = [len(call.kwargs["Delete"]["Objects"]) for call in s3_client.delete_objects.call_args_list]
    assert sizes == [1000, 1000, 500]


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    AWS_S3_REGION_NAME="us-east-1",
)
def test_delete_s3_objects_logs_per_key_errors(mock_boto3_client, caplog):
    caplog.set_level("ERROR")
    s3_client = mock_boto3_client.return_value
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Contents": [{"Key": "products/E/a.jpg"}, {"Key": "products/E/b.jpg"}]}
    ]
    s3_client.get_paginator.return_value = paginator
    s3_client.delete_objects.return_value = {
        "Deleted": [{"Key": "products/E/a.jpg"}],
        "Errors": [{"Key": "products/E/b.jpg", "Message": "AccessDenied"}],
    }

    count = _delete_s3_objects_for_product("E")

    assert count == 1
    assert "Failed to delete S3 key products/E/b.jpg" in caplog.text

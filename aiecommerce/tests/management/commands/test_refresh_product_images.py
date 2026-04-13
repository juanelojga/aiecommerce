"""Tests for the refresh_product_images management command."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from aiecommerce.tests.factories import ProductMasterFactory

pytestmark = pytest.mark.django_db


@patch("aiecommerce.management.commands.refresh_product_images.refresh_product_images")
def test_command_invokes_service_and_prints_task_id(mock_refresh, capsys):
    ProductMasterFactory(code="CLI-1")
    mock_refresh.return_value = "task-abc"

    call_command("refresh_product_images", "CLI-1")

    mock_refresh.assert_called_once_with("CLI-1")
    captured = capsys.readouterr()
    assert "Queued image refresh for CLI-1" in captured.out
    assert "task-abc" in captured.out


def test_command_raises_command_error_for_missing_product():
    with pytest.raises(CommandError, match="not found"):
        call_command("refresh_product_images", "MISSING")


def test_command_requires_product_code_argument():
    with pytest.raises(CommandError):
        call_command("refresh_product_images")

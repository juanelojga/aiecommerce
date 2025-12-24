import logging
from typing import TYPE_CHECKING, List, cast
from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.services.scrape_tecnomega_impl.persister import ProductPersister

if TYPE_CHECKING:
    # Only for type checking; avoids importing heavy model at runtime
    from aiecommerce.models.product import ProductRawWeb


class DummyProduct:
    pass


class TestProductPersister:
    def test_save_bulk_no_products_returns_empty_and_logs(self, caplog):
        persister = ProductPersister(batch_size=50)

        with caplog.at_level(logging.INFO):
            result = persister.save_bulk([])

        assert result == []
        # Ensure an info message about no products is logged
        assert any("No products to persist." in rec.getMessage() for rec in caplog.records)

    def test_save_bulk_success_uses_transaction_and_bulk_create(self, caplog):
        persister = ProductPersister(batch_size=25)

        # Annotate as List[ProductRawWeb] for type checking; at runtime we patch the model
        products = cast("List[ProductRawWeb]", [DummyProduct(), DummyProduct()])

        # Patch ProductRawWeb and transaction.atomic within the persister module
        with (
            patch("aiecommerce.services.scrape_tecnomega_impl.persister.ProductRawWeb") as ProductRawWebMock,
            patch("aiecommerce.services.scrape_tecnomega_impl.persister.transaction") as transaction_mock,
            caplog.at_level(logging.INFO),
        ):
            # Configure the mocked manager and atomic context manager
            bulk_create_mock = MagicMock()
            ProductRawWebMock.objects.bulk_create = bulk_create_mock

            cm = MagicMock()
            cm.__enter__.return_value = None
            cm.__exit__.return_value = None
            transaction_mock.atomic.return_value = cm

            result = persister.save_bulk(products)

        # Returned list should be the same object reference
        assert result is products

        # Assert transaction.atomic was called and used as a context manager
        transaction_mock.atomic.assert_called_once_with()
        assert cm.__enter__.called and cm.__exit__.called

        # bulk_create should be called with our products and batch_size
        bulk_create_mock.assert_called_once_with(products, batch_size=25)

        # Info logs about persisting and success
        messages = [rec.getMessage() for rec in caplog.records]
        assert any("Persisting 2 products in batches of 25." in m for m in messages)
        assert any("Successfully saved 2 products to the database." in m for m in messages)

    def test_save_bulk_logs_error_and_reraises(self, caplog):
        persister = ProductPersister(batch_size=10)
        products = cast("List[ProductRawWeb]", [DummyProduct()])

        with (
            patch("aiecommerce.services.scrape_tecnomega_impl.persister.ProductRawWeb") as ProductRawWebMock,
            patch("aiecommerce.services.scrape_tecnomega_impl.persister.transaction") as transaction_mock,
            caplog.at_level(logging.ERROR),
        ):
            # Configure transaction context manager
            cm = MagicMock()
            cm.__enter__.return_value = None
            cm.__exit__.return_value = None
            transaction_mock.atomic.return_value = cm

            # Make bulk_create raise an arbitrary exception
            ProductRawWebMock.objects.bulk_create.side_effect = RuntimeError("DB down")

            with pytest.raises(RuntimeError):
                persister.save_bulk(products)

        # Ensure an error was logged with our message fragment
        assert any("Database error during bulk creation" in rec.getMessage() for rec in caplog.records)

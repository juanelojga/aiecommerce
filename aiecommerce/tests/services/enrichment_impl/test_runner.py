from unittest.mock import MagicMock

import pytest

from aiecommerce.services.enrichment_impl.exceptions import EnrichmentError
from aiecommerce.services.enrichment_impl.runner import EnrichmentRunner
from aiecommerce.tests.factories import ProductMasterFactory


class _SpecStub:
    def __init__(self, data: dict):
        self._data = data

    def model_dump(self, exclude_none: bool = False):  # mimic pydantic API used by the runner
        return self._data


@pytest.mark.django_db
def test_process_product_success_dry_run_true(caplog):
    product = ProductMasterFactory(specs=None)

    # Mock service to return a stub with model_dump
    service = MagicMock()
    expected_specs = {"power": "500W", "voltage": "110V"}
    service.enrich_product.return_value = _SpecStub(expected_specs)

    runner = EnrichmentRunner(service=service, model_name="test-model")

    success, specs = runner.process_product(product, dry_run=True)

    # Assert service called with expected payload
    service.enrich_product.assert_called_once()
    called_payload, called_model = service.enrich_product.call_args[0]
    assert called_payload["code"] == product.code
    assert called_payload["description"] == product.description
    assert called_payload["category"] == product.category
    assert called_model == "test-model"

    # Assert return values
    assert success is True
    assert specs == expected_specs

    # In-memory object updated
    assert product.specs == expected_specs

    # Not persisted when dry_run=True
    product.refresh_from_db()
    # Factory may set default {} on specs; ensure it didn't persist expected specs
    assert product.specs != expected_specs


@pytest.mark.django_db
def test_process_product_success_persists_and_uses_update_fields():
    product = ProductMasterFactory(specs=None)

    service = MagicMock()
    expected_specs = {"battery": "2200mAh"}
    service.enrich_product.return_value = _SpecStub(expected_specs)

    runner = EnrichmentRunner(service=service, model_name="gpt-model")
    # Spy by wrapping the bound save method
    from unittest.mock import patch

    with patch.object(product, "save", wraps=product.save) as save_spy:
        success, specs = runner.process_product(product, dry_run=False)

        assert success is True
        assert specs == expected_specs
        assert product.specs == expected_specs

        # Ensure save called once with specific update_fields
        save_spy.assert_called_once()
        kwargs = save_spy.call_args.kwargs
        assert kwargs.get("update_fields") == ["specs"]


@pytest.mark.django_db
def test_process_product_no_data_returns_false_and_logs_warning(caplog):
    product = ProductMasterFactory(specs=None)

    service = MagicMock()
    service.enrich_product.return_value = None

    runner = EnrichmentRunner(service=service, model_name="any-model")

    with caplog.at_level("WARNING"):
        success, specs = runner.process_product(product, dry_run=False)

    assert success is False
    assert specs is None
    # Verify warning mention
    assert any("Failed to extract specs" in rec.message for rec in caplog.records)


@pytest.mark.django_db
def test_process_product_handles_enrichment_error_logs_and_returns_false(caplog):
    product = ProductMasterFactory(specs=None)

    service = MagicMock()
    service.enrich_product.side_effect = EnrichmentError("service failed")

    runner = EnrichmentRunner(service=service, model_name="any-model")

    with caplog.at_level("ERROR"):
        success, specs = runner.process_product(product, dry_run=False)

    assert success is False
    assert specs is None
    assert any("Service Error" in rec.message for rec in caplog.records)


@pytest.mark.django_db
def test_process_product_handles_unexpected_exception_logs_and_returns_false(caplog):
    product = ProductMasterFactory(specs=None)

    service = MagicMock()
    service.enrich_product.side_effect = ValueError("boom")

    runner = EnrichmentRunner(service=service, model_name="any-model")

    with caplog.at_level("ERROR"):
        success, specs = runner.process_product(product, dry_run=False)

    assert success is False
    assert specs is None
    assert any("An unexpected error occurred" in rec.message for rec in caplog.records)

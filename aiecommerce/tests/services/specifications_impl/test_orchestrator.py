from unittest.mock import MagicMock

import pytest

from aiecommerce.services.specifications_impl.exceptions import EnrichmentError
from aiecommerce.services.specifications_impl.orchestrator import ProductSpecificationsOrchestrator
from aiecommerce.services.specifications_impl.schemas import GenericSpecs
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestProductSpecificationsOrchestrator:
    def test_process_product_success_with_save(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        extracted_specs = GenericSpecs(model_name="Test Model", normalized_name="Test Brand Test Model", summary="Extracted Summary")
        mock_service.enrich_product.return_value = extracted_specs

        success, result = orchestrator.process_product(product, dry_run=False)

        assert success is True
        # result is model_dump(exclude_none=True)
        expected_result = extracted_specs.model_dump(exclude_none=True)
        assert result == expected_result

        # Verify product was updated and saved
        product.refresh_from_db()
        assert product.specs == result
        assert product.model_name == "Test Model"
        assert product.normalized_name == "Test Brand Test Model"
        mock_service.enrich_product.assert_called_once()

    def test_process_product_success_with_none_returned(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        mock_service.enrich_product.return_value = None

        success, result = orchestrator.process_product(product, dry_run=False)

        assert success is False
        assert result is None
        product.refresh_from_db()
        assert product.specs is None

    def test_process_product_success_dry_run(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        extracted_specs = GenericSpecs(model_name="Dry Run Model", normalized_name="Dry Run Brand Dry Run Model", summary="Dry Run Summary")
        mock_service.enrich_product.return_value = extracted_specs

        success, result = orchestrator.process_product(product, dry_run=True)

        assert success is True
        expected_result = extracted_specs.model_dump(exclude_none=True)
        assert result == expected_result

        # Verify product was updated in memory but NOT saved to DB
        assert product.specs == result
        assert product.model_name == "Dry Run Model"
        assert product.normalized_name == "Dry Run Brand Dry Run Model"

        product.refresh_from_db()
        assert product.specs is None
        assert product.model_name != "Dry Run Model"

    def test_process_product_no_data_returned(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        mock_service.enrich_product.return_value = None

        success, result = orchestrator.process_product(product, dry_run=False)

        assert success is False
        assert result is None

        product.refresh_from_db()
        assert product.specs is None
        assert product.model_name is None
        assert product.normalized_name is None

    def test_process_product_enrichment_error(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        mock_service.enrich_product.side_effect = EnrichmentError("Service failed")

        success, result = orchestrator.process_product(product, dry_run=False)

        assert success is False
        assert result is None

    def test_process_product_unexpected_exception(self):
        mock_service = MagicMock()
        orchestrator = ProductSpecificationsOrchestrator(mock_service)

        product = ProductMasterFactory(specs=None)
        mock_service.enrich_product.side_effect = Exception("Unexpected")

        success, result = orchestrator.process_product(product, dry_run=False)

        assert success is False
        assert result is None

import logging
from unittest.mock import MagicMock, patch

import pytest
from model_bakery import baker

from aiecommerce.services.mercadolibre_impl.eligibility import MercadoLibreEligibilityService
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter

pytestmark = pytest.mark.django_db


@pytest.fixture
def ml_filter_mock():
    """Fixture for a mocked MercadoLibreFilter."""
    return MagicMock(spec=MercadoLibreFilter)


@pytest.fixture
def eligibility_service(ml_filter_mock):
    """Fixture for the MercadoLibreEligibilityService with a mocked filter."""
    return MercadoLibreEligibilityService(ml_filter=ml_filter_mock)


def test_enables_eligible_products(eligibility_service, ml_filter_mock):
    """
    Verify that products returned by the filter are correctly marked as eligible.
    """
    # Arrange: Create products that are not yet marked for ML
    products_to_enable = baker.make("ProductMaster", is_for_mercadolibre=False, _quantity=3)
    eligible_ids = [p.id for p in products_to_enable]
    ml_filter_mock.get_eligible_products.return_value.values_list.return_value = eligible_ids

    # Act
    eligibility_service.update_eligibility_flags()

    # Assert
    for product in products_to_enable:
        product.refresh_from_db()
        assert product.is_for_mercadolibre is True

    # Verify that get_eligible_products was called
    ml_filter_mock.get_eligible_products.assert_called_once()


def test_disables_ineligible_products(eligibility_service, ml_filter_mock):
    """
    Verify that products no longer eligible are unmarked.
    """
    # Arrange: Create products that are currently marked for ML
    products_to_disable = baker.make("ProductMaster", is_for_mercadolibre=True, _quantity=2)

    # The filter returns an empty list, meaning none are eligible anymore
    ml_filter_mock.get_eligible_products.return_value.values_list.return_value = []

    # Act
    eligibility_service.update_eligibility_flags()

    # Assert
    for product in products_to_disable:
        product.refresh_from_db()
        assert product.is_for_mercadolibre is False


def test_handles_mixed_eligibility_scenarios(eligibility_service, ml_filter_mock):
    """
    Test a mixed scenario with products to be enabled, disabled, and left unchanged.
    """
    # Arrange
    # 1. Product that is newly eligible
    prod_to_enable = baker.make("ProductMaster", is_for_mercadolibre=False)
    # 2. Product that remains eligible
    prod_remains_eligible = baker.make("ProductMaster", is_for_mercadolibre=True)
    # 3. Product that is no longer eligible
    prod_to_disable = baker.make("ProductMaster", is_for_mercadolibre=True)
    # 4. Product that remains ineligible
    prod_remains_ineligible = baker.make("ProductMaster", is_for_mercadolibre=False)

    # Filter returns the two eligible products
    eligible_ids = [prod_to_enable.id, prod_remains_eligible.id]
    ml_filter_mock.get_eligible_products.return_value.values_list.return_value = eligible_ids

    # Act
    eligibility_service.update_eligibility_flags()

    # Assert
    prod_to_enable.refresh_from_db()
    assert prod_to_enable.is_for_mercadolibre is True, "Should be enabled"

    prod_remains_eligible.refresh_from_db()
    assert prod_remains_eligible.is_for_mercadolibre is True, "Should remain enabled"

    prod_to_disable.refresh_from_db()
    assert prod_to_disable.is_for_mercadolibre is False, "Should be disabled"

    prod_remains_ineligible.refresh_from_db()
    assert prod_remains_ineligible.is_for_mercadolibre is False, "Should remain disabled"


def test_logging_output_for_updates(eligibility_service, ml_filter_mock, caplog):
    """
    Verify that the logging output correctly reports the number of enabled/disabled products.
    """
    # Arrange
    prod_to_enable = baker.make("ProductMaster", is_for_mercadolibre=False)
    baker.make("ProductMaster", is_for_mercadolibre=True)

    eligible_ids = [prod_to_enable.id]
    ml_filter_mock.get_eligible_products.return_value.values_list.return_value = eligible_ids

    # Act
    with caplog.at_level(logging.INFO):
        eligibility_service.update_eligibility_flags()

    # Assert
    assert "Starting to update Mercado Libre eligibility flags." in caplog.text
    assert "Mercado Libre eligibility update complete. Enabled: 1, Disabled: 1." in caplog.text


def test_no_changes_if_state_is_correct(eligibility_service, ml_filter_mock, caplog):
    """
    Verify that no database updates occur if the flags are already correct.
    """
    # Arrange
    eligible_prod = baker.make("ProductMaster", is_for_mercadolibre=True)
    baker.make("ProductMaster", is_for_mercadolibre=False)

    eligible_ids = [eligible_prod.id]
    ml_filter_mock.get_eligible_products.return_value.values_list.return_value = eligible_ids

    with patch("aiecommerce.services.mercadolibre_impl.eligibility.ProductMaster.objects.update") as mock_update:
        with caplog.at_level(logging.INFO):
            # Act
            eligibility_service.update_eligibility_flags()

    # Assert
    mock_update.assert_not_called()
    assert "Mercado Libre eligibility update complete. Enabled: 0, Disabled: 0." in caplog.text

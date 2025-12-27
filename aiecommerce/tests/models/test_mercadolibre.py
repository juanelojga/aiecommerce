import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from model_bakery import baker

from aiecommerce.models import ProductMaster
from aiecommerce.models.mercadolibre import MercadoLibreListing

pytestmark = pytest.mark.django_db


def test_mercadolibre_listing_defaults():
    """
    Test that a new MercadoLibreListing instance is created with default values.
    """
    # Arrange
    product_master = baker.make(ProductMaster)

    # Act
    listing = baker.make(MercadoLibreListing, product_master=product_master)

    # Assert
    assert listing.status == MercadoLibreListing.Status.PENDING
    assert listing.ml_id is None
    assert listing.last_synced is None
    assert listing.sync_error is None


def test_mercadolibre_listing_str_representation():
    """
    Test the string representation of a MercadoLibreListing instance.
    """
    # Arrange
    product_master = baker.make(ProductMaster, description="Test Product")
    listing_with_id = baker.make(MercadoLibreListing, product_master=product_master, ml_id="MLA12345")
    product_master_no_id = baker.make(ProductMaster, description="Test Product No ID")
    listing_without_id = baker.make(MercadoLibreListing, product_master=product_master_no_id)

    # Act & Assert
    assert str(listing_with_id) == f"{product_master} (MLA12345)"
    assert str(listing_without_id) == f"{product_master_no_id} (N/A)"


def test_mercadolibre_listing_str_no_description():
    """
    Test the string representation of a MercadoLibreListing instance when description is null.
    """
    # Arrange
    product_master = baker.make(ProductMaster, description=None)
    listing = baker.make(MercadoLibreListing, product_master=product_master)

    # Act & Assert
    assert str(listing) == f"Master: {product_master.code} - No description (N/A)"


def test_onetoone_constraint_with_product_master():
    """
    Test that the OneToOne relationship with ProductMaster is enforced.
    """
    # Arrange
    product_master = baker.make(ProductMaster)
    baker.make(MercadoLibreListing, product_master=product_master)

    # Act & Assert
    with pytest.raises(IntegrityError):
        baker.make(MercadoLibreListing, product_master=product_master)


def test_ml_id_uniqueness():
    """
    Test that the 'ml_id' field must be unique.
    """
    # Arrange
    baker.make(MercadoLibreListing, ml_id="MLA12345")

    # Act & Assert
    with pytest.raises(IntegrityError):
        baker.make(MercadoLibreListing, ml_id="MLA12345")


def test_ml_id_can_be_null():
    """
    Test that multiple listings can have a null 'ml_id'.
    """
    # Arrange
    baker.make(MercadoLibreListing, ml_id=None)

    # Act
    baker.make(MercadoLibreListing, ml_id=None)

    # Assert
    assert MercadoLibreListing.objects.filter(ml_id=None).count() == 2


@pytest.mark.parametrize("status_choice", MercadoLibreListing.Status.values)
def test_mercadolibre_listing_valid_statuses(status_choice):
    """
    Test that all defined status choices are accepted.
    """
    # Arrange & Act
    listing = baker.make(MercadoLibreListing, status=status_choice)

    # Assert
    listing.full_clean()  # Should not raise any error
    assert listing.status == status_choice


def test_mercadolibre_listing_invalid_status():
    """
    Test that invalid status values are rejected by Django's field validation.
    """
    # Arrange
    listing = baker.make(MercadoLibreListing, status="INVALID")

    # Act & Assert
    with pytest.raises(ValidationError):
        listing.full_clean()

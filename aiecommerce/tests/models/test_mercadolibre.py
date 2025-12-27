import pytest
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
    product_master = baker.make(ProductMaster, name="Test Product")
    listing_with_id = baker.make(MercadoLibreListing, product_master=product_master, ml_id="MLA12345")
    listing_without_id = baker.make(MercadoLibreListing)

    # Act & Assert
    assert str(listing_with_id) == "Test Product (MLA12345)"
    assert str(listing_without_id) == f"{listing_without_id.product_master.name} (N/A)"


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
    try:
        baker.make(MercadoLibreListing, ml_id=None)
    except IntegrityError:
        pytest.fail("Should be able to create multiple listings with ml_id=None")

    # Assert
    assert MercadoLibreListing.objects.filter(ml_id=None).count() == 2

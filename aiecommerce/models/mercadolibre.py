from django.db import models
from django.utils.translation import gettext_lazy as _

from aiecommerce.models.product import ProductMaster


class MercadoLibreListing(models.Model):
    """
    Represents a product listing on Mercado Libre.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACTIVE = "ACTIVE", _("Active")
        PAUSED = "PAUSED", _("Paused")
        ERROR = "ERROR", _("Error")

    product_master = models.OneToOneField(
        ProductMaster,
        on_delete=models.CASCADE,
        related_name="mercadolibre_listing",
        help_text=_("The master product associated with this listing."),
    )
    ml_id = models.CharField(
        _("Mercado Libre ID"),
        max_length=24,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text=_("The unique identifier for the listing on Mercado Libre."),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text=_("The current status of the listing."),
    )
    last_synced = models.DateTimeField(
        _("Last Synced"),
        null=True,
        blank=True,
        help_text=_("When the listing was last synced with Mercado Libre."),
    )
    sync_error = models.TextField(
        _("Sync Error"),
        null=True,
        blank=True,
        help_text=_("Details of the last synchronization error, if any."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Mercado Libre Listing")
        verbose_name_plural = _("Mercado Libre Listings")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "last_synced"]),
        ]

    def __str__(self):
        """
        String representation used in tests:
        "Master: {code} - {description} (ml_id)".
        """
        return (
            f"Master: {self.product_master.code} - {self.product_master.description} "
            f"({self.ml_id or 'N/A'})"
        )

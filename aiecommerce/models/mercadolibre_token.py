from datetime import timedelta

from django.db import models
from django.utils import timezone


class MercadoLibreToken(models.Model):
    """Stores OAuth2 tokens for a Mercado Libre account."""

    user_id = models.CharField(max_length=50, unique=True, db_index=True)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    is_test_user = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self) -> bool:
        # Check if the token is expired or close to expiring (buffer of 5 minutes)
        return timezone.now() >= (self.expires_at - timedelta(minutes=5))

    def __str__(self):
        prefix = "[TEST] " if self.is_test_user else ""
        return f"{prefix}ML Token - User ID: {self.user_id}"

from django.db import models


class ProductRawPDF(models.Model):
    """Stores raw product data extracted from PDF files."""

    raw_description = models.TextField(null=True, blank=True)
    distributor_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category_header = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PDF Row ({self.id}) - {self.raw_description or 'No description'}"


class ProductRawWeb(models.Model):
    """Stores raw product data scraped from web pages."""

    # Identification
    distributor_code = models.CharField(max_length=255, null=True, blank=True, db_index=True)  # 'Código'
    raw_description = models.TextField(null=True, blank=True)  # 'Descripción'

    # Specific Branch Availability (Storing 'Si'/'No' as raw strings)
    stock_principal = models.CharField(max_length=10, null=True, blank=True)
    stock_colon = models.CharField(max_length=10, null=True, blank=True)
    stock_sur = models.CharField(max_length=10, null=True, blank=True)
    stock_gye_norte = models.CharField(max_length=10, null=True, blank=True)
    stock_gye_sur = models.CharField(max_length=10, null=True, blank=True)

    image_url = models.URLField(max_length=2000, null=True, blank=True)

    # Metadata
    # CRITICAL for hourly updates: Identifies which "run" this item belongs to.
    scrape_session_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)

    raw_html = models.TextField(null=True, blank=True)  # Optional: Can get heavy
    search_term = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Web Scrape ({self.id}) - SKU: {self.distributor_code or 'N/A'}"


class ProductMaster(models.Model):
    """Normalized and master product record."""

    sku = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    price_distributor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    availability_status = models.CharField(max_length=100, null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Master: {self.sku} - {self.description or 'No description'}"

from django.db import models


class ProductRawPDF(models.Model):
    """Stores raw product data extracted from PDF files."""

    raw_description = models.TextField(null=True, blank=True)
    distributor_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category_header = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PDF Row ({self.id}) - {self.raw_description[:50] if self.raw_description else 'No description'}"


class ProductRawWeb(models.Model):
    """Stores raw product data scraped from web pages."""

    sku = models.CharField(max_length=255, null=True, blank=True)  # Mapping to 'Código'
    raw_description = models.TextField(null=True, blank=True)
    scraped_availability = models.TextField(null=True, blank=True)  # e.g., 'Principal', 'Norte'
    product_url = models.URLField(max_length=2000, null=True, blank=True)
    raw_html = models.TextField(null=True, blank=True)
    search_term = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Web Scrape ({self.id}) - SKU: {self.sku or 'N/A'}"


class ProductMaster(models.Model):
    """Normalized and master product record."""

    sku = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    price_distributor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    availability_status = models.CharField(max_length=100, null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Master: {self.sku or 'No SKU'} - {self.description[:50] if self.description else 'No description'}"

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

    code = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    sku = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="Manufacturer Part Number (MPN or SKU).")
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    stock_principal = models.CharField(max_length=10, null=True, blank=True)
    stock_colon = models.CharField(max_length=10, null=True, blank=True)
    stock_sur = models.CharField(max_length=10, null=True, blank=True)
    stock_gye_norte = models.CharField(max_length=10, null=True, blank=True)
    stock_gye_sur = models.CharField(max_length=10, null=True, blank=True)
    image_url = models.URLField(max_length=2000, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_for_mercadolibre = models.BooleanField(default=False)

    specs = models.JSONField(default=dict, blank=True, null=True)

    seo_title = models.CharField(max_length=60, null=True, blank=True, db_index=True, help_text="AI-generated title optimized for marketplaces (Max 60 chars).")
    seo_description = models.TextField(null=True, blank=True, help_text="AI-generated plain text description including storytelling and specs.")

    gtin = models.CharField(max_length=14, null=True, blank=True, db_index=True, help_text="Verified EAN/GTIN/UPC code.")
    gtin_source = models.CharField(max_length=50, null=True, blank=True, help_text="Strategy used: google_search, ean_search_api, etc.")

    normalized_name = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="Standardized name: [Brand] [Line] [Model] [Specs]")
    model_name = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="The specific model identifier (e.g., ProBook 440 G10).")

    def __str__(self):
        has_images = self.images.exists()
        return f"Master: {self.code} - {self.description or 'No description'} (Images: {'Yes' if has_images else 'No'})"


class ProductImage(models.Model):
    """Stores images associated with a master product."""

    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name="images")
    url = models.URLField(max_length=2000)
    order = models.PositiveIntegerField(default=0)
    is_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.product.code} ({self.order}) - {self.url}"


class ProductDetailScrape(models.Model):
    """
    Stores structured product tecnomega_product_details_fetcher_impl scraped from deep-link pages.
    Linked to ProductMaster via a ForeignKey.
    """

    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name="detail_scrapes", help_text="The master product this scrape belongs to.")
    name = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")

    # Stores the full dictionary of attributes (Marca, Peso, Sku, etc.)
    attributes = models.JSONField(default=dict)

    # Stores the list of image URLs found
    image_urls = models.JSONField(default=list)

    # Audit trail
    raw_html = models.TextField(null=True, blank=True)
    scrape_session_id = models.CharField(max_length=100, db_index=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Detail Scrape for {self.product.code} at {self.created_at}"

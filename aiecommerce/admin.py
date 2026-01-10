from django.contrib import admin

from aiecommerce.models import MercadoLibreListing, MercadoLibreToken, ProductDetailScrape, ProductImage, ProductMaster, ProductRawPDF, ProductRawWeb


# Register your models
@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "price", "is_active", "sku", "gtin", "last_updated")
    list_filter = ("is_active", "category")
    search_fields = ("code", "description")


@admin.register(MercadoLibreListing)
class MercadoLibreListingAdmin(admin.ModelAdmin):
    list_display = ("product_master", "ml_id", "status", "last_synced")
    list_filter = ("status",)
    search_fields = ("ml_id", "product_master__code", "product_master__description")


@admin.register(MercadoLibreToken)
class MercadoLibreTokenAdmin(admin.ModelAdmin):
    list_display = ("user_id", "expires_at", "is_expired", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("user_id",)

    def is_expired(self, obj):
        return obj.is_expired()


admin.site.register(ProductRawPDF)
admin.site.register(ProductRawWeb)
admin.site.register(ProductImage)
admin.site.register(ProductDetailScrape)

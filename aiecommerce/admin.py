from django.contrib import admin

from aiecommerce.models import MercadoLibreListing, ProductMaster, ProductRawPDF, ProductRawWeb


# Register your models
@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "price", "is_active", "last_updated")
    list_filter = ("is_active", "category")
    search_fields = ("code", "description")


@admin.register(MercadoLibreListing)
class MercadoLibreListingAdmin(admin.ModelAdmin):
    list_display = ("product_master", "ml_id", "status", "last_synced")
    list_filter = ("status",)
    search_fields = ("ml_id", "product_master__code", "product_master__description")


admin.site.register(ProductRawPDF)
admin.site.register(ProductRawWeb)

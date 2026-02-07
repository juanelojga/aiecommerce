from django.contrib import admin
from django.db.models import Q

from aiecommerce.models import MercadoLibreListing, MercadoLibreToken, ProductDetailScrape, ProductImage, ProductMaster, ProductRawPDF, ProductRawWeb


class GtinNotNullFilter(admin.SimpleListFilter):
    title = "GTIN"  # Display title in the filter UI
    parameter_name = "gtin"

    def lookups(self, request, model_admin):
        return (("null", "Empty"),)

    def queryset(self, request, queryset):
        if self.value() == "null":
            return queryset.filter(~Q(gtin__isnull=False))  # Filter where gtin is not null
        return queryset


@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "get_ml_id", "price", "is_active", "sku", "gtin", "is_for_mercadolibre", "last_updated")
    list_filter = ("is_active", "category", GtinNotNullFilter)  # Add the custom filter here
    search_fields = ("code", "description", "mercadolibre_listing__ml_id")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("mercadolibre_listing")

    @admin.display(description="ML ID", ordering="mercadolibre_listing__ml_id")
    def get_ml_id(self, obj):
        try:
            return obj.mercadolibre_listing.ml_id or "-"
        except MercadoLibreListing.DoesNotExist:
            return "-"


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

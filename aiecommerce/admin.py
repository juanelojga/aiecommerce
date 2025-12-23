from django.contrib import admin

from aiecommerce.models import ProductMaster, ProductRawPDF, ProductRawWeb


# Register your models
@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "price", "is_active", "last_updated")
    list_filter = ("is_active",)


admin.site.register(ProductRawPDF)
admin.site.register(ProductRawWeb)

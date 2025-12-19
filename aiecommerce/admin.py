from django.contrib import admin

from aiecommerce.models import ProductMaster, ProductRawPDF, ProductRawWeb

# Register your models
admin.site.register(ProductMaster)
admin.site.register(ProductRawPDF)
admin.site.register(ProductRawWeb)

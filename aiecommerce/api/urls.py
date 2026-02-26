from django.urls import URLPattern, URLResolver
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# Register viewsets here:
# from aiecommerce.api.v1.views.product import ProductViewSet
# router.register(r"products", ProductViewSet, basename="product")

urlpatterns: list[URLPattern | URLResolver] = [
    *router.urls,
    # Add non-router API paths here:
    # path("custom/", CustomView.as_view(), name="custom-endpoint"),
]

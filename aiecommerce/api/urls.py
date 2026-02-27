from django.urls import URLPattern, URLResolver, path
from rest_framework.routers import DefaultRouter

from aiecommerce.api.v1.views.health_check import HealthCheckView

router = DefaultRouter()

# Register viewsets here:
# from aiecommerce.api.v1.views.product import ProductViewSet
# router.register(r"products", ProductViewSet, basename="product")

urlpatterns: list[URLPattern | URLResolver] = [
    *router.urls,
    path("health/", HealthCheckView.as_view(), name="api-health-check"),
    # Add non-router API paths here:
    # path("custom/", CustomView.as_view(), name="custom-endpoint"),
]

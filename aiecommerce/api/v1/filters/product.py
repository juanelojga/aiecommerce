import django_filters
from django.db.models import QuerySet

from aiecommerce.models.product import ProductMaster


class ProductFilter(django_filters.FilterSet):
    """FilterSet for the product catalog list endpoint."""

    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")
    has_stock = django_filters.BooleanFilter(method="filter_has_stock", label="Has stock")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = ProductMaster
        fields = ["category", "has_stock", "is_active"]

    def filter_has_stock(
        self,
        queryset: QuerySet[ProductMaster],
        name: str,
        value: bool,
    ) -> QuerySet[ProductMaster]:
        """Filter products by stock availability using the annotated field."""
        if value is True:
            return queryset.filter(computed_total_available_stock__gt=0)  # type: ignore[misc]
        if value is False:
            return queryset.filter(computed_total_available_stock=0)  # type: ignore[misc]
        return queryset

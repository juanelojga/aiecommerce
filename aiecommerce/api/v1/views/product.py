from django.db.models import Case, IntegerField, QuerySet, Value, When
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from aiecommerce.api.v1.filters.product import ProductFilter
from aiecommerce.api.v1.serializers.product import ProductSerializer
from aiecommerce.models.product import ProductMaster


class ProductViewSet(mixins.ListModelMixin, GenericViewSet):
    """
    List-only viewset for the product catalog.

    GET /api/v1/products/

    Supports filtering by category, has_stock, is_active and
    ordering by last_bundled_date (ascending = oldest first).
    """

    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    ordering_fields = ["last_bundled_date"]
    ordering = ["last_bundled_date"]

    def get_queryset(self) -> QuerySet[ProductMaster]:
        """Return annotated queryset with total_available_stock computed at DB level."""
        branch_cases = [When(**{f"{field}__iexact": "SI"}, then=Value(1)) for field in ProductMaster.BRANCH_FIELDS]

        # Mirror the @property logic:
        # If stock_principal != 'SI' → 0, else sum branch availability.
        stock_annotation = Case(
            When(
                stock_principal__iexact="SI",
                then=sum(Case(branch, default=Value(0), output_field=IntegerField()) for branch in branch_cases),
            ),
            default=Value(0),
            output_field=IntegerField(),
        )

        return ProductMaster.objects.annotate(computed_total_available_stock=stock_annotation).only(
            "id",
            "code",
            "sku",
            "normalized_name",
            "price",
            "category",
            "last_bundled_date",
            "is_active",
            "stock_principal",
            *ProductMaster.BRANCH_FIELDS,
        )

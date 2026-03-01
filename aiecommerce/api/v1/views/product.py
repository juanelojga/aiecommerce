from django.db.models import Case, IntegerField, QuerySet, Value, When
from rest_framework import mixins, serializers
from rest_framework.viewsets import GenericViewSet

from aiecommerce.api.v1.filters.product import ProductFilter
from aiecommerce.api.v1.serializers.product import ProductSerializer
from aiecommerce.api.v1.serializers.product_detail import ProductDetailSerializer
from aiecommerce.models.product import ProductMaster


class ProductViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """
    Viewset for the product catalog.

    GET /api/v1/products/          — Paginated product list.
    GET /api/v1/products/{id}/     — Full technical details for a single product.

    The list action supports filtering by category, has_stock, is_active and
    ordering by last_bundled_date (ascending = oldest first).

    The retrieve action returns the complete technical profile including
    the ``specs`` JSONField, used by the Dependency Resolver for
    compatibility checks (TDP, socket types, dimensions).
    """

    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    ordering_fields = ["last_bundled_date"]
    ordering = ["last_bundled_date"]

    def get_serializer_class(self) -> type[serializers.Serializer]:
        """Return the appropriate serializer for the current action."""
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    def get_queryset(self) -> QuerySet[ProductMaster]:
        """Return the appropriate queryset for the current action.

        For *list*: annotated with ``computed_total_available_stock`` at DB
        level and projected via ``.only()`` for performance.

        For *retrieve*: full model (no ``.only()``) so that every field
        (``specs``, ``seo_title``, etc.) is available to the serializer.
        """
        if self.action == "retrieve":
            return ProductMaster.objects.all()

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

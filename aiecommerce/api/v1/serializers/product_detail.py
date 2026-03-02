from rest_framework import serializers

from aiecommerce.api.v1.serializers.product_image import ProductImageSerializer
from aiecommerce.models.product import ProductMaster


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for the product technical details retrieve endpoint.

    Provides the full technical profile of a specific component,
    including the complete ``specs`` JSONField used by the
    Dependency Resolver for compatibility checks.
    """

    total_available_stock = serializers.SerializerMethodField()
    image_urls = ProductImageSerializer(source="images", many=True, read_only=True)

    class Meta:
        model = ProductMaster
        fields = [
            "id",
            "code",
            "sku",
            "normalized_name",
            "model_name",
            "description",
            "seo_title",
            "seo_description",
            "price",
            "category",
            "gtin",
            "specs",
            "image_url",
            "image_urls",
            "total_available_stock",
        ]
        read_only_fields = fields

    def get_total_available_stock(self, obj: ProductMaster) -> int:
        """Return computed stock from the model property."""
        return obj.total_available_stock

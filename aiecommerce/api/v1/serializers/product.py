from rest_framework import serializers

from aiecommerce.models.product import ProductMaster


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for the product catalog list endpoint."""

    total_available_stock = serializers.IntegerField(
        read_only=True,
        source="computed_total_available_stock",
    )

    class Meta:
        model = ProductMaster
        fields = [
            "id",
            "code",
            "sku",
            "normalized_name",
            "price",
            "category",
            "total_available_stock",
        ]
        read_only_fields = fields

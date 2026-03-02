from rest_framework import serializers

from aiecommerce.models.product import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Read-only serializer for product images.

    Returns ``url`` and ``order`` for each image associated with a product,
    ordered by the ``order`` field (ascending).
    """

    class Meta:
        model = ProductImage
        fields = [
            "url",
            "order",
        ]
        read_only_fields = fields

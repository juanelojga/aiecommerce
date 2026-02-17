"""
Example usage of GTINSearchService.

This demonstrates how to use the GTIN enrichment service to search
for GTIN codes using three sequential strategies.
"""

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_enrichment_impl import GTINSearchService


def example_search_gtin():
    """Example of searching for GTIN code."""
    # Initialize the service
    service = GTINSearchService()

    # Get a product (replace with actual product query)
    product = ProductMaster.objects.filter(gtin__isnull=True).first()

    if not product:
        print("No products found without GTIN")
        return

    # Search for GTIN
    gtin, strategy = service.search_gtin(product)

    if gtin:
        print(f"✅ GTIN found: {gtin}")
        print(f"   Strategy: {strategy}")

        # Update the product
        product.gtin = gtin
        product.gtin_source = strategy
        product.save()
    else:
        print(f"❌ No GTIN found for product: {product.code}")
        print(f"   Strategy used: {strategy}")


if __name__ == "__main__":
    example_search_gtin()

import os
import sys

import django

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiecommerce.settings")
django.setup()


def verify_image_search(product_master_id: int):
    try:
        product_master = ProductMaster.objects.get(id=product_master_id)
    except ProductMaster.DoesNotExist:
        print(f"ProductMaster with ID {product_master_id} not found.")
        return

    print(f"Verifying image search for ProductMaster: {product_master.description} (ID: {product_master.id})")

    image_search_service = ImageSearchService()

    # Build search query
    search_query = image_search_service.build_search_query(product_master)
    print(f"\nGenerated Search Query: {search_query}")

    # Find image URLs
    try:
        image_urls = image_search_service.find_image_urls(search_query)
        print("\nFound Image URLs:")
        if image_urls:
            for url in image_urls:
                print(f"- {url}")
        else:
            print("No image URLs found.")
    except Exception as e:
        print(f"\nError finding image URLs: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_image_search.py <product_master_id>")
        sys.exit(1)

    try:
        product_id = int(sys.argv[1])
        verify_image_search(product_id)
    except ValueError:
        print("Error: ProductMaster ID must be an integer.")
        sys.exit(1)

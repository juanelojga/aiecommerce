from django.conf import settings
from django.core.management.base import BaseCommand

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search import (
    ImageCandidateSelector,
    ImageSearchService,
)
from aiecommerce.tasks.images import process_product_image


class Command(BaseCommand):
    help = "Fetches images for products destined for Mercado Libre that are missing images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of products to process.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Finds candidate products and prints the image URLs that would be fetched, without calling Celery.",
        )
        parser.add_argument(
            "--id",
            type=int,
            default=None,
            help="Specify a single product ID to process.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        product_id = options["id"]

        if product_id:
            try:
                products = [ProductMaster.objects.get(pk=product_id)]
                self.stdout.write(self.style.SUCCESS(f"Processing product with ID {product_id}."))
            except ProductMaster.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Product with ID {product_id} not found."))
                return
        else:
            selector = ImageCandidateSelector()
            products = selector.find_products_without_images()

        if limit and not product_id:
            products = products[:limit]

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Found {len(products)} products. Performing a dry run to find image URLs..."))
            search_service = ImageSearchService()
            for product in products:
                query = search_service.build_search_query(product)
                urls = search_service.find_image_urls(query, image_search_count=settings.IMAGE_SEARCH_COUNT)
                self.stdout.write(f"\n- Product: {product.description} (ID: {product.id})")
                self.stdout.write(f"  Query: '{query}'")
                if urls:
                    self.stdout.write("  Candidate URLs:")
                    for url in urls:
                        self.stdout.write(f"  - {url}")
                else:
                    self.stdout.write("  No candidate URLs found.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Found {len(products)} products to process. Triggering Celery tasks..."))
            for product in products:
                process_product_image.delay(product.id)
            self.stdout.write(self.style.SUCCESS("Done."))

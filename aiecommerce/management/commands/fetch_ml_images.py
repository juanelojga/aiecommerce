from django.core.management.base import BaseCommand

from aiecommerce.services.mercadolibre_impl.image_search import ImageCandidateSelector
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
            help="Print the names of products that would have images fetched without actually calling the search API.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]

        selector = ImageCandidateSelector()
        products = selector.find_products_without_images()

        if limit:
            products = products[:limit]

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Found {len(products)} products that would have images fetched:"))
            for product in products:
                self.stdout.write(f"- {product.description}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Found {len(products)} products to process. Triggering Celery tasks..."))
            for product in products:
                process_product_image.delay(product.id)
            self.stdout.write(self.style.SUCCESS("Done."))

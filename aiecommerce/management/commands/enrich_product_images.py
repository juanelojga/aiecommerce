import time

from django.core.management.base import BaseCommand

from aiecommerce.models import ProductMaster
from aiecommerce.tasks.images import process_product_image


class Command(BaseCommand):
    help = "Enqueues tasks to fetch and process images for products that do not have them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which products would be processed, but do not enqueue any tasks.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS("--- Starting image enrichment process ---"))

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE: No tasks will be enqueued. ---"))

        # Fetch products without any associated images
        products_without_images = ProductMaster.objects.filter(images__isnull=True, is_active=True).order_by("id")
        total_products = products_without_images.count()

        if total_products == 0:
            self.stdout.write(self.style.SUCCESS("No products found without images."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total_products} products without images to process."))

        if dry_run:
            self.stdout.write("--- Displaying the first 2 products that would be processed: ---")
            for product in products_without_images[:2]:
                self.stdout.write(f"  - [DRY RUN] Would process Product ID: {product.id}, SKU: {product.sku}, Description: {product.description}")
            return

        # In normal mode, enqueue the tasks
        enqueued_count = 0
        for product in products_without_images.iterator():
            try:
                process_product_image.delay(product.id)
                self.stdout.write(self.style.SUCCESS(f"Successfully enqueued task for Product ID: {product.id}"))
                enqueued_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to enqueue task for Product ID: {product.id}. Error: {e}"))
            time.sleep(0.1)  # To avoid overwhelming Celery broker

        self.stdout.write(self.style.SUCCESS(f"\n--- Process complete. Enqueued {enqueued_count}/{total_products} tasks. ---"))

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.product_images import refresh_product_images


class Command(BaseCommand):
    help = "Delete a product's images (DB + S3) and enqueue a task to re-fetch them."

    def add_arguments(self, parser):
        parser.add_argument("product_code", type=str, help="Product code to refresh images for.")

    def handle(self, *args, **options):
        code = options["product_code"]
        try:
            task_id = refresh_product_images(code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f"Product with code {code!r} not found.")

        self.stdout.write(self.style.SUCCESS(f"Queued image refresh for {code}. Task id: {task_id}"))

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService
from aiecommerce.tasks.images import process_product_image


class Command(BaseCommand):
    help = "Verifies image fetching for a specific product and optionally enqueues the task."

    def add_arguments(self, parser):
        parser.add_argument("product_code", type=str, help="Product code (EAN/SKU)")
        parser.add_argument("--dry-run", action="store_true", default=True, help="Show results without enqueuing (default)")
        parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Actually enqueue the task")

    def handle(self, *args, **options):
        product_code = options["product_code"]
        dry_run = options["dry_run"]

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f"ProductMaster with code '{product_code}' not found.")

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))
            self.stdout.write(f"- Product: {product.description} (Code: {product.code})")

            service = ImageSearchService()
            query = service.build_search_query(product)
            self.stdout.write(f"Query: '{query}'")

            urls = service.find_image_urls(query, image_search_count=10)
            self.stdout.write("Candidate URLs:")
            for url in urls:
                self.stdout.write(f"- {url}")
        else:
            process_product_image.delay(product.id)
            self.stdout.write(self.style.SUCCESS("Done."))

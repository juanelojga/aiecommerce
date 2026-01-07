from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService
from aiecommerce.tasks.images import process_product_image


class Command(BaseCommand):
    help = "Fetches images for products destined for Mercado Libre that are missing images."

    def add_arguments(self, parser):
        parser.add_argument("product_code", type=str, help="The product code (ProductMaster.code) to sync.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="API calls are performed, but no data is saved to the database.",
        )
        parser.add_argument(
            "--no-dry-run",
            action="store_false",
            dest="dry_run",
            help="Disables dry-run mode, allowing database persistence.",
        )

    def handle(self, *args, **options):
        product_code = options["product_code"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f"ProductMaster with code '{product_code}' not found.")

        if dry_run:
            search_service = ImageSearchService()

            query = search_service.build_search_query(product)
            urls = search_service.find_image_urls(query, image_search_count=settings.IMAGE_SEARCH_COUNT)
            self.stdout.write(f"\n- Product: {product.description} (Code: {product.code})")
            self.stdout.write(f"  Query: '{query}'")
            if urls:
                self.stdout.write("  Candidate URLs:")
                for url in urls:
                    self.stdout.write(f"  - {url}")
            else:
                self.stdout.write("  No candidate URLs found.")
        else:
            process_product_image.delay(product.id)
            self.stdout.write(self.style.SUCCESS("Done."))

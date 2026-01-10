import logging

from django.core.management.base import BaseCommand

from aiecommerce.services.normalization_impl import ProductNormalizationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalizes product data from web scrapes and PDF lists into a master product table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=str,
            help="Specify a scrape_session_id to process. If not provided, the latest one will be used.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting product normalization...")
        session_id = options.get("session_id")

        service = ProductNormalizationService()
        results = service.normalize_products(scrape_session_id=session_id)

        if results:
            self.stdout.write(self.style.SUCCESS("Normalization process finished successfully."))
            self.stdout.write(f"  - Processed Web Items: {results['processed_count']}")
            self.stdout.write(f"  - Products Created: {results['created_count']}")
            self.stdout.write(f"  - Products Updated: {results['updated_count']}")
            self.stdout.write(f"  - Products Marked as Inactive: {results['inactive_count']}")
        else:
            self.stdout.write(self.style.WARNING("Normalization process did not run. Check logs for tecnomega_product_details_fetcher_impl."))

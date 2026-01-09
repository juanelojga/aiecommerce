import logging

from django.conf import settings  # Import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_search_impl.ean_api_strategy import EANSearchAPIStrategy
from aiecommerce.services.gtin_search_impl.ean_search_client import EANSearchClient
from aiecommerce.services.gtin_search_impl.matcher import ProductMatcher

# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verifies the EAN API strategy for a given product code."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("product_code", type=str, help="The SKU of the product to verify.")
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear cache for the product queries before running.",
        )

    def handle(self, *args, **options) -> None:
        # Display current cache backend
        cache_backend = settings.CACHES["default"]["BACKEND"]
        self.stdout.write(self.style.NOTICE(f"Current Cache Backend: {cache_backend}"))

        product_code = options["product_code"]
        clear_cache = options["clear_cache"]

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Product with SKU '{product_code}' not found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Verifying EAN API for product: {product.description} (SKU: {product.sku})"))

        # Instantiate dependencies
        client = EANSearchClient()
        matcher = ProductMatcher(product)
        strategy = EANSearchAPIStrategy(client=client, matcher=matcher)

        if clear_cache:
            self.stdout.write(self.style.WARNING("Clearing cache..."))
            # Clear cache for model name query
            model_name_query = strategy._get_query(product, use_sku=False)
            if model_name_query:
                cache_key_model = strategy._get_cache_key(model_name_query)
                cache.delete(cache_key_model)
                self.stdout.write(self.style.SUCCESS(f"  - Cleared cache for query: '{model_name_query}'"))
            # Clear cache for SKU query
            sku_query = strategy._get_query(product, use_sku=True)
            if sku_query:
                cache_key_sku = strategy._get_cache_key(sku_query)
                cache.delete(cache_key_sku)
                self.stdout.write(self.style.SUCCESS(f"  - Cleared cache for query: '{sku_query}'"))

        # Run the strategy
        gtin = strategy.search_for_gtin(product)

        if gtin:
            self.stdout.write(self.style.SUCCESS(f"\nFound GTIN: {gtin}"))
        else:
            self.stdout.write(self.style.WARNING("\nNo GTIN found."))

import json
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import ProductMaster
from aiecommerce.services.specifications_impl.orchestrator import ProductSpecificationsOrchestrator
from aiecommerce.services.specifications_impl.service import (
    ConfigurationError,
    ProductSpecificationsService,
)


class Command(BaseCommand):
    help = "Normalize ProductMaster records with structured specs using AI"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("product_code", type=str, help="The product code (ProductMaster.code) to sync.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess products that already have specs",
        )
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
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="Delay in seconds between processing each product.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        product_code = options["product_code"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f"ProductMaster with code '{product_code}' not found.")

        try:
            self.stdout.write(self.style.HTTP_INFO("Initializing services..."))

            service = ProductSpecificationsService()
            orchestrator = ProductSpecificationsOrchestrator(service)

        except ConfigurationError as e:
            self.stdout.write(self.style.ERROR(f"Configuration Error: {e}"))
            return

        # complete the code
        description = product.description or ""
        self.stdout.write(self.style.NOTICE(f"Processing product: {product.code} - {description[:50]}..."))

        success, specs = orchestrator.process_product(product, dry_run=dry_run)

        if success:
            self.stdout.write(self.style.SUCCESS("Successfully processed product."))
            self.stdout.write(self.style.SUCCESS("Extracted Specifications:"))
            self.stdout.write(json.dumps(specs, indent=2))
        else:
            self.stdout.write(self.style.ERROR("Failed to process product."))

        if delay > 0 and not dry_run:
            time.sleep(delay)

from typing import Any

from django.core.management.base import BaseCommand

from aiecommerce.services.mercadolibre_impl.eligibility import (
    MercadoLibreEligibilityService,
)
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter


class Command(BaseCommand):
    help = "Updates the 'is_for_mercadolibre' flag on all ProductMaster instances."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculates which products would be changed without saving to the database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        self.stdout.write(self.style.HTTP_INFO("Initializing services..."))
        ml_filter = MercadoLibreFilter()
        service = MercadoLibreEligibilityService(ml_filter)

        self.stdout.write(self.style.HTTP_INFO("Updating eligibility flags..."))
        result = service.update_eligibility_flags(dry_run=dry_run)

        enabled_count = result["enabled"]
        disabled_count = result["disabled"]

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n--- DRY RUN RESULTS ---\n"
                    f"Products that would be enabled: {enabled_count}\n"
                    f"Products that would be disabled: {disabled_count}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n--- UPDATE COMPLETE ---\nProducts enabled: {enabled_count}\nProducts disabled: {disabled_count}")
            )

        self.stdout.write(self.style.SUCCESS("Operation finished."))

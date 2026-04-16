from __future__ import annotations

import logging
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.picture_update_service import GENERIC_IMAGE_SUFFIX
from aiecommerce.services.product_images import refresh_product_images
from aiecommerce.services.telegram_impl.formatters import format_incorrect_ml_images_stats
from aiecommerce.tasks.mercadolibre_pictures import update_ml_listing_pictures_task
from aiecommerce.tasks.notifications import send_telegram_notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = f"Find ACTIVE Mercado Libre listings whose product images still use the generic {GENERIC_IMAGE_SUFFIX} placeholder, refresh the images, and update the live ML listing."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the affected listings without enqueuing any work.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Cap the number of listings queued per run.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        limit: int | None = options["limit"]

        qs = (
            MercadoLibreListing.objects.filter(
                status=MercadoLibreListing.Status.ACTIVE,
                product_master__images__url__endswith=GENERIC_IMAGE_SUFFIX,
            )
            .select_related("product_master")
            .distinct()
            .order_by("pk")
        )
        if limit is not None:
            qs = qs[:limit]

        listings = list(qs)
        total = len(listings)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No ACTIVE listings with the generic placeholder image."))
            return

        self.stdout.write(self.style.WARNING(f"Found {total} ACTIVE listing(s) with the generic {GENERIC_IMAGE_SUFFIX} image."))

        queued = 0
        skipped = 0
        for listing in listings:
            code = listing.product_master.code
            if not code:
                logger.warning("Skipping listing %s: product_master.code is empty.", listing.pk)
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  [dry-run] would refresh {code} (ml_id={listing.ml_id})")
                queued += 1
                continue

            refresh_product_images(code, link=update_ml_listing_pictures_task.si(code))
            queued += 1
            logger.info("Queued refresh+ml-update for product %s (ml_id=%s).", code, listing.ml_id)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. {queued} listing(s) would be queued."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Queued {queued} refresh+ml-update job(s)."))

        stats = {"queued": queued, "skipped": skipped}
        if not dry_run and (queued > 0 or skipped > 0):
            try:
                message = format_incorrect_ml_images_stats(stats, dry_run=dry_run)
                send_telegram_notification.apply_async(args=(message,))
            except Exception:
                logger.error("Failed to queue Telegram notification.", exc_info=True)

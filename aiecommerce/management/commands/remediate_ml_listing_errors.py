import logging
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl.error_remediation_service import MercadoLibreErrorRemediationService
from aiecommerce.services.telegram_impl.formatters import format_remediation_stats
from aiecommerce.tasks.notifications import send_telegram_notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remediate MercadoLibreListing rows stuck in ERROR status based on their sync_error code."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Classify listings and log intended actions without deleting anything.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process at most N ERROR listings.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        limit: int | None = options["limit"]

        self.stdout.write("Starting Mercado Libre error remediation...")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run enabled."))

        auth_service = MercadoLibreAuthService()
        try:
            token_instance = MercadoLibreToken.objects.filter(is_test_user=False).latest("created_at")
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError("No Mercado Libre token found. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token: {e}")

        client = MercadoLibreClient(access_token=token_instance.access_token)
        service = MercadoLibreErrorRemediationService(ml_client=client)

        stats = service.remediate_all(limit=limit, dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS(f"Remediation finished. total={stats['total']} gtin={stats['gtin']} price={stats['price']} other={stats['other']} failed={stats['failed']}"))

        if not dry_run and stats["total"] > 0:
            self._send_notification(stats)

    def _send_notification(self, stats: dict[str, int]) -> None:
        try:
            message = format_remediation_stats(stats)
            send_telegram_notification.apply_async(args=(message,))
            logger.info("Remediation Telegram notification queued.")
        except Exception as e:
            logger.error(f"Failed to queue Telegram notification: {e}")
            self.stdout.write(self.style.WARNING("Failed to send Telegram notification"))

import logging
from argparse import ArgumentParser
from typing import Any

import instructor
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_category_impl.attribute_fixer import MercadolibreAttributeFixer
from aiecommerce.services.mercadolibre_impl import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl import BatchPublisherOrchestrator
from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator
from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService
from aiecommerce.services.telegram_impl.formatters import format_batch_publish_stats
from aiecommerce.tasks.notifications import send_telegram_notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Publishes a batch of products to Mercado Libre.
    """

    help = "Publishes all products with 'Pending' status to Mercado Libre."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Prepare the payload and log it, but do not actually send it to Mercado Libre.",
        )
        parser.add_argument(
            "--sandbox",
            action="store_true",
            help="Use the Mercado Libre sandbox environment (test user).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        sandbox: bool = options["sandbox"]

        mode = "SANDBOX" if sandbox else "PRODUCTION"

        # Retrieve and validate token
        token_instance = self._get_valid_token(sandbox)

        self.stdout.write(self.style.SUCCESS(f"--- Starting batch product publication in {mode} mode ---"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run is enabled. No data will be sent to Mercado Libre."))

        stats: dict[str, int | list[str]] = {"success": 0, "errors": 0, "skipped": 0, "published_ids": []}

        try:
            # Initialize services
            client = MercadoLibreClient(access_token=token_instance.access_token)
            open_client = instructor.from_openai(OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url=settings.OPENROUTER_BASE_URL))
            attribute_fixer = MercadolibreAttributeFixer(client=open_client)
            publisher = MercadoLibrePublisherService(client=client, attribute_fixer=attribute_fixer)
            publisher_orchestrator = PublisherOrchestrator(publisher=publisher)

            # Execute batch publication
            batch_orchestrator = BatchPublisherOrchestrator(publisher_orchestrator=publisher_orchestrator)
            stats = batch_orchestrator.run(dry_run=dry_run, sandbox=sandbox)

            self.stdout.write(self.style.SUCCESS(f"--- Batch publication finished: {stats['success']} succeeded, {stats['errors']} failed, {stats['skipped']} skipped ---"))

        except (MLTokenError, MercadoLibreToken.DoesNotExist) as e:
            raise CommandError(f"Token error: {e}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            logger.exception("Failed to publish batch of products")
            raise
        finally:
            # Send Telegram notification only if products were processed
            if stats.get("success", 0) > 0 or stats.get("errors", 0) > 0:
                self._send_notification(stats, mode, dry_run)

    def _get_valid_token(self, sandbox: bool) -> MercadoLibreToken:
        """Retrieve and validate MercadoLibre token for the specified environment."""
        auth_service = MercadoLibreAuthService()

        token_instance = MercadoLibreToken.objects.filter(is_test_user=sandbox).order_by("-created_at").first()

        if not token_instance:
            env = "sandbox" if sandbox else "production"
            raise CommandError(f"No token found for {env} user. Please authenticate first.")

        try:
            return auth_service.get_valid_token(user_id=token_instance.user_id)
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token: {e}")

    def _send_notification(self, stats: dict[str, Any], mode: str, dry_run: bool) -> None:
        """Send Telegram notification with batch publication results."""
        try:
            # Format the message
            message = format_batch_publish_stats(
                stats=stats,
                mode=mode,
                dry_run=dry_run,
                product_ids=stats.get("published_ids", []),
            )

            # Queue the notification task (non-blocking)
            send_telegram_notification.apply_async(args=(message,))
            logger.info("Telegram notification task queued successfully")

        except Exception as e:
            # Don't let notification errors break the command
            logger.error(f"Failed to queue Telegram notification: {e}")
            self.stdout.write(self.style.WARNING("Failed to send Telegram notification"))

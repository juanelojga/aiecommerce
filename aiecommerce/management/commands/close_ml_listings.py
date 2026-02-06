from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import MercadoLibreToken
from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl.close_publication_service import (
    MercadoLibreClosePublicationService,
)


class Command(BaseCommand):
    help = "Closes listings that have been paused for 48+ hours on Mercado Libre."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making any actual changes.",
        )
        parser.add_argument(
            "--id",
            type=str,
            help="The internal ID or Mercado Libre ID of a specific listing to close.",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=48,
            help="Number of hours a listing must be paused before closing (default: 48).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        listing_id = options["id"]
        hours = options["hours"]

        self.stdout.write("Starting Mercado Libre listings close operation...")
        if dry_run:
            self.stdout.write(self.style.WARNING("Performing a dry run."))

        auth_service = MercadoLibreAuthService()
        try:
            # We first try to find the latest token to get a user_id
            token_instance = MercadoLibreToken.objects.filter(is_test_user=False).latest("created_at")
            # Then we use the auth_service to ensure it is valid (refreshes if needed)
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError("No token found for site MEC. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token for site MEC: {e}")

        client = MercadoLibreClient(access_token=token_instance.access_token)
        close_service = MercadoLibreClosePublicationService(ml_client=client)

        if listing_id:
            listing = MercadoLibreListing.objects.filter(pk=listing_id).first() or MercadoLibreListing.objects.filter(ml_id=listing_id).first()
            if not listing:
                self.stdout.write(self.style.ERROR(f"Listing with id {listing_id} not found."))
                return

            self.stdout.write(f"Closing listing: {listing.ml_id or listing.id}")
            if close_service.close_listing(listing, dry_run=dry_run):
                self.stdout.write(self.style.SUCCESS(f"Listing {listing.ml_id or listing.id} closed successfully."))
            else:
                self.stdout.write(self.style.WARNING(f"No changes for listing {listing.ml_id or listing.id}."))
        else:
            self.stdout.write(f"Closing all paused listings older than {hours} hours.")
            close_service.close_all_paused_listings(hours=hours, dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS("Listing close operation finished."))

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import MercadoLibreToken
from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl.sync_service import MercadoLibreSyncService


class Command(BaseCommand):
    help = "Synchronizes listings with Mercado Libre."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making any actual changes.",
        )
        parser.add_argument(
            "--id",
            type=str,
            help="The internal ID or Mercado Libre ID of a specific listing to sync.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        listing_id = options["id"]

        self.stdout.write("Starting Mercado Libre listings synchronization...")
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
        sync_service = MercadoLibreSyncService(ml_client=client)

        if listing_id:
            try:
                listing = MercadoLibreListing.objects.get(pk=listing_id)
            except (MercadoLibreListing.DoesNotExist, ValueError):
                try:
                    listing = MercadoLibreListing.objects.get(ml_id=listing_id)
                except MercadoLibreListing.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Listing with id {listing_id} not found."))
                    return

            self.stdout.write(f"Syncing listing: {listing.ml_id or listing.id}")
            if sync_service.sync_listing(listing, dry_run=dry_run):
                self.stdout.write(self.style.SUCCESS(f"Listing {listing.ml_id or listing.id} updated."))
            else:
                self.stdout.write(self.style.NOTICE(f"No changes for listing {listing.ml_id or listing.id}."))
        else:
            self.stdout.write("Syncing all active listings.")
            sync_service.sync_all_listings(dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS("Synchronization finished."))

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from aiecommerce.models.product import ProductRawWeb


class Command(BaseCommand):
    help = "Deletes records from ProductRawWeb older than 48 hours."

    def handle(self, *args: Any, **options: Any):
        """
        The main logic for the command.

        Deletes all ProductRawWeb records where 'created_at' is older than
        48 hours from the current time.
        """
        self.stdout.write("Starting to prune old scrape records...")

        # Calculate the cutoff time (48 hours ago)
        cutoff_time = timezone.now() - timedelta(hours=48)

        # Filter records older than the cutoff time
        old_records = ProductRawWeb.objects.filter(created_at__lt=cutoff_time)

        # Get the count and delete them
        # The .delete() method returns a tuple with the number of deletions
        # and a dictionary with the number of deletions per object type.
        deleted_count, _ = old_records.delete()

        if deleted_count > 0:
            success_message = f"Successfully pruned {deleted_count} old scrape records."
            self.stdout.write(self.style.SUCCESS(success_message))
        else:
            self.stdout.write(self.style.SUCCESS("No old scrape records to prune."))

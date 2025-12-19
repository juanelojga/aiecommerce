from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from aiecommerce.models import ProductRawPDF


class ProductRawRepository:
    """
    Repository for managing raw product data from PDF sources in the database.
    """

    BATCH_SIZE = 1000

    def save_bulk(self, data: List[Dict]) -> int:
        """
        Atomically truncates the existing ProductRawPDF table and bulk-inserts new data.

        This method ensures data consistency by performing the delete and create
        operations within a single database transaction. An `created_at` timestamp
        is uniformly applied to all new records.

        Args:
            data: A list of dictionaries, where each dictionary represents the
                  data for a single ProductRawPDF instance.

        Returns:
            The total number of records created. Returns 0 if the input data is empty.
        """
        if not data:
            return 0

        now = timezone.now()
        for item in data:
            item["created_at"] = now

        with transaction.atomic():
            # Truncate the table before inserting new data
            ProductRawPDF.objects.all().delete()

            # Prepare model instances for bulk creation
            instances = [ProductRawPDF(**item) for item in data]

            # Bulk create the new records
            ProductRawPDF.objects.bulk_create(instances, batch_size=self.BATCH_SIZE)

        return len(instances)

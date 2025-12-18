from typing import Any, Dict, List

from aiecommerce.services.price_list_impl.repository import ProductRawRepository
from aiecommerce.services.price_list_ingestion import PriceListIngestionService


class PriceListIngestionUseCase:
    """
    Handles the orchestration of price list ingestion, including data retrieval
    and persistence.
    """

    def __init__(
        self,
        ingestion_service: PriceListIngestionService,
        repository: ProductRawRepository,
    ):
        self.ingestion_service = ingestion_service
        self.repository = repository

    def execute(self, base_url: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes the price list ingestion process.

        Args:
            base_url: The base URL from which to start the ingestion process.
            dry_run: If True, the data will be processed but not persisted
                     to the database. A preview of the data will be returned.

        Returns:
            A dictionary containing the status of the operation, the count of
            processed/saved records, and an optional data preview for dry runs.
        """
        data: List[Dict] = self.ingestion_service.process(base_url)

        if dry_run:
            return {"status": "dry_run", "count": len(data), "preview": data[:5]}
        else:
            saved_count = self.repository.save_bulk(data)
            return {"status": "success", "count": saved_count}

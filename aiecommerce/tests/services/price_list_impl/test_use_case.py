from typing import Any, Dict, List

from aiecommerce.services.price_list_impl.repository import ProductRawRepository
from aiecommerce.services.price_list_impl.use_case import PriceListIngestionUseCase
from aiecommerce.services.price_list_ingestion import PriceListIngestionService


class _FakeIngestionService(PriceListIngestionService):  # Subclass to ensure compatibility
    def __init__(self, data: List[Dict]):
        self._data = data
        self.calls: List[Dict[str, Any]] = []

    def process(self, base_url: str) -> List[Dict]:  # Matches PriceListIngestionService's method
        self.calls.append({"base_url": base_url})
        return self._data


class _FakeRepository(ProductRawRepository):  # Subclass to ensure compatibility
    def __init__(self) -> None:
        self.saved_payloads: List[List[Dict]] = []
        self.return_count: int | None = None

    def save_bulk(self, data: List[Dict]) -> int:  # Overrides ProductRawRepository's method
        self.saved_payloads.append(data)
        # If test did not set a custom return count, default to len(data)
        return self.return_count if self.return_count is not None else len(data)


def test_execute_dry_run_returns_preview_and_does_not_persist() -> None:
    data = [{"id": i} for i in range(10)]
    ingestion = _FakeIngestionService(data)
    repo = _FakeRepository()

    use_case = PriceListIngestionUseCase(ingestion_service=ingestion, repository=repo)
    result = use_case.execute(base_url="https://example.com/prices", dry_run=True)

    # ingestion should be called with the base URL
    assert ingestion.calls == [{"base_url": "https://example.com/prices"}]

    # repository should not be called in dry run
    assert repo.saved_payloads == []

    # result should include dry_run status, total count and preview of first 5 items
    assert result["status"] == "dry_run"
    assert result["count"] == len(data)
    assert result["preview"] == data[:5]


def test_execute_persists_data_and_returns_success_with_saved_count() -> None:
    data = [{"sku": "A1"}, {"sku": "B2"}]
    ingestion = _FakeIngestionService(data)
    repo = _FakeRepository()
    # simulate repository saving and returning a custom saved count
    repo.return_count = 2

    use_case = PriceListIngestionUseCase(ingestion_service=ingestion, repository=repo)
    result = use_case.execute(base_url="https://example.com/prices", dry_run=False)

    # ingestion should be called
    assert len(ingestion.calls) == 1
    # repository should be called once with the exact data from ingestion
    assert repo.saved_payloads == [data]

    # result should indicate success and reflect repository return count
    assert result == {"status": "success", "count": 2}


def test_execute_handles_empty_data_in_both_modes() -> None:
    empty: List[Dict] = []
    ingestion = _FakeIngestionService(empty)
    repo = _FakeRepository()

    use_case = PriceListIngestionUseCase(ingestion_service=ingestion, repository=repo)

    # dry run with empty data
    dry = use_case.execute(base_url="https://example.com/prices", dry_run=True)
    assert dry["status"] == "dry_run"
    assert dry["count"] == 0
    assert dry["preview"] == []
    assert repo.saved_payloads == []  # still no persistence

    # non-dry run with empty data should still call repository with empty list
    normal = use_case.execute(base_url="https://example.com/prices", dry_run=False)
    assert repo.saved_payloads[-1] == []
    # default return of repo is len(data) which is 0
    assert normal == {"status": "success", "count": 0}

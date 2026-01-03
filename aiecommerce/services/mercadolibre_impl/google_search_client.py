from typing import Any, Protocol


class GoogleSearchClient(Protocol):
    """Protocol for Google Custom Search API client."""

    def list(self, **kwargs: Any) -> Any: ...

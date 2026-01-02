from typing import Any

from aiecommerce.services.mercadolibre_impl.google_search_client import GoogleSearchClient


def test_google_search_client_protocol():
    """
    Tests that a class implementing the list method satisfies the GoogleSearchClient protocol.
    """

    class MockClient:
        def list(self, **kwargs: Any) -> Any:
            return {"items": []}

    def use_client(client: GoogleSearchClient):
        return client.list(q="test")

    mock_client = MockClient()
    result = use_client(mock_client)
    assert result == {"items": []}

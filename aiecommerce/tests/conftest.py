import pytest


@pytest.fixture(autouse=True)
def _disable_ssl_redirect(settings: pytest.FixtureRequest) -> None:
    """Disable SECURE_SSL_REDIRECT for all tests.

    When DEBUG=False (the CI/production default), Django's SecurityMiddleware
    redirects every HTTP request to HTTPS with a 301.  The test client uses
    plain HTTP, so every request would fail with an unexpected redirect.
    """
    settings.SECURE_SSL_REDIRECT = False  # type: ignore[attr-defined]

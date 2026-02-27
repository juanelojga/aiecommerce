"""Header-based API key authentication for DRF.

Validates the ``X-API-KEY`` request header against the value stored in
``settings.API_KEY``.  Uses :func:`hmac.compare_digest` for constant-time
comparison to prevent timing-based attacks.

When the header is **absent** the authenticator returns ``None`` so that the
next authentication class in the chain (e.g. ``SessionAuthentication``) gets a
chance to authenticate the request.  When the header is **present but
invalid**, an :class:`~rest_framework.exceptions.AuthenticationFailed`
exception is raised immediately.
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

if TYPE_CHECKING:
    from rest_framework.request import Request


class _ApiKeyUser:
    """Lightweight sentinel that satisfies DRF's ``request.user`` contract.

    DRF expects ``authenticate()`` to return a *(user, auth)* 2-tuple where
    *user* is truthy.  This minimal object avoids importing the full Django
    ``User`` model while still being recognised as an authenticated principal.
    """

    is_authenticated: bool = True

    def __str__(self) -> str:  # pragma: no cover – cosmetic
        return "ApiKeyUser"


_API_KEY_USER = _ApiKeyUser()

_HEADER = "HTTP_X_API_KEY"


class ApiKeyAuthentication(BaseAuthentication):
    """Authenticate requests bearing a valid ``X-API-KEY`` header.

    Behaviour
    ---------
    * Header missing → return ``None`` (fall through to next auth backend).
    * ``settings.API_KEY`` empty/unset → raise ``AuthenticationFailed``
      (fail-secure: prevents accidental open access when the key is not
      configured).
    * Header present and valid → return ``(_ApiKeyUser(), "api_key")``.
    * Header present but invalid → raise ``AuthenticationFailed``.
    """

    def authenticate(self, request: Request) -> tuple[_ApiKeyUser, str] | None:
        key_from_header: str | None = request.META.get(_HEADER)

        if key_from_header is None:
            # Header not supplied – let the next authenticator try.
            return None

        configured_key: str = getattr(settings, "API_KEY", "")
        if not configured_key:
            raise AuthenticationFailed("API key authentication is not configured on the server.")

        if not hmac.compare_digest(key_from_header, configured_key):
            raise AuthenticationFailed("Invalid API key.")

        return _API_KEY_USER, "api_key"

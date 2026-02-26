"""IP-based access control for DRF views.

Checks ``request.META['REMOTE_ADDR']`` against the networks listed in
``settings.API_ALLOWED_IPS``.  Each entry can be a plain IP address
(``192.168.1.10``) **or** a CIDR range (``10.0.0.0/8``).  Both IPv4 and
IPv6 are supported via the :mod:`ipaddress` standard-library module.

When ``settings.API_ALLOWED_IPS`` is **empty** (the default for local
development), *all* IPs are permitted so developers don't need to
configure anything to get started.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

logger = logging.getLogger(__name__)

# Module-level cache: parsed once per process, not per request.
_parsed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None


def _get_allowed_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Return the parsed network list, initialising the cache on first call."""
    global _parsed_networks  # noqa: PLW0603
    if _parsed_networks is None:
        raw: list[str] = getattr(settings, "API_ALLOWED_IPS", [])
        networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in raw:
            entry = entry.strip()
            if not entry:
                continue
            try:
                networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                logger.warning("Ignoring invalid API_ALLOWED_IPS entry: %s", entry)
        _parsed_networks = networks
    return _parsed_networks


class IPWhitelistPermission(BasePermission):
    """Allow access only from IP addresses / CIDR ranges in ``settings.API_ALLOWED_IPS``.

    If the setting is empty or absent every IP is allowed (fail-open for
    local development).  In production the list should be populated with
    trusted addresses.
    """

    message = "Request blocked: IP address is not in the allowlist."

    def has_permission(self, request: Request, view: APIView) -> bool:
        allowed = _get_allowed_networks()

        # Empty allowlist → permit all (dev convenience).
        if not allowed:
            return True

        remote_addr: str = request.META.get("REMOTE_ADDR", "")
        try:
            client_ip = ipaddress.ip_address(remote_addr)
        except ValueError:
            logger.warning("Could not parse REMOTE_ADDR: %s", remote_addr)
            return False

        return any(client_ip in network for network in allowed)

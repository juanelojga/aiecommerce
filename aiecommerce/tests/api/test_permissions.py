"""Tests for IPWhitelistPermission."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

import aiecommerce.api.permissions.ip_whitelist_permission as _mod
from aiecommerce.api.permissions.ip_whitelist_permission import (
    IPWhitelistPermission,
)

factory = APIRequestFactory()


@pytest.fixture(autouse=True)
def _reset_network_cache() -> None:  # type: ignore[misc]
    """Reset the module-level parsed network cache before each test."""
    _mod._parsed_networks = None


class TestIPWhitelistPermission:
    """Unit tests for the IP-based access control permission."""

    def _make_perm(self) -> IPWhitelistPermission:
        return IPWhitelistPermission()

    def _make_request(self, remote_addr: str = "127.0.0.1") -> MagicMock:
        request = factory.get("/api/v1/")
        request.META["REMOTE_ADDR"] = remote_addr
        return request

    # -- Empty allowlist (dev convenience) ------------------------------------

    @override_settings(API_ALLOWED_IPS=[])
    def test_empty_allowlist_permits_all(self) -> None:
        """When API_ALLOWED_IPS is empty, all IPs are allowed."""
        request = self._make_request("203.0.113.42")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is True

    # -- Exact IP match -------------------------------------------------------

    @override_settings(API_ALLOWED_IPS=["192.168.1.100"])
    def test_allowed_ip_passes(self) -> None:
        """A request from an allowed IP is permitted."""
        request = self._make_request("192.168.1.100")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is True

    @override_settings(API_ALLOWED_IPS=["192.168.1.100"])
    def test_blocked_ip_rejected(self) -> None:
        """A request from a non-allowed IP is rejected."""
        request = self._make_request("10.0.0.1")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is False

    # -- CIDR range matching ---------------------------------------------------

    @override_settings(API_ALLOWED_IPS=["10.0.0.0/8"])
    def test_cidr_range_allows_matching_ip(self) -> None:
        """An IP within a CIDR range is permitted."""
        request = self._make_request("10.255.255.1")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is True

    @override_settings(API_ALLOWED_IPS=["10.0.0.0/8"])
    def test_cidr_range_blocks_non_matching_ip(self) -> None:
        """An IP outside a CIDR range is rejected."""
        request = self._make_request("192.168.1.1")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is False

    @override_settings(API_ALLOWED_IPS=["192.168.1.0/24"])
    def test_cidr_24_range(self) -> None:
        """A /24 CIDR range matches all 256 addresses in the subnet."""
        view = MagicMock()
        perm = self._make_perm()

        # In range
        request_in = self._make_request("192.168.1.42")
        assert perm.has_permission(request_in, view) is True

        # Out of range
        _mod._parsed_networks = None  # reset cache
        request_out = self._make_request("192.168.2.42")
        assert perm.has_permission(request_out, view) is False

    # -- IPv6 support ----------------------------------------------------------

    @override_settings(API_ALLOWED_IPS=["::1"])
    def test_ipv6_localhost_allowed(self) -> None:
        """IPv6 localhost is permitted when in the allowlist."""
        request = self._make_request("::1")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is True

    @override_settings(API_ALLOWED_IPS=["::1"])
    def test_ipv6_other_blocked(self) -> None:
        """An IPv6 address not in the allowlist is rejected."""
        request = self._make_request("::2")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is False

    @override_settings(API_ALLOWED_IPS=["fd00::/8"])
    def test_ipv6_cidr_range(self) -> None:
        """IPv6 CIDR ranges are supported."""
        view = MagicMock()
        perm = self._make_perm()

        request_in = self._make_request("fd00::1")
        assert perm.has_permission(request_in, view) is True

        _mod._parsed_networks = None
        request_out = self._make_request("fe80::1")
        assert perm.has_permission(request_out, view) is False

    # -- Multiple entries ------------------------------------------------------

    @override_settings(API_ALLOWED_IPS=["192.168.1.0/24", "10.0.0.5", "::1"])
    def test_multiple_entries(self) -> None:
        """Multiple allowlist entries (mixed IPs and CIDRs) work together."""
        view = MagicMock()
        perm = self._make_perm()

        assert perm.has_permission(self._make_request("192.168.1.50"), view) is True
        assert perm.has_permission(self._make_request("10.0.0.5"), view) is True
        assert perm.has_permission(self._make_request("::1"), view) is True
        assert perm.has_permission(self._make_request("172.16.0.1"), view) is False

    # -- Invalid REMOTE_ADDR ---------------------------------------------------

    @override_settings(API_ALLOWED_IPS=["127.0.0.1"])
    def test_invalid_remote_addr_rejected(self) -> None:
        """An unparseable REMOTE_ADDR is rejected."""
        request = self._make_request("not-an-ip")
        view = MagicMock()

        assert self._make_perm().has_permission(request, view) is False

    # -- Invalid allowlist entry (graceful handling) ---------------------------

    @override_settings(API_ALLOWED_IPS=["not-valid", "127.0.0.1"])
    def test_invalid_entry_ignored_valid_still_works(self) -> None:
        """Invalid entries in API_ALLOWED_IPS are skipped; valid ones still work."""
        view = MagicMock()
        perm = self._make_perm()

        request = self._make_request("127.0.0.1")
        assert perm.has_permission(request, view) is True

    # -- Permission message ----------------------------------------------------

    def test_message_attribute(self) -> None:
        """The permission class has a descriptive denial message."""
        perm = self._make_perm()
        assert "not in the allowlist" in perm.message

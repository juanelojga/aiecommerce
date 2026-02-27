# API Authentication & Authorization

This document describes the two-layer security model protecting all `/api/v1/` endpoints.

## Overview

| Layer          | Class                   | What it does                                              |
| -------------- | ----------------------- | --------------------------------------------------------- |
| Authentication | `ApiKeyAuthentication`  | Validates the `X-API-KEY` request header                  |
| Authorization  | `IPWhitelistPermission` | Restricts access to a set of allowed IP addresses / CIDRs |

Both classes are registered as **global DRF defaults** in `settings.REST_FRAMEWORK`, so every API view inherits them automatically. Individual views can override `authentication_classes` or `permission_classes` when justified.

`SessionAuthentication` is kept as a secondary authentication backend so that the browsable API and Django admin continue to work for browser-based sessions.

---

## API Key Authentication

### How it works

1. The client sends the `X-API-KEY` header with every request.
2. `ApiKeyAuthentication` reads the header and compares it against `settings.API_KEY` using `hmac.compare_digest()` (constant-time comparison to prevent timing attacks).
3. If the header is **missing**, the authenticator returns `None` — DRF falls through to the next backend (`SessionAuthentication`).
4. If the header is **present but invalid**, a `403 Forbidden` is returned immediately.
5. If `settings.API_KEY` is empty or unset, all API-key-authenticated requests are rejected (fail-secure).

### Configuration

Add to your `.env` file:

```dotenv
# Generate a strong key:  python -c 'import secrets; print(secrets.token_urlsafe(32))'
API_KEY=your-secret-api-key-here
```

### Usage

```bash
curl -H "X-API-KEY: your-secret-api-key-here" https://your-domain.com/api/v1/...
```

### File location

```
aiecommerce/api/authentication/
├── __init__.py                    # Re-exports ApiKeyAuthentication
└── api_key_authentication.py      # Implementation
```

---

## IP Whitelisting

### How it works

1. `IPWhitelistPermission` reads `request.META['REMOTE_ADDR']` to obtain the client's IP address.
2. It checks whether the IP falls within any of the networks listed in `settings.API_ALLOWED_IPS`.
3. Both individual IPs (`203.0.113.5`) and CIDR ranges (`10.0.0.0/8`) are supported via Python's `ipaddress` standard library module.
4. IPv4 and IPv6 are fully supported.
5. The network list is parsed **once per process** (not per request) for performance.

### Configuration

Add to your `.env` file:

```dotenv
# Comma-separated IPs and/or CIDR ranges.
# Leave empty to allow ALL IPs (convenient for local dev, NOT for production).
API_ALLOWED_IPS=127.0.0.1,::1,10.0.0.0/8
```

### Behaviour

| `API_ALLOWED_IPS` value     | Effect                                |
| --------------------------- | ------------------------------------- |
| Empty / not set             | All IPs are allowed (dev convenience) |
| `127.0.0.1,::1`             | Only localhost (IPv4 + IPv6)          |
| `203.0.113.0/24,10.0.0.0/8` | Two CIDR ranges                       |

### File location

```
aiecommerce/api/permissions/
├── __init__.py                    # Re-exports IPWhitelistPermission
└── ip_whitelist_permission.py     # Implementation
```

---

## Environment Variables

| Variable          | Required   | Default | Description                                                               |
| ----------------- | ---------- | ------- | ------------------------------------------------------------------------- |
| `API_KEY`         | Yes (prod) | `""`    | Secret key validated against the `X-API-KEY` header. Empty = fail-secure. |
| `API_ALLOWED_IPS` | No         | `[]`    | Comma-separated IPs/CIDRs. Empty = allow all IPs.                         |

---

## DRF Settings

The global defaults in `settings.REST_FRAMEWORK`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "aiecommerce.api.authentication.api_key_authentication.ApiKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "aiecommerce.api.permissions.ip_whitelist_permission.IPWhitelistPermission",
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

DRF evaluates authentication classes **in order** — `ApiKeyAuthentication` is tried first. If it returns `None` (no header), `SessionAuthentication` gets a chance. Permission classes are evaluated with AND semantics — the request must pass **both** `IPWhitelistPermission` and `IsAuthenticated`.

---

## Per-View Overrides

To exempt a specific view from the global defaults (e.g., a public health-check endpoint):

```python
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

class HealthCheckView(APIView):
    authentication_classes: list[type] = []     # No auth required
    permission_classes = [AllowAny]             # No IP check

    def get(self, request):
        return Response({"status": "ok"})
```

Any override of `permission_classes` or `authentication_classes` should have explicit justification in a code comment or PR description.

---

## Production Checklist

- [ ] Set a strong, random `API_KEY` (minimum 32 characters).
- [ ] Populate `API_ALLOWED_IPS` with your trusted server/VPN IPs.
- [ ] If behind a reverse proxy (nginx, Railway, AWS ALB), ensure `REMOTE_ADDR` reflects the real client IP. You may need to configure Django's `SECURE_PROXY_SSL_HEADER` or use a middleware like `django-xff` to parse `X-Forwarded-For`.
- [ ] Rotate `API_KEY` periodically and after any suspected compromise.
- [ ] Monitor logs for `AuthenticationFailed` exceptions (indicates brute-force or misconfiguration).

---

## Testing

Use `APIRequestFactory` and `override_settings` for isolated tests:

```python
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from aiecommerce.api.authentication.api_key_authentication import ApiKeyAuthentication

factory = APIRequestFactory()

@override_settings(API_KEY="test-secret")
def test_valid_api_key():
    request = factory.get("/api/v1/products/", HTTP_X_API_KEY="test-secret")
    auth = ApiKeyAuthentication()
    user, auth_info = auth.authenticate(request)
    assert user.is_authenticated
    assert auth_info == "api_key"
```

See `aiecommerce/tests/api/` for the full test suite.

---

## Practical Testing with curl

For hands-on examples of testing the API using `curl` (health check, authenticated requests, error troubleshooting), see the [API curl Testing Guide](../docs/testing/api-curl-guide.md).

# API Testing with curl

This guide shows how to test API endpoints locally using `curl`. It covers the public health-check endpoint and authenticated requests protected by the two-layer security model (API key + IP whitelist).

## Prerequisites

1. **Docker services running**

   ```bash
   docker-compose up -d
   ```

2. **Environment variables** — The Docker Compose file ships with dev-friendly defaults:

   | Variable          | Docker default                         | Description                       |
   | ----------------- | -------------------------------------- | --------------------------------- |
   | `API_KEY`         | `dev-test-key-change-me-in-production` | Secret for the `X-API-KEY` header |
   | `API_ALLOWED_IPS` | `127.0.0.1,::1`                        | Localhost IPs (IPv4 + IPv6)       |

   To override, create a `.env` file in the project root or export the variables before running `docker-compose up`:

   ```bash
   # .env (example)
   API_KEY=my-secret-key-at-least-32-chars-long
   API_ALLOWED_IPS=127.0.0.1,::1,10.0.0.0/8
   ```

3. **Local dev server** (alternative to Docker):

   ```bash
   source venv/bin/activate
   # Export vars so the Django dev server picks them up
   export API_KEY="dev-test-key-change-me-in-production"
   export API_ALLOWED_IPS="127.0.0.1,::1"
   python manage.py runserver
   ```

---

## 1. Health Check (Public — No Auth Required)

The health endpoint is exempt from API key authentication and IP whitelisting, making it suitable for Docker `HEALTHCHECK`, load balancer probes, and quick smoke tests.

```bash
curl -s http://localhost:8000/api/v1/health/ | python -m json.tool
```

**Expected response** (`200 OK`):

```json
{
  "status": "ok"
}
```

### One-liner with status code

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health/
# Output: 200
```

---

## 2. Authenticated API Requests

All endpoints under `/api/v1/` (except health) require:

1. A valid `X-API-KEY` header matching the server's `API_KEY` setting.
2. The client IP to be in the `API_ALLOWED_IPS` whitelist.

### Template

```bash
curl -s \
  -H "X-API-KEY: dev-test-key-change-me-in-production" \
  http://localhost:8000/api/v1/<endpoint>/ | python -m json.tool
```

### Example — List endpoint (once viewsets are registered)

```bash
curl -s \
  -H "X-API-KEY: dev-test-key-change-me-in-production" \
  http://localhost:8000/api/v1/products/ | python -m json.tool
```

### POST request with JSON body

```bash
curl -s -X POST \
  -H "X-API-KEY: dev-test-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Product", "price": 99.99}' \
  http://localhost:8000/api/v1/products/ | python -m json.tool
```

---

## 3. Common Error Responses

### Missing API key (`401 Unauthorized`)

```bash
curl -s http://localhost:8000/api/v1/products/
```

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Fix:** Add the `X-API-KEY` header to your request.

### Invalid API key (`403 Forbidden`)

```bash
curl -s -H "X-API-KEY: wrong-key" http://localhost:8000/api/v1/products/
```

```json
{
  "detail": "Invalid API key."
}
```

**Fix:** Use the correct `API_KEY` value from your `.env` or Docker environment.

### IP not whitelisted (`403 Forbidden`)

```bash
# Coming from an IP not in API_ALLOWED_IPS
curl -s -H "X-API-KEY: dev-test-key-change-me-in-production" \
  http://<remote-host>:8000/api/v1/products/
```

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Fix:** Add your IP or CIDR to `API_ALLOWED_IPS`:

```bash
API_ALLOWED_IPS=127.0.0.1,::1,203.0.113.5
```

### Empty `API_KEY` in settings (`403 Forbidden`)

When `API_KEY` is empty or unset, the server is **fail-secure** — all API-key requests are rejected regardless of the key sent.

**Fix:** Set a non-empty `API_KEY` in your `.env` or environment.

---

## 4. Useful curl Flags

| Flag                | Purpose                                  |
| ------------------- | ---------------------------------------- | ------------------------ |
| `-s`                | Silent mode (no progress bar)            |
| `-v`                | Verbose — shows request/response headers |
| `-o /dev/null`      | Discard body (useful with `-w`)          |
| `-w "%{http_code}"` | Print only the HTTP status code          |
| `-H "Header: val"`  | Add a custom header                      |
| `-X POST`           | Set HTTP method                          |
| `-d '{"k":"v"}'`    | Send JSON body                           |
| `                   | python -m json.tool`                     | Pretty-print JSON output |

---

## 5. Docker HEALTHCHECK

You can add a `HEALTHCHECK` to `docker-compose.yml` to let Docker monitor the web service:

```yaml
services:
  web:
    # ... existing config ...
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Check container health status:

```bash
docker-compose ps
# or
docker inspect --format='{{.State.Health.Status}}' aiecommerce-web-1
```

---

## Related Documentation

- [API Authentication & Authorization](../api-authentication.md) — Full details on the two-layer security model.
- [Railway Deployment Guide](../deployment/RAILWAY_GUIDE.md) — Production environment variable setup.

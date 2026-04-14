# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Django 5.x + DRF on Python 3.12, PostgreSQL, Redis, Celery. Tooling: Ruff (lint/format), Mypy (with `mypy_django_plugin` + `mypy_drf_plugin`), pytest + pytest-django + model_bakery. Containerized via Docker Compose.

## Common Commands

Dev runs in Docker; prefix commands with `docker compose exec web`, or run locally via `uv run …` (uv manages `.venv/`).

```bash
# Tests (inside the web container — requires the `db` service to be up)
docker compose exec web pytest                                   # all
docker compose exec web pytest aiecommerce/tests/test_models.py  # single file
docker compose exec web pytest path::test_name                   # single test

# Tests (local, against a host-exposed DB on 5432 matching DATABASE_URL in .env)
uv run pytest

# Lint / format / types
uv run ruff format .
uv run ruff check . --fix
uv run mypy .   # excludes aiecommerce/tests/, venv/, .venv/

# Django
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell

# Docker lifecycle
docker compose up -d --build
docker compose logs -f
docker compose down          # preserves data; `-v` wipes the DB
```

Never run `migrate` automatically as part of a task — only when explicitly asked.

## Architecture

The project is a single Django app (`aiecommerce/`) structured as modular packages, not monolithic `models.py`/`views.py` files. Each class lives in its own file and is re-exported from the package `__init__.py`.

- `models/` — domain entities (product, mercadolibre, mercadolibre_token, …). Split per domain.
- `views/` — project-level views (e.g. Mercado Libre OAuth login/callback).
- `api/` — versioned REST API. `api/urls.py` → `api/v1/` with `views/`, `serializers/`, `filters/`. Authentication and permissions live in `api/authentication/` and `api/permissions/`.
- `services/` — business logic. Views stay thin; anything non-trivial (scraping, AI enrichment, ML publishing, image pipeline, normalization, pricing, Telegram notifications) is a service package under `services/<feature>_impl/`.
- `tasks/` — Celery tasks (images, upscaling, notifications, periodic, connectivity). The image refresh pipeline is async and requires a running Celery worker.
- `management/commands/` — operational entry points that orchestrate services: scraping (`scrape_tecnomega`), price sync (`sync_price_list`), enrichment (`enrich_products_*`), Mercado Libre lifecycle (`publish_ml_product*`, `sync_ml_listings`, `pause_ml_listings`, `close_ml_listings`, `update_ml_eligibility`), image ops (`refresh_product_images`, `upscale_scraped_images`).
- `tests/` mirrors the package layout (`tests/api/`, `tests/services/`, `tests/management/commands/`).

Data flow for the core pipeline: scraping → raw rows (`ProductRawWeb`) → `sync_price_list` produces processed products → enrichment commands fill SKU / specs / images / GTIN / ML category → publish commands push to Mercado Libre. See `docs/mercadolibre/` for end-to-end guides (notably `ai_content_pipeline.md`, `image_pipeline.md`, `image_refresh.md`).

## API Security

All `/api/v1/` endpoints require both an `X-API-KEY` header (matching `API_KEY` env) **and** source IP in `API_ALLOWED_IPS` (CIDR-aware, empty = allow-all). Empty `API_KEY` fail-secures to reject all API-key requests. Session auth is the fallback when no `X-API-KEY` is sent (used by Django admin / DRF browsable API). Details: `docs/api-authentication.md`.

## Conventions

- Absolute imports only.
- Type hints required on new code; mypy is strict outside tests.
- Prefer CBVs (Django generic / DRF) over FBVs.
- Use `model_bakery` for test factories; shared fixtures in `conftest.py`, app-specific in `tests/fixtures.py`. Mark DB tests with `@pytest.mark.django_db`.
- Do not generate tests in the same change as feature code unless explicitly requested.
- Secrets via env vars only (`.env`, `django-environ`); never hardcode.

## Engineering Practices

All generated code must follow these practices:

- **TDD**: when tests are explicitly requested, write the failing test first, then implement to green. Even when tests are not requested in the same change (per the Conventions rule above), design code to be testable — pure functions where possible, inject dependencies into services instead of instantiating external clients inline.
- **SOLID**: single-responsibility per module/class (mirrors the "one class per file" layout); depend on abstractions for external systems (Mercado Libre, Telegram, scraping, AI) — keep them behind `services/<feature>_impl/` packages so they can be swapped or mocked.
- **DRY**: before adding a helper, search `services/`, `models/`, and `api/` for an existing implementation and reuse it. Do not duplicate validation, serialization, or query logic across views and services.
- **General best practices**: small functions, descriptive names, no dead code, no commented-out blocks. Fail loudly at boundaries (raise — don't silently swallow exceptions). Log via the existing logger setup. Never hardcode secrets.

## CI Parity

Before declaring any code task complete, run the same checks CI runs (see `.github/workflows/ci.yml`):

```bash
ruff check .            # linting, import ordering
ruff format --check .   # formatting
mypy .                  # type checking
pytest                  # tests
```

Fix lint, formatting, import-ordering, and type errors locally — do not rely on CI to surface them. `ruff check --fix` and `ruff format .` may be used to auto-fix, but the `--check` variants must pass cleanly afterward.

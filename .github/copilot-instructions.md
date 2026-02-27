# GitHub Copilot Instructions – AI Ecommerce Django Project

## Project Overview

This is a **Django 5.x + PostgreSQL** e-commerce application with AI-powered product enrichment and MercadoLibre marketplace integration.

**Tech Stack:**

- Django 5.x, Python 3.12
- PostgreSQL (with Django ORM)
- Redis + Celery for background tasks
- pytest + pytest-django + model_bakery for testing
- Ruff (linting/formatting), MyPy (strict type checking)
- Docker Compose for local development

**Key Features:**

- Web scraping pipeline (Tecnomega supplier)
- AI content generation for product descriptions/specs
- Image processing and upscaling
- MercadoLibre API integration (OAuth2, product publishing)
- Scheduled background jobs via Celery Beat

## Build, Test, and Lint Commands

### Development Setup

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Install dependencies
pip install -r requirements.txt        # Production deps
pip install -r requirements-dev.txt    # Adds testing/linting tools

# Run migrations (manual step - never auto-migrate)
python manage.py migrate

# Start dev server
python manage.py runserver
```

### Testing

```bash
# Run all tests
venv/bin/python -m pytest

# Run specific test file
venv/bin/python -m pytest aiecommerce/tests/test_models.py

# Run specific test function
venv/bin/python -m pytest aiecommerce/tests/services/test_enrichment.py::test_enrich_product_specs

# Run with coverage
venv/bin/python -m pytest --cov=aiecommerce

# Run tests matching a pattern
venv/bin/python -m pytest -k "test_mercadolibre"
```

### Linting and Formatting

```bash
# Format code (auto-fix)
ruff format .

# Check and auto-fix linting issues
ruff check . --fix

# Type checking (strict mode)
mypy .

# Run all pre-commit hooks manually
pre-commit run --all-files
```

### Celery (Background Tasks)

```bash
# Start Celery worker
celery -A aiecommerce.config.celery worker -l info

# Start Celery Beat scheduler
celery -A aiecommerce.config.celery beat -l info

# Run both worker + beat in one command (dev only)
celery -A aiecommerce.config.celery worker --beat -l info
```

### Key Management Commands

```bash
# Scrape products from Tecnomega
python manage.py scrape_tecnomega --categories notebook monitor

# Sync price list
python manage.py sync_price_list

# Normalize products
python manage.py normalize_products

# Enrich products with AI-generated content
python manage.py enrich_products_content
python manage.py enrich_products_specs

# Publish to MercadoLibre
python manage.py publish_ml_product <product_id>

# Verify MercadoLibre OAuth handshake
python manage.py verify_ml_handshake
```

## Architecture

### File Organization (CRITICAL)

**DO NOT use single `models.py` or `views.py` files.** This project uses a **modular package structure** where each class gets its own file:

```
aiecommerce/
├── api/                 # DRF API layer
│   ├── urls.py
│   ├── authentication/  # Custom auth backends
│   │   ├── __init__.py
│   │   └── api_key_authentication.py
│   ├── permissions/     # Custom permission classes
│   │   ├── __init__.py
│   │   └── ip_whitelist_permission.py
│   └── v1/
│       ├── views/
│       └── serializers/
├── models/              # Each model in separate file
│   ├── __init__.py      # MUST export: from .product import Product
│   ├── product.py       # Product model only
│   └── mercadolibre.py  # MercadoLibre models only
├── views/               # Each view/viewset in separate file
│   ├── __init__.py
│   ├── mercadolibre_login.py
│   └── mercadolibre_callback.py
├── services/            # Business logic (pure Python, no Django magic)
│   ├── __init__.py
│   ├── enrichment_impl/      # Service implementations
│   ├── mercadolibre_impl/
│   └── price_list_impl/
├── tasks/               # Celery tasks
│   ├── periodic.py      # Scheduled tasks
│   └── async.py         # On-demand async tasks
├── management/commands/ # Django management commands
│   └── *.py
├── tests/               # Mirror app structure
│   ├── factories.py     # model_bakery fixtures
│   ├── models/
│   ├── views/
│   └── services/
├── urls.py
└── admin.py
```

### Service Layer Pattern

- **Views are THIN**: Parse request → call service → return response
- **Services contain business logic**: Data transformation, external APIs, complex operations
- Services are in `aiecommerce/services/<domain>_impl/` packages
- Example: `enrichment_impl/enrichment_service.py` handles AI content generation

### Background Jobs

- **Celery Beat** runs scheduled tasks (defined in `aiecommerce/config/celery.py`)
- Tasks are in `aiecommerce/tasks/periodic.py`
- Scraping → normalization → enrichment → publishing pipeline runs automatically
- Schedule: Mon-Sat, every 2 hours from 8am-6pm (staggered by 10-15 min intervals)

### External Integrations

1. **Tecnomega (supplier)**: Web scraping for product data
2. **MercadoLibre**: OAuth2 auth + product publishing API
3. **AI Services**: Product description/spec generation (via external API)
4. **Image Processing**: Upscaling, format conversion

## Coding Standards

### Type Hints (MANDATORY)

```python
# ✅ Good
def get_product_by_id(product_id: int) -> Product | None:
    return Product.objects.filter(id=product_id).first()

# ❌ Bad - missing type hints
def get_product_by_id(product_id):
    return Product.objects.filter(id=product_id).first()
```

### Imports

- Use **absolute imports**: `from aiecommerce.models.product import Product`
- NOT relative imports: `from .models import Product`

### Database

- Use PostgreSQL-specific features when helpful: `ArrayField`, `JSONField`, `HStoreField`
- **NEVER auto-run migrations** - user must explicitly run `python manage.py migrate`
- Use `.select_related()` and `.prefetch_related()` to avoid N+1 queries

### Views

- Prefer **Class-Based Views** (CBV) over function-based views
- Keep views thin - move logic to services
- Use DRF serializers for API validation

### Environment Variables

- All secrets in `.env` (use `django-environ`)
- Never hardcode credentials

## Testing Guidelines

### Framework & Location

- Use **pytest** with `pytest-django`
- Tests in `aiecommerce/tests/` mirroring app structure
- Shared fixtures in `aiecommerce/tests/factories.py` (uses `model_bakery`)

### Naming Conventions

```python
# File: test_<feature>.py
# Function: test_<behavior>_<scenario>

@pytest.mark.django_db
def test_enrich_product_content_success(product_factory):
    product = product_factory(content=None)
    result = enrich_product_content(product)
    assert result.content is not None
```

### Test Structure (Arrange-Act-Assert)

```python
@pytest.mark.django_db
def test_normalize_product_creates_master_record():
    # Arrange
    raw = baker.make("ProductRawWeb", name="Laptop HP")

    # Act
    master = normalize_product(raw)

    # Assert
    assert master.name == "Laptop HP"
    assert master.source == "tecnomega"
```

### Fixtures

- Use `model_bakery` for test data: `baker.make("Product", name="Test")`
- Mock external APIs (HTTP, Celery tasks)
- Use `freezegun` for time-dependent tests

### Coverage Requirements

- Happy path + edge cases + failure scenarios
- Test boundaries: empty lists, None values, invalid IDs
- No trivial tests (tests must have assertions)

### Test Execution Rules (IMPORTANT)

- **DO NOT auto-generate tests** unless explicitly requested
- **DO NOT auto-run tests** after code changes
- When asked to "generate tests", create test files in a **separate step** (don't modify prod code)

## Code Review Focus

### What to focus on in reviews

When reviewing changes, prioritize:

1. **Correctness & bugs**
   - Spot logical errors, missing edge-case handling, and incorrect queryset usage.
   - Check for improper use of `select_related` / `prefetch_related` where N+1 queries are likely.
   - Verify that database migrations match model changes and avoid destructive operations without safeguards.

2. **Security (Django-specific)**
   - Ensure no use of `csrf_exempt` unless explicitly justified in a comment.
   - Check that user input is validated and not directly interpolated into SQL or templates.
   - Confirm permissions:
     - Views and DRF viewsets use appropriate authentication/permission classes.
     - Sensitive views are protected with `login_required` or equivalent.
     - Verify that API views use `ApiKeyAuthentication` and `IPWhitelistPermission` (globally set in `REST_FRAMEWORK` defaults). Any view that overrides `permission_classes` should have explicit justification.
   - Watch for XSS/HTML injection issues in templates and API responses.

3. **Django & DRF best practices**
   - Prefer Django ORM over raw SQL unless clearly justified.
   - Encourage using model methods or managers for business logic instead of views/templates.
   - In DRF:
     - Use serializers for input/output validation.
     - Check that viewsets use proper HTTP methods and return appropriate status codes.

4. **Testing**
   - If a PR changes logic, suggest adding or updating tests.
   - Prefer `pytest`/Django TestCase patterns used in this repo.
   - Ask for tests for:
     - New views, serializers, or model logic.
     - Security-sensitive behavior and permissions.
   - Highlight missing coverage for edge cases (empty querysets, invalid data, permission failures).

5. **Performance**
   - Identify obvious inefficiencies (e.g., loops over querysets causing many DB hits).
   - Suggest using annotations, `values`, or `exists` where suitable.
   - Flag heavy operations in request/response cycles that might belong in tasks (Celery, background jobs).

6. **Architecture & readability**
   - Encourage small, single‑responsibility views, serializers, and services.
   - Keep models lean; complex domain logic can go into service modules or domain layer.
   - Suggest refactoring large functions/classes into smaller units when it improves clarity.

7. **Styling & consistency**
   - Follow PEP 8 and Django style where possible.
   - Keep imports sorted and unused imports removed.
   - Prefer consistent naming:
     - `ModelNameView`, `ModelNameSerializer`, `ModelNameForm`, etc.
   - Ensure templates follow the existing block structure and naming conventions.

## How to respond

When leaving review comments:

- Be concise and specific; point to the exact lines and explain _why_ something should change.
- When possible, propose a concrete Django‑idiomatic code snippet.
- If the change is acceptable but could be improved, prefix with: "Optional improvement:".
- If the issue is critical (security, data loss), clearly mark it as "High priority".

## Things to ignore

- Do **not** suggest framework changes (e.g., switching away from Django).
- Do **not** rewrite the entire file if only small edits are needed; focus on the diff.
- Do **not** enforce different patterns than the dominant ones already used in this repository unless there is a clear bug or risk.

## Workflow Guidelines

- **Plan First:** Always propose a bulleted plan of files to create/edit before generating code.
- **Incremental Changes:** Break large tasks into small, verifiable steps.
- **No Auto-Commit:** Do **NOT** automatically commit changes.

## Documentation Resources

- [HTTPS Setup for Local Development](../docs/README_HTTPS.md) - OAuth2 callback setup
- [MercadoLibre Integration](../docs/mercadolibre-verification.md) - API verification
- [AI Content Pipeline](../docs/mercadolibre/ai_content_pipeline.md) - Product enrichment flow
- [Celery Guide](../docs/infrastructure/celery_guide.md) - Background task setup
- [API Authentication](../docs/api-authentication.md) - API key and IP whitelisting setup

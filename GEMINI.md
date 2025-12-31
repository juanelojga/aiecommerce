# GEMINI.md – Project Context & Guidelines

## 1. Project Overview
This is a robust **Django + PostgreSQL** backend project.
- **Tech Stack:** Django 5.x, Python 3.12, PostgreSQL.
- **Testing:** `pytest` + `pytest-django` + `model_bakery`.
- **Tooling:** Docker, Ruff (linting/formatting), MyPy (strict typing).
- **Architecture:** Modular "Apps" structure with split models and views packages.

## 2. Project Structure & Organization
**Strictly** adhere to this file organization. Do not use single `models.py` or `views.py` files for apps.

### App Layout
New functionality must follow this directory structure:
```text
aiecommerce/
├── models/             # MODULE: Split models by domain entity
│   ├── __init__.py     # MUST export models: `from .user import User`
│   ├── user.py
│   └── profile.py
├── views/              # MODULE: Split views by feature/resource
│   ├── __init__.py
│   ├── auth_views.py
│   └── profile_views.py
├── services/           # PURE PYTHON: Business logic isolation
│   ├── __init__.py
│   └── auth_service.py
├── urls.py
├── admin.py
└── tests/              # Mirrors app structure
    ├── fixtures.py     # App-specific fixtures (factories)
    └── views/          # Tests specific to view modules
````

## 3. Coding Standards & Tooling

### Python & Django

  - **File Organization:** Each class **must** be defined in its own file.
  - **Typing:** All new code (functions, methods, arguments) **must** have valid Python type hints.
  - **Linting:** All code must pass `ruff check` and `ruff format`.
  - **Imports:** Use absolute imports (e.g., `from apps.users.models import User`).
  - **Views:** Keep views "thin" (parsing, validation, response only). Move business logic to `services/`.
  - **CBVs:** Prefer Class-Based Views (Django Generic or DRF) over function-based views.

### Database

  - **PostgreSQL:** Use Postgres-specific features (e.g., `ArrayField`, `JSONField`) where appropriate.
  - **Migrations:** **NEVER** run `python manage.py migrate` automatically.
  - **Secrets:** Never use hardcoded secrets. Use environment variables (via `os.environ` or `django-environ`).

## 4. Test Generation Guidelines

**Strict Rules:**
- Do **NOT** generate tests in the same iteration as feature code unless explicitly asked.
- Do **NOT** execute unit test cases after a change is made unless specifically requested.

### When to Generate Tests

  - **Separate Iteration:** When I say "now generate tests", only create or update `tests/` files.
  - **No Code Mod:** Do not modify production code while writing tests unless fixing clear bugs discovered during the process.
  - **Scope:** Prefer unit or small integration tests over broad end‑to‑end tests.

### Test Style & Structure

  - **Framework:** `pytest` + `pytest-django`.
  - **Location:** Mirror app structure under `tests/apps/<app_name>/`.
  - **Naming:**
      - Files: `test_<feature>.py`.
      - Functions: `test_<unit_of_behavior>`.
  - **Structure:** Follow **Arrange–Act–Assert**. Focus on one behavior per test.
  - **DB Access:** Use `@pytest.mark.django_db` only when hitting the database.
  - **Example Pattern:**
    ```python
    import pytest
    from django.urls import reverse

    @pytest.mark.django_db
    def test_login_view_rejects_invalid_credentials(client):
        url = reverse("accounts:login")
        response = client.post(url, {"username": "foo", "password": "wrong"})
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    ```

### Fixtures, Factories & Mocking

  - **Setup:** Use pytest fixtures, not inline setup in every test.
  - **Factories:** Use `model_bakery` (preferred) or `factory_boy` for models. Avoid hard-coded objects.
  - **Location:** Shared fixtures in `conftest.py`; app-specific in `apps/<name>/tests/fixtures.py`.
  - **External Services:** Mock HTTP calls, emails, and APIs. Use `freezegun` for time-dependent logic.
  - **Example Fixture:**
    ```python
    # apps/accounts/tests/fixtures.py
    import pytest
    from model_bakery import baker

    @pytest.fixture
    def user(db):
        return baker.make("auth.User")
    ```

### Coverage & Scenarios

  - **Requirements:** Include happy-path, edge cases, and at least one failure/validation scenario.
  - **Boundaries:** Test empty input, `None`, invalid IDs, and permission errors.
  - **Avoid:** Do not write trivial tests that run without asserting results.

### AI Test Safety Rules

  - **Behavior:** Generated tests must reflect current code behavior, not change it implicitly.
  - **Stability:** Do not introduce flaky tests (no sleep-based timing or real network calls).
  - **Implementation Details:** Do not assert on private helpers or exact log messages unless specified.

## 5. Workflow & Interaction

  - **Plan First:** Always propose a bulleted plan of files to create/edit before generating code.
  - **Incremental Changes:** Break large tasks into small, verifiable steps.
  - **Diffs:** Show diffs for all proposed changes.

## 6. Example Prompts

  - *"Create a `Subscription` model in `apps/billing/models/subscription.py` with fields: user (FK), plan, status. Export it in `__init__.py`."*
  - *"Refactor the invoice calculation logic from `apps/billing/views/invoice.py` into `apps/billing/services/calculation.py`."*
  - *"Now generate tests for the `Subscription` model using the rules in GEMINI.md, covering creation and status validation."*

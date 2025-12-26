# GitHub Copilot Code Review Instructions – Django Project

## Project context

- This is a Django web application using:
  - Django 4.x (function-based/class-based views, Django ORM, migrations).
  - Django REST Framework for APIs (if applicable).
  - PostgreSQL as the main database.
- Follow Django’s official best practices for security, performance, and style.

## What to focus on in reviews

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

- Be concise and specific; point to the exact lines and explain *why* something should change.
- When possible, propose a concrete Django‑idiomatic code snippet.
- If the change is acceptable but could be improved, prefix with: “Optional improvement:”.
- If the issue is critical (security, data loss), clearly mark it as “High priority”.

## Things to ignore

- Do **not** suggest framework changes (e.g., switching away from Django).
- Do **not** rewrite the entire file if only small edits are needed; focus on the diff.
- Do **not** enforce different patterns than the dominant ones already used in this repository unless there is a clear bug or risk.

# django models testing best practices

For Django models, aim to test behavior and business rules (constraints, methods, signals) rather than Django’s own ORM internals, using pytest, pytest-django, and model factories for clean, isolated tests. Organize tests to mirror your apps and model modules, and rely on factories/fixtures plus database-backed tests that focus on meaningful outcomes and edge cases.[^1][^2][^3][^4][^5]

## What to test on models

- Custom methods: Test model methods (like `full_name`, `get_active()`, `calculate_total()`) as pure units: given certain field values and related objects, assert the returned value or queryset matches expectations.[^6][^1]
- Constraints and validation: For `UniqueConstraint` and `CheckConstraint`, write tests that attempt invalid saves and assert that `IntegrityError` or `ValidationError` is raised, instead of only asserting `unique=True` on the field.[^7][^8]
- Signals and side effects: If `post_save` or `pre_save` signals create related objects or trigger logic, assert those effects (e.g., count created objects, check field changes), keeping the signal logic as thin as possible.[^9][^1]


## What not to over-test

- Django internals: Do not test that `db_index=True` actually creates an index in the database; Django already guarantees that. Instead, if important, assert that the field has `db_index=True` or the right `choices`, `null`, or `blank` configuration via `model._meta.get_field("field")`.[^10][^1]
- Basic CRUD: Avoid exhaustive “create/update/delete” tests that just restate the ORM; focus on domain rules such as “only one active headquarters per partner” or “email or phone must be set”.[^8][^11]


## Using pytest, factories, and fixtures

- Prefer pytest + pytest-django: Use function-style tests, `@pytest.mark.django_db` for DB access, and native `assert` statements for better failure messages and simpler code.[^2][^12]
- Use factories over static fixtures: Libraries like `factory_boy` or `model_bakery` let you generate valid model instances with sensible defaults, making tests less brittle than big JSON/YAML fixtures while still easy to customize per test.[^3][^4][^13]
- Scope fixtures thoughtfully: Use function-scoped factories for most model instances, and only use module/session-scoped fixtures for expensive shared setup to keep tests fast and deterministic.[^4][^14]


## Structure and organization

- Mirror app and model layout: Place tests in `tests/` packages inside each app (`apps/billing/tests/test_models_subscription.py`), roughly mirroring `apps/billing/models/subscription.py`, so navigation is obvious.[^5]
- Group by behavior, not type: Within model tests, group functions by behavior (e.g., `TestSubscriptionConstraints`, `TestSubscriptionManager`, `TestSubscriptionSignals`) rather than dumping everything into one giant test class.[^1][^5]
- Keep tests small and focused: One assertion per behavior is ideal; if parametrizing with pytest, use `@pytest.mark.parametrize` to cover multiple inputs/outputs for the same rule without duplicating boilerplate.[^12][^2]


## Recommended patterns and examples

- Factory-based instance fixture:

```python
@pytest.mark.django_db
def test_user_full_name(user_factory):
    user = user_factory(first_name="Ada", last_name="Lovelace")
    assert user.full_name == "Ada Lovelace"
```

This pattern combines a factory-based fixture with a focused assertion on a derived property.[^3][^4]
- Constraint test:

```python
@pytest.mark.django_db
def test_partner_has_only_one_headquarter(partner_factory, office_factory):
    partner = partner_factory()
    office_factory(partner=partner, headquarter=True)
    with pytest.raises(IntegrityError):
        office_factory(partner=partner, headquarter=True)
```

This asserts the actual business rule enforced by a conditional `UniqueConstraint` rather than just configuration.[^7][^8]

If you share a concrete model (e.g., subscriptions, invoices, accounts), a set of model-specific test cases and factory shapes can be sketched tailored to your Django + PostgreSQL project.
<span style="display:none">[^15][^16][^17][^18][^19][^20]</span>

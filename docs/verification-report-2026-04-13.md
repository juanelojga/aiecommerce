# Django Verification Report

- **Date:** 2026-04-13
- **Branch:** `feat/general-code-check`
- **Scope:** Full CI-parity audit (`ruff`, `mypy`, `pytest`, Django system + migration checks) plus diff review against `main`.

## Context

Triggered by a `/django-verification` run to confirm the branch is safe to open as a pull request. The audit is read-only: no source files were modified. Checks mirror the CI parity commands documented in `CLAUDE.md`.

## Summary

**Recommendation: PASS.** Branch meets full CI parity and is safe to open as a PR. Two first-party deprecation warnings should be addressed opportunistically but are not regressions introduced by this branch.

## Results

| Phase | Check | Command | Result |
|-------|-------|---------|--------|
| Lint | Ruff lint | `ruff check .` | ✅ All checks passed |
| Format | Ruff format | `ruff format --check .` | ✅ 278 files already formatted |
| Types | Mypy | `mypy .` | ✅ No issues in 174 source files |
| Migrations | Pending migrations | `manage.py makemigrations --check` | ✅ No changes detected |
| Tests | Pytest suite | `pytest` | ✅ **684 passed**, 0 failed, 46 warnings (4.87s) |
| Django | System check | `manage.py check` | ✅ 0 issues |
| Git | Working tree | `git status` | ✅ Clean |

## Diff vs `main`

9 files changed, +2554 / -0 lines. All additions are documentation or lockfile entries:

- `.agents/skills/django-patterns/SKILL.md`
- `.agents/skills/django-security/SKILL.md`
- `.agents/skills/django-tdd/SKILL.md`
- `.agents/skills/django-verification/SKILL.md`
- `.claude/skills/django-{patterns,security,tdd,verification}` (symlinks)
- `skills-lock.json`

No production code, migrations, or configuration changed on this branch.

## Warnings worth addressing (non-blocking)

1. **`datetime.utcnow()` deprecation** — `aiecommerce/services/scrape_tecnomega_impl/coordinator.py:42`. Python 3.12 flags this; replace with `datetime.now(datetime.UTC)` before a future Python upgrade.
2. **pandas `FutureWarning`** — `aiecommerce/services/price_list_impl/domain.py:30`. Assigning object values (`['CAT A' 'CAT B']`) into a `float64` column will raise in a future pandas release; cast the column to `object` explicitly before assignment.
3. **Third-party `httplib2` / `pyparsing` `DeprecationWarning`s** — upstream issues, no action required locally.
4. **Missing `staticfiles/` during tests** — cosmetic `UserWarning`; resolved by `collectstatic` in deploy pipelines and harmless in the test environment.

## Phases not executed

The following verification phases were skipped because they require tooling not installed in the local venv, network access, or production-only context. They are expected to run in CI or during staging/deploy preparation:

- Security scanners: `pip-audit`, `safety`, `bandit`
- `manage.py check --deploy` (requires production settings)
- `collectstatic`
- N+1 / query-count performance profiling
- API schema generation (DRF)
- Log-file inspection

## How to reproduce

From the repository root with the project virtualenv active:

```bash
venv/bin/ruff check .
venv/bin/ruff format --check .
venv/bin/mypy .
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/python manage.py check
venv/bin/python -m pytest
```

## Follow-up: previously skipped phases (executed 2026-04-13)

Security scanners and the remaining deployment/operational checks were run on a follow-up pass. Tools not previously present (`pip-audit`, `bandit`, `safety`) were installed into `venv/` ephemerally for this audit and are **not** added to `requirements*.txt`.

| Phase | Check | Command | Result |
|-------|-------|---------|--------|
| Security | pip-audit | `venv/bin/pip-audit` | ⚠️ 57 known vulnerabilities across 18 packages |
| Security | bandit | `venv/bin/bandit -r aiecommerce -x aiecommerce/tests` | ⚠️ 1 low-severity issue (B101 `assert` use) |
| Security | safety | `venv/bin/safety scan` / `safety check` | ⛔ Blocked — `scan` requires interactive login; legacy `check` raises `Unhandled exception: 'pytest'` |
| Django | Deploy check | `manage.py check --deploy` | ⚠️ 6 warnings (expected under dev settings) |
| Static | Collectstatic | `manage.py collectstatic --noinput --dry-run` | ✅ 171 files would be collected; no errors |
| Perf | N+1 / query counts | _n/a_ | ⛔ Not executed — no `django-silk` / `nplusone` installed |
| API | DRF schema | _n/a_ | ⛔ Not executed — no schema generator (`drf-spectacular` / `drf-yasg`) configured in `settings.py` |
| Logs | Log-file inspection | _n/a_ | ℹ️ No `logs/` directory and no file handler in settings — logs stream to stdout under Docker |

### pip-audit details

57 advisories across 18 packages. Highlights (top priorities for upgrade):

- **django 6.0** — 12 CVEs fixed in 6.0.2 / 6.0.3 / 6.0.4 (includes CVE-2026-25674, CVE-2026-33033, CVE-2026-4292). Recommend bumping to the latest 6.0.x patch release.
- **aiohttp 3.13.2** — 18 CVEs fixed in 3.13.3 / 3.13.4.
- **cryptography 46.0.3** — 3 CVEs fixed in 46.0.5 / 46.0.6 / 46.0.7.
- **pillow 12.0.0** — 2 CVEs fixed in 12.1.1 / 12.2.0.
- **pyopenssl 25.3.0**, **werkzeug 3.1.4**, **requests 2.32.5**, **protobuf 6.33.2**, **pytest 9.0.2**, **pygments 2.19.2**, **urllib3 2.6.2**, **filelock 3.20.1**, **pyasn1 0.6.1**, **virtualenv 20.35.4**, **pdfminer-six 20251107**, **rembg 2.0.61** — each have patch-level fixes available.
- **diskcache 5.6.3** — CVE-2025-69872 reported with no fix version yet; track upstream.
- **pip 24.0** — 4 advisories; upgrade the venv's pip to ≥ 26.0.

None of the CVEs are introduced by this branch (which only adds documentation / skill files); they reflect the pinned dependency baseline on `main`. Remediation should be a separate dependency-bump PR.

### bandit details

Single low-severity / high-confidence finding:

- `aiecommerce/services/mercadolibre_publisher_impl/batch_orchestrator.py:91` — `assert isinstance(published_ids, list)`. Runtime `assert` is stripped under `python -O`. Consider replacing with an explicit type check or `typing.cast(...)` if the narrowing is purely for mypy. Low risk; not blocking.

### safety blocker

Modern `safety scan` requires an interactive account login before it will run; the legacy `safety check` path raises an unhandled `'pytest'` key error against the current environment. Equivalent CVE coverage is already provided by `pip-audit` above, so this is informational. To unblock, either run `safety auth login` interactively or rely on `pip-audit` going forward.

### `manage.py check --deploy` warnings

All 6 warnings are the standard dev-settings deltas and are expected to be set by the production environment / reverse proxy, not the repo defaults:

- `security.W004` `SECURE_HSTS_SECONDS` unset
- `security.W008` `SECURE_SSL_REDIRECT` not `True`
- `security.W009` `SECRET_KEY` is dev placeholder
- `security.W012` `SESSION_COOKIE_SECURE` not `True`
- `security.W016` `CSRF_COOKIE_SECURE` not `True`
- `security.W018` `DEBUG=True`

Action: confirm the production settings / environment variables override all six. No repo change required.

### N+1 / query profiling — not executed

Neither `django-silk` nor `nplusone` is installed. Unblock by adding one as a dev dependency and wiring its middleware into `settings.py` under a `DEBUG`-only branch, then replaying representative API flows under `pytest` with `CaptureQueriesContext` or the Silk UI.

### API schema — not executed

`settings.py` wires vanilla DRF only; no `drf-spectacular` or `drf-yasg` app is installed. Unblock by adding `drf-spectacular`, registering its `AutoSchema` as `DEFAULT_SCHEMA_CLASS`, and running `manage.py spectacular --file schema.yml`.

### Log-file inspection

There is no `logs/` directory in the repo and no file-based handler in `settings.LOGGING`; logs are streamed to stdout and captured by the Docker runtime (`docker compose logs`). No stale log artefacts to inspect.

### Follow-up recommendation

Open a separate PR to address the `pip-audit` findings (dependency bumps, grouped by package family). The current branch remains documentation-only and does not need to block on those upgrades.

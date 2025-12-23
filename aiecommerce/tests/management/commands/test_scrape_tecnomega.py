import io
from typing import Any, cast

import pytest
from django.core.management.base import CommandError

from aiecommerce.management.commands.scrape_tecnomega import Command as ScrapeCommand
from aiecommerce.services.scrape_tecnomega_impl.config import ScrapeConfig


class _FakeCoordinator:
    """Test double for ScrapeCoordinator that records constructor args and run calls."""

    def __init__(
        self, *, config: Any, fetcher: Any, parser: Any, mapper: Any, persister: Any, reporter: Any, previewer: Any
    ):
        self.config = config
        self.fetcher = fetcher
        self.parser = parser
        self.mapper = mapper
        self.persister = persister
        self.reporter = reporter
        self.previewer = previewer
        self.run_called = False

    def run(self) -> None:
        self.run_called = True


def _make_command() -> Any:
    # Cast to Any to avoid mypy signature and OutputWrapper type mismatches in tests
    cmd = cast(Any, ScrapeCommand())
    # Capture outputs
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    return cmd


def test_handle_success_uses_defaults_and_runs_coordinator(monkeypatch):
    # Patch the ScrapeCoordinator used inside the command module
    import aiecommerce.management.commands.scrape_tecnomega as mod

    fake_holder = {}

    def factory(**kwargs: Any) -> _FakeCoordinator:
        fake = _FakeCoordinator(**kwargs)
        fake_holder["instance"] = fake
        return fake

    monkeypatch.setattr(mod, "ScrapeCoordinator", lambda **kwargs: factory(**kwargs))

    cmd = _make_command()

    # Run with no options -> defaults from ScrapeConfig
    cmd.handle()

    out = cmd.stdout.getvalue()

    # Messages
    assert "Initializing scrape process" in out
    assert "Starting scrape for categories" in out
    assert "Scrape process completed successfully" in out

    # Coordinator constructed and run invoked
    fake = fake_holder["instance"]
    assert fake.run_called is True

    # Config defaults applied
    assert fake.config.dry_run is False
    # Use the defaults as computed by ScrapeConfig (may depend on settings)
    assert fake.config.categories == ScrapeConfig().categories


def test_handle_dry_run_and_custom_categories(monkeypatch):
    import aiecommerce.management.commands.scrape_tecnomega as mod

    fake_holder = {}

    def factory(**kwargs: Any) -> _FakeCoordinator:
        fake = _FakeCoordinator(**kwargs)
        fake_holder["instance"] = fake
        return fake

    monkeypatch.setattr(mod, "ScrapeCoordinator", lambda **kwargs: factory(**kwargs))

    cmd = _make_command()

    categories = ["laptops", "desktops"]
    cmd.handle(categories=categories, dry_run=True)

    out = cmd.stdout.getvalue()
    assert "-- DRY RUN MODE --" in out
    assert "Starting scrape for categories" in out

    fake = fake_holder["instance"]
    assert fake.run_called is True
    assert fake.config.dry_run is True
    assert fake.config.categories == categories


def test_handle_configuration_error_raises_commanderror(monkeypatch):
    # No need to patch coordinator because config creation will fail before it's used
    cmd = _make_command()

    with pytest.raises(CommandError) as exc:
        # Empty categories should violate ScrapeConfig __post_init__
        cmd.handle(categories=[], dry_run=False)

    assert "Configuration error" in str(exc.value)


def test_handle_unexpected_exception_wrapped_in_commanderror(monkeypatch):
    import aiecommerce.management.commands.scrape_tecnomega as mod

    class _BoomCoordinator(_FakeCoordinator):
        def run(self) -> None:  # type: ignore[override]
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "ScrapeCoordinator", lambda **kwargs: _BoomCoordinator(**kwargs))

    cmd = _make_command()

    with pytest.raises(CommandError) as exc:
        cmd.handle()

    # Ensure our error message is surfaced through CommandError
    assert "An unexpected error occurred: boom" in str(exc.value)

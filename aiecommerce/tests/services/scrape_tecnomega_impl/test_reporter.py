import pytest

from aiecommerce.services.scrape_tecnomega_impl.reporter import ScrapeReporter


class _Buffer:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def write(self, msg: str) -> None:
        self.messages.append(msg)


class _Style:
    # Mimic django BaseCommand.style API by returning the message unchanged
    def SUCCESS(self, msg: str) -> str:  # noqa: N802 (match Django style method name)
        return msg

    def ERROR(self, msg: str) -> str:  # noqa: N802
        return msg

    def NOTICE(self, msg: str) -> str:  # noqa: N802
        return msg

    def WARNING(self, msg: str) -> str:  # noqa: N802
        return msg


class _FakeCommand:
    def __init__(self) -> None:
        self.stdout: _Buffer = _Buffer()
        self.stderr: _Buffer = _Buffer()
        self.style: _Style = _Style()


@pytest.fixture
def command() -> _FakeCommand:
    return _FakeCommand()


def test_track_success_updates_count_and_writes_success(command):
    reporter = ScrapeReporter(command)

    reporter.track_success("laptops", 5)

    # total count updated
    assert reporter.total_scraped_count == 5

    # success message written to stdout
    assert any("Successfully processed 5 items for category 'laptops'." in msg for msg in command.stdout.messages)


def test_track_failure_appends_and_writes_error(command):
    reporter = ScrapeReporter(command)

    err = ValueError("boom")
    reporter.track_failure("phones", err)

    # category recorded as failed
    assert reporter.failed_categories == ["phones"]

    # error message written to stderr
    assert any("Failed to process category 'phones': boom" in msg for msg in command.stderr.messages)


def test_print_summary_no_failures_outputs_success_and_total(command):
    reporter = ScrapeReporter(command)
    reporter.track_success("keyboards", 3)
    reporter.track_success("mice", 2)

    reporter.print_summary(dry_run=False)

    # Notice header and finish lines
    assert any("--------------------" in msg for msg in command.stdout.messages)
    assert any("Scrape process finished." in msg for msg in command.stdout.messages)

    # Total items line
    assert any("Total items processed: 5" == msg for msg in command.stdout.messages)

    # Success summary when no failures
    assert any("All categories processed successfully." in msg for msg in command.stdout.messages)

    # No warning when dry_run is False
    assert not any("Dry run" in msg for msg in command.stdout.messages)


def test_print_summary_with_failures_outputs_error_list(command):
    reporter = ScrapeReporter(command)
    reporter.track_success("cpus", 1)
    reporter.track_failure("gpus", RuntimeError("x"))
    reporter.track_failure("ram", RuntimeError("y"))

    reporter.print_summary(dry_run=False)

    # Error summary with failed categories, on stderr
    assert any("Completed with errors. Failed categories: gpus, ram" in msg for msg in command.stderr.messages)


def test_print_summary_dry_run_outputs_warning(command):
    reporter = ScrapeReporter(command)
    reporter.print_summary(dry_run=True)

    assert any("Dry run complete. No database changes were made." in msg for msg in command.stdout.messages)

from unittest.mock import ANY, MagicMock

from aiecommerce.services.scrape_tecnomega_impl.config import ScrapeConfig
from aiecommerce.services.scrape_tecnomega_impl.coordinator import ScrapeCoordinator


def make_coordinator(dry_run: bool = False, categories=None):
    if categories is None:
        categories = ["cat1"]

    config = ScrapeConfig(base_url="https://example.com/search", categories=categories, dry_run=dry_run)

    fetcher = MagicMock()
    parser = MagicMock()
    mapper = MagicMock()
    persister = MagicMock()
    reporter = MagicMock()
    previewer = MagicMock()

    coord = ScrapeCoordinator(
        config=config,
        fetcher=fetcher,
        parser=parser,
        mapper=mapper,
        persister=persister,
        reporter=reporter,
        previewer=previewer,
    )
    return coord, config, fetcher, parser, mapper, persister, reporter, previewer


class TestProcessSingleCategory:
    def test_returns_empty_when_fetcher_returns_no_content(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator()

        fetcher.fetch.return_value = ""  # no content

        result = coord._process_single_category("cat1")

        assert result == []
        fetcher.fetch.assert_called_once_with(cfg.get_base_url(), "cat1")
        parser.parse.assert_not_called()
        mapper.to_entity.assert_not_called()
        persister.save_bulk.assert_not_called()
        previewer.show_preview.assert_not_called()

    def test_returns_empty_when_parser_returns_no_dtos(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator()

        fetcher.fetch.return_value = "<html>ok</html>"
        parser.parse.return_value = []

        result = coord._process_single_category("cat1")

        assert result == []
        parser.parse.assert_called_once_with("<html>ok</html>")
        mapper.to_entity.assert_not_called()
        persister.save_bulk.assert_not_called()

    def test_dry_run_maps_and_previews_without_persisting(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator(dry_run=True)

        fetcher.fetch.return_value = "<html>ok</html>"
        dtos = [object(), object()]
        parser.parse.return_value = dtos
        # mapped entities
        entities = [object(), object()]

        # mapper.to_entity called per dto; simulate by returning from side_effect list
        mapper.to_entity.side_effect = entities

        result = coord._process_single_category("laptops")

        # ensure mapper called with scrape_session_id and category
        assert mapper.to_entity.call_count == 2
        for call_args in mapper.to_entity.call_args_list:
            # args: dto, scrape_session_id, category
            assert call_args.args[2] == "laptops"
            assert call_args.args[1] == coord.scrape_session_id

        previewer.show_preview.assert_called_once()
        # First arg is category, second is the list of entities
        args, kwargs = previewer.show_preview.call_args
        assert args[0] == "laptops"
        assert args[1] == entities

        persister.save_bulk.assert_not_called()
        assert result == entities

    def test_persists_when_not_dry_run(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator(dry_run=False)

        fetcher.fetch.return_value = "<html>ok</html>"
        parser.parse.return_value = [object(), object(), object()]
        mapped = [object(), object(), object()]
        mapper.to_entity.side_effect = mapped

        # persister returns whatever it saves (could be same or transformed)
        saved = [object()]
        persister.save_bulk.return_value = saved

        result = coord._process_single_category("tablets")

        persister.save_bulk.assert_called_once_with(mapped)
        previewer.show_preview.assert_not_called()
        assert result == saved


class TestRunAndReporting:
    def test_run_reports_success_for_each_category_and_prints_summary(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator(dry_run=True, categories=["c1", "c2"])

        # Make internals simple: always return N fake products
        fetcher.fetch.return_value = "<html>ok</html>"
        parser.parse.return_value = [object(), object()]
        # return a fresh object per call regardless of number of calls/categories
        mapper.to_entity.side_effect = lambda *args, **kwargs: object()

        coord.run()

        # Two categories with two products each
        reporter.track_success.assert_any_call("c1", 2)
        reporter.track_success.assert_any_call("c2", 2)
        # Summary printed with dry_run flag
        reporter.print_summary.assert_called_once_with(True)

    def test_run_reports_failure_when_exception_occurs_but_continues(self):
        coord, cfg, fetcher, parser, mapper, persister, reporter, previewer = make_coordinator(dry_run=True, categories=["ok", "boom", "ok2"])

        def fetch_side_effect(url, category):
            if category == "boom":
                raise RuntimeError("fetch failed")
            return "<html>ok</html>"

        fetcher.fetch.side_effect = fetch_side_effect
        parser.parse.return_value = [object()]
        mapper.to_entity.side_effect = lambda *args, **kwargs: object()

        coord.run()

        reporter.track_success.assert_any_call("ok", 1)
        reporter.track_failure.assert_any_call("boom", ANY)
        reporter.track_success.assert_any_call("ok2", 1)
        reporter.print_summary.assert_called_once_with(True)

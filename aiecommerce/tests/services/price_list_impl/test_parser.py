import io
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from aiecommerce.services.price_list_impl.domain import ParserConfig
from aiecommerce.services.price_list_impl.exceptions import ParsingError
from aiecommerce.services.price_list_impl.parser import XlsPriceListParser


class _FakeCategoryResolver:
    def resolve_categories(self, df: pd.DataFrame) -> pd.DataFrame:  # mimic Protocol
        out = df.copy()
        # Add deterministic category header so parser passes it through
        out["category_header"] = "General"
        return out


def _make_parser(cfg: ParserConfig | None = None) -> XlsPriceListParser:
    return XlsPriceListParser(config=cfg or ParserConfig(), category_resolver=_FakeCategoryResolver())


def test_parse_end_to_end_multiple_pages_and_columns(monkeypatch: Any) -> None:
    # Configure fewer column pairs to simplify the fixture DataFrame
    cfg = ParserConfig(header_row_offset=1, column_pairs=[(0, 1), (2, 3)])

    # Build a DataFrame emulating read_excel(header=None)
    # Page 1 (rows 0..1), separator (row 2), Page 2 (rows 3..4)
    df = pd.DataFrame(
        [
            ["HEADER P1 A", np.nan, "HEADER P1 B", np.nan],  # header row (will be skipped on first page)
            [" item A ", 10.0, "item B", 20.0],  # two columns of items on same row
            [np.nan, np.nan, np.nan, np.nan],  # empty row => page separator
            ["HEADER P2 A", np.nan, "HEADER P2 B", np.nan],  # page 2 header (not skipped)
            ["item C", 30.0, "  ", 40.0],  # second desc is whitespace => will be trimmed and dropped
        ]
    )

    def _fake_read_excel(content: io.BytesIO, header: None) -> pd.DataFrame:  # type: ignore[override]
        # Validate method contract
        assert isinstance(content, io.BytesIO)
        assert header is None
        return df

    monkeypatch.setattr(pd, "read_excel", _fake_read_excel)

    parser = _make_parser(cfg)
    result: List[Dict] = parser.parse(io.BytesIO(b"xls-bytes"))

    # Expect three valid items (item A, item B, item C). The whitespace-only desc should be removed.
    assert len(result) == 3

    # Column names and presence of category fields
    for row in result:
        # Parser guarantees these columns; category info is exposed via 'category_header'
        assert set(row.keys()) >= {"raw_description", "distributor_price"}
        assert "category_header" in row

    # Values normalized and stripped
    descriptions = [r["raw_description"] for r in result]
    prices = [r["distributor_price"] for r in result]
    assert descriptions == ["item A", "item B", "item C"]
    assert prices == [10.0, 20.0, 30.0]


def test_validate_columns_raises_when_insufficient_columns() -> None:
    # Default config requires columns up to index 7; supply only 2 columns
    parser = _make_parser(ParserConfig())
    tiny_df = pd.DataFrame([[1, 2]])
    with pytest.raises(ParsingError):
        parser._validate_columns(tiny_df)  # type: ignore[attr-defined]


def test_load_workbook_wraps_errors(monkeypatch: Any) -> None:
    def _fail_read_excel(content: io.BytesIO, header: None) -> pd.DataFrame:  # type: ignore[override]
        raise ValueError("bad excel")

    monkeypatch.setattr(pd, "read_excel", _fail_read_excel)

    parser = _make_parser()
    with pytest.raises(ParsingError):
        # Trigger via public API to ensure exception propagation
        parser.parse(io.BytesIO(b"broken"))


def test_clean_and_normalize_trims_and_filters() -> None:
    parser = _make_parser()

    # _clean_and_normalize expects 'raw_description' and 'distributor_price' columns
    raw = pd.DataFrame(
        {
            "raw_description": ["  alpha  ", "", "   ", None, "beta"],
            "distributor_price": ["9", None, "5.5", 7, "not-a-number"],
        }
    )

    cleaned = parser._clean_and_normalize(raw)  # type: ignore[attr-defined]

    # Rows kept: "alpha" (9.0), whitespace-only desc removed, empty desc removed,
    # None desc becomes "None" string but keeps if price numeric (7),
    # non-numeric price dropped.
    # Therefore expected two rows: "alpha" and "None"
    assert cleaned == [
        {"raw_description": "alpha", "distributor_price": 9.0},
        {"raw_description": "None", "distributor_price": 7.0},
    ]

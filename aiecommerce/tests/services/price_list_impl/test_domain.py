import numpy as np
import pandas as pd

from aiecommerce.services.price_list_impl.domain import ParserConfig, StandardCategoryResolver


def test_parser_config_defaults() -> None:
    cfg = ParserConfig()
    assert cfg.header_row_offset == 1
    # Expect the full set of default column pairs
    assert cfg.column_pairs == [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]
    assert cfg.start_row_index == 5


def test_standard_category_resolver_resolves_and_ffills_headers() -> None:
    df = pd.DataFrame(
        {
            # StandardCategoryResolver expects these specific columns
            "raw_description": [
                "CAT A",  # header row (price is NaN)
                "item 1",
                np.nan,  # empty row
                "CAT B",  # header row (price is NaN)
                "item 2",
            ],
            "distributor_price": [
                np.nan,  # header -> NaN
                10.0,
                np.nan,  # empty row
                np.nan,  # header -> NaN
                20.0,
            ],
        }
    )

    resolved = StandardCategoryResolver().resolve_categories(df.copy())

    # Expect a new column
    assert "category_header" in resolved.columns

    # Header rows should set the category, others should be forward-filled
    expected = [
        "CAT A",  # header found here
        "CAT A",  # ffilled
        "CAT A",  # ffilled over empty row
        "CAT B",  # new header
        "CAT B",  # ffilled
    ]
    assert resolved["category_header"].tolist() == expected

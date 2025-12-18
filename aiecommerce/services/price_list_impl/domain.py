from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import pandas as pd

from aiecommerce.services.price_list_impl.interfaces import CategoryResolver


@dataclass
class ParserConfig:
    header_row_offset: int = 1
    column_pairs: List[Tuple[int, int]] = field(default_factory=lambda: [(0, 1), (2, 3), (4, 5), (6, 7)])
    start_row_index: int = 5


class StandardCategoryResolver(CategoryResolver):
    def resolve_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        df["category_header"] = np.where((df["price"].isna()) & (df["desc"].notna()), df["desc"], np.nan)
        df["category_header"] = df["category_header"].ffill()
        return df

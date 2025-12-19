from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import pandas as pd

from aiecommerce.services.price_list_impl.interfaces import CategoryResolver


@dataclass
class ParserConfig:
    header_row_offset: int = 1
    column_pairs: List[Tuple[int, int]] = field(default_factory=lambda: [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])
    start_row_index: int = 5


class StandardCategoryResolver(CategoryResolver):
    def resolve_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        # 1. Work on a Copy
        df_copy = df.copy()

        # 2. Normalize Price for Detection
        df_copy["_temp_price"] = pd.to_numeric(df_copy["distributor_price"], errors="coerce")

        # 3. Identify Headers
        is_header = (df_copy["_temp_price"].isna()) & (df_copy["raw_description"].notna())

        # 4. Assign Categories
        df_copy["category_header"] = np.nan
        df_copy.loc[is_header, "category_header"] = df_copy["raw_description"]
        df_copy["category_header"] = df_copy["category_header"].ffill()

        # 5. Apply Fallback Rule
        is_case = df_copy["raw_description"].str.match(r"^CASE", case=False, na=False)
        df_copy.loc[df_copy["category_header"].isna() & is_case, "category_header"] = "CASE"

        # 6. Cleanup
        df_copy = df_copy.drop(columns=["_temp_price"])

        return df_copy

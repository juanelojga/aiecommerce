import io
from typing import Dict, List

import pandas as pd

from aiecommerce.services.price_list_impl.domain import ParserConfig
from aiecommerce.services.price_list_impl.interfaces import (
    CategoryResolver,
    PriceListParser,
)


class XlsPriceListParser(PriceListParser):
    def __init__(
        self,
        config: ParserConfig,
        category_resolver: CategoryResolver,
    ) -> None:
        self.config = config
        self.category_resolver = category_resolver

    def parse(self, content: io.BytesIO) -> List[Dict]:
        df = pd.read_excel(content, header=None)

        separator_indices = [-1] + df[df.isnull().all(axis=1)].index.tolist() + [len(df)]
        pages = []
        for i in range(len(separator_indices) - 1):
            start, end = separator_indices[i] + 1, separator_indices[i + 1]
            page = df.iloc[start:end]
            if not page.empty:
                pages.append(page)

        all_pages_data = []
        for i, page_df in enumerate(pages):
            # Per instruction: Skip the first row only for Page 1.
            if i == 0:
                page_df = page_df.iloc[self.config.header_row_offset :]

            page_linear_data = []
            for desc_col, price_col in self.config.column_pairs:
                chunk = page_df[[desc_col, price_col]].copy()
                chunk.columns = ["desc", "price"]
                page_linear_data.append(chunk)

            if page_linear_data:
                concatenated_page = pd.concat(page_linear_data, ignore_index=True)
                all_pages_data.append(concatenated_page)

        if not all_pages_data:
            return []

        linear_df = pd.concat(all_pages_data, ignore_index=True)
        linear_df.dropna(how="all", inplace=True)

        resolved_df = self.category_resolver.resolve_categories(linear_df)

        final_df = resolved_df.dropna(subset=["desc", "price"]).copy()
        final_df = final_df[final_df["desc"].str.strip() != ""]

        return final_df.to_dict("records")

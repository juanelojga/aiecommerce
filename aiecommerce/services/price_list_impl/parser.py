import io
from typing import Dict, List

import pandas as pd

from aiecommerce.services.price_list_impl.domain import ParserConfig
from aiecommerce.services.price_list_impl.exceptions import ParsingError
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
        """
        Orchestrates the parsing of an XLS price list file by chaining together
        the loading, validation, splitting, extraction, and cleaning steps.
        """

        df = self._load_workbook(content)

        self._validate_columns(df)

        pages = self._split_into_pages(df)

        raw_items_df = self._extract_raw_items(pages)

        resolved_df = self.category_resolver.resolve_categories(raw_items_df)

        cleaned_items = self._clean_and_normalize(resolved_df)

        return cleaned_items

    def _load_workbook(self, content: io.BytesIO) -> pd.DataFrame:
        """
        Loads the content of the XLS file into a pandas DataFrame.
        """

        try:
            return pd.read_excel(content, header=None)

        except (ValueError, OSError) as e:
            raise ParsingError(f"Failed to load workbook: {e}") from e

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validates that the DataFrame has enough columns to satisfy the column
        pair configuration.
        """

        max_col_index = max(col for pair in self.config.column_pairs for col in pair)

        if df.shape[1] <= max_col_index:
            raise ParsingError(
                f"Workbook has {df.shape[1]} columns, but parsing "
                f"configuration requires at least {max_col_index + 1}."
            )

    def _split_into_pages(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """
        Splits the DataFrame into multiple pages based on empty rows.
        """

        separator_indices = [-1] + df[df.isnull().all(axis=1)].index.tolist() + [len(df)]

        pages = []

        for i in range(len(separator_indices) - 1):
            start, end = separator_indices[i] + 1, separator_indices[i + 1]

            page = df.iloc[start:end]

            if not page.empty:
                pages.append(page)

        return pages

    def _extract_raw_items(self, pages: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Extracts and linearizes items from the given pages into a single
        DataFrame with 'desc' and 'price' columns for internal processing.
        """

        all_pages_data = []

        for i, page_df in enumerate(pages):
            if i == 0:
                page_df = page_df.iloc[self.config.header_row_offset :]

            page_linear_data = []

            for desc_col, price_col in self.config.column_pairs:
                if price_col < page_df.shape[1]:
                    chunk = page_df[[desc_col, price_col]].copy()

                    chunk.columns = ["desc", "price"]

                    page_linear_data.append(chunk)

            if page_linear_data:
                concatenated_page = pd.concat(page_linear_data, ignore_index=True)

                all_pages_data.append(concatenated_page)

        if not all_pages_data:
            return pd.DataFrame(columns=["desc", "price"])

        linear_df = pd.concat(all_pages_data, ignore_index=True)

        return linear_df.dropna(how="all")

    def _clean_and_normalize(self, df: pd.DataFrame) -> List[Dict]:
        """
        Cleans and normalizes the DataFrame, converting data types,
        dropping invalid rows, and renaming columns for the final output.
        """

        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        df.dropna(subset=["price"], inplace=True)

        df["desc"] = df["desc"].astype(str).str.strip()

        df = df[df["desc"] != ""]

        df = df.rename(columns={"desc": "raw_description", "price": "distributor_price"})

        final_columns = [
            "raw_description",
            "distributor_price",
            "category",
            "subcategory",
        ]

        output_columns = [col for col in final_columns if col in df.columns]

        return df[output_columns].to_dict("records")

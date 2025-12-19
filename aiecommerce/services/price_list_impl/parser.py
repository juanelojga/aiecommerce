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

        # Step 1: Extract raw data. Result contains headers w/ NaN prices.
        df = self._extract_raw_items(pages)

        # Step 2: Resolve categories. Uses headers to fill categories.
        df = self.category_resolver.resolve_categories(df)

        # Step 3: Clean and normalize. Removes headers, keeps items.
        result = self._clean_and_normalize(df)

        return result

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
        DataFrame with 'raw_description' and 'distributor_price' columns.
        Raw data is preserved, including rows with NaN prices (headers),
        for category resolution in a later step.
        """
        all_pages_data = []
        for i, page_df in enumerate(pages):
            if i == 0:
                page_df = page_df.iloc[self.config.header_row_offset :]

            page_linear_data = []
            for desc_col, price_col in self.config.column_pairs:
                if price_col < page_df.shape[1]:
                    chunk = page_df[[desc_col, price_col]].copy()
                    chunk.columns = ["raw_description", "distributor_price"]
                    page_linear_data.append(chunk)

            if page_linear_data:
                concatenated_page = pd.concat(page_linear_data, ignore_index=True)
                all_pages_data.append(concatenated_page)

        if not all_pages_data:
            return pd.DataFrame(columns=["raw_description", "distributor_price"])

        return pd.concat(all_pages_data, ignore_index=True)

    def _clean_and_normalize(self, df: pd.DataFrame) -> List[Dict]:
        """
        Cleans and normalizes the DataFrame after category resolution.
        This includes converting data types, dropping rows with invalid prices,
        and preparing the data for final output.
        """
        # Work on a copy to avoid SettingWithCopyWarning
        df = df.copy()

        # Step A: Convert price to numeric, coercing errors
        df["distributor_price"] = pd.to_numeric(df["distributor_price"], errors="coerce")

        # Step C: NOW (and only now) drop rows where distributor_price is NaN
        df.dropna(subset=["distributor_price"], inplace=True)

        # Step B: Convert raw_description to string and strip whitespace
        df["raw_description"] = df["raw_description"].astype(str).str.strip()

        df = df[df["raw_description"] != ""]

        # Final columns for the output
        final_columns = [
            "raw_description",
            "distributor_price",
            "category_header",
        ]

        output_columns = [col for col in final_columns if col in df.columns]

        return df[output_columns].to_dict("records")

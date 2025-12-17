import io
from typing import Any, Dict, List, Optional

import pandas as pd
import requests


class PriceListIngestionService:
    """
    A service to fetch and parse a multi-column XLS price list into a structured format.
    """

    def fetch(self, url: str) -> Optional[io.BytesIO]:
        """
        Downloads an XLS file from a URL and returns its content as a BytesIO stream.

        Args:
            url: The URL of the XLS file to download.

        Returns:
            A BytesIO stream with the file content, or None if the download fails.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.RequestException as e:
            # Handle download errors gracefully
            print(f"Error downloading file from {url}: {e}")
            return None

        # Use BytesIO to treat the downloaded content as a file
        return io.BytesIO(response.content)

    def parse(self, file_content: io.BytesIO) -> List[Dict[str, Any]]:
        """
        Parses an XLS file content into a list of product dictionaries.

        Args:
            file_content: A BytesIO stream of the XLS file.

        Returns:
            A list of dictionaries, where each dictionary represents a product
            with 'raw_description', 'distributor_price', and 'category_header'.
        """
        # Ensure stream is at the beginning
        try:
            file_content.seek(0)
        except Exception:
            pass

        # Read the XLS file into a pandas DataFrame
        xls = pd.ExcelFile(file_content)
        df = xls.parse(header=None)

        all_products = []
        column_pairs = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]

        for desc_col, price_col in column_pairs:
            # Check if the column pair exists in the DataFrame
            if desc_col not in df.columns or price_col not in df.columns:
                continue

            # Create a temporary DataFrame for the current column pair
            pair_df = df[[desc_col, price_col]].copy()
            pair_df.columns = ["raw_description", "distributor_price"]

            # Identify category headers
            # A header is where price is NaN but description is not
            pair_df["category_header"] = pair_df.apply(
                lambda row: row["raw_description"]
                if pd.isna(row["distributor_price"]) and pd.notna(row["raw_description"])
                else None,
                axis=1,
            )

            # Forward-fill the category header
            pair_df["category_header"].ffill(inplace=True)

            # Clean the data
            # 1. Drop rows that were only headers (price is still NaN)
            # 2. Drop rows where both description and price are missing
            cleaned_df = pair_df.dropna(subset=["distributor_price"])
            cleaned_df = cleaned_df.dropna(subset=["raw_description", "distributor_price"], how="all")

            # Convert to list of dictionaries
            all_products.extend(cleaned_df.to_dict(orient="records"))

        return all_products

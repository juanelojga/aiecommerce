import io
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import requests


class PriceListIngestionService:
    """
    A service to fetch and parse a multi-column XLS price list into a structured format.
    """

    def get_xls_url(self) -> str:
        """
        Finds the downloadable XLS file URL by following a redirect and swapping the extension.

        This method navigates a common pattern where a generic link redirects to a
        monthly, timestamped file (e.g., .../LISTA-PRECIOS202512.pdf). It captures
        the final URL and modifies it to point to the corresponding XLS version.

        Returns:
            The resolved URL for the XLS file.
        """
        base_url = "http://www.tecnomega.com/envio_promocion_precios.php"

        # Use a context manager for safety. We set stream=True to avoid downloading
        # the whole file, as we only need the final redirected URL from the headers.
        with requests.get(base_url, stream=True) as response:
            final_url = response.url

        # Replace the .pdf extension with .xls, case-insensitively
        xls_url = re.sub(r"\.pdf$", ".xls", final_url, flags=re.IGNORECASE)

        return xls_url

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
        Parses a paginated, multi-column XLS file into a list of product dictionaries.

        This method implements a specific algorithm to handle a complex document structure:
        1.  It identifies pages, which are separated by blocks of empty rows.
        2.  It linearizes the data by reading column pairs in a "zig-zag" sequence
            (Page 1 Col 1 -> P1 Col 2 -> ... -> P2 Col 1 -> ...), creating a
            single continuous list.
        3.  It applies category logic globally, propagating category headers from the
            end of one page-column to the start of the next.

        Args:
            file_content: A BytesIO stream of the XLS file.

        Returns:
            A list of dictionaries, where each dictionary represents a product.
        """
        try:
            file_content.seek(0)
        except (AttributeError, io.UnsupportedOperation):
            pass

        # 1. Load & Detect Pages
        df = pd.read_excel(file_content, header=None)
        page_breaks = df[df.isnull().all(axis=1)].index
        pages_df = []
        last_break = -1
        for pb_index in page_breaks:
            # Check if it's a real break (more than one empty row)
            if pb_index > last_break + 1:
                pages_df.append(df.iloc[last_break + 1 : pb_index])
            last_break = pb_index
        pages_df.append(df.iloc[last_break + 1 :])  # Add the last page

        # 2. Linearize Data (The "Zig-Zag" Unroll)
        all_rows = []
        column_pairs = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]

        for i, page_df in enumerate(pages_df):
            start_row = 3 if i == 0 else 0  # Skip headers only on the first page
            for desc_col, price_col in column_pairs:
                if desc_col < len(page_df.columns) and price_col < len(page_df.columns):
                    # Extract the two columns for the current pair
                    chunk = page_df.iloc[start_row:, [desc_col, price_col]].copy()
                    chunk.columns = ["raw_description", "distributor_price"]
                    all_rows.append(chunk)

        # 3. Apply Category Logic (Global Context)
        if not all_rows:
            return []

        continuous_df = pd.concat(all_rows, ignore_index=True).dropna(how="all")

        # Identify Headers: price is NaN but description has text
        is_header = continuous_df["distributor_price"].isna() & continuous_df["raw_description"].notna()
        continuous_df["category_header"] = continuous_df.loc[is_header, "raw_description"]

        # Propagate the last valid category forward
        continuous_df["category_header"].ffill(inplace=True)

        # Fallback rule for items at the start that missed a header
        # If a category is still NaN, check if the description starts with "CASE"
        continuous_df.loc[
            continuous_df["category_header"].isna() & continuous_df["raw_description"].str.startswith("CASE", na=False),
            "category_header",
        ] = "CASE"

        # 4. Final Clean
        # Remove header rows and rows with no price
        final_df = continuous_df.dropna(subset=["distributor_price"])

        return final_df.to_dict(orient="records")

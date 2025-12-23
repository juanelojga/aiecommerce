import logging

from aiecommerce.services.scrape_tecnomega_impl.parser import HtmlParser


def wrap_table(inner: str, header_cols: int | None = None) -> str:
    thead = ""
    if header_cols is not None:
        ths = "".join(["<th>H</th>" for _ in range(header_cols)])
        thead = f"<thead><tr>{ths}</tr></thead>"
    return f"""
    <html>
      <body>
        <table class=\"table-hover\">
          {thead}
          <tbody>
            {inner}
          </tbody>
        </table>
      </body>
    </html>
    """


class TestParse:
    def test_returns_empty_when_no_product_table(self, caplog):
        html = "<html><body><p>No table here</p></body></html>"
        parser = HtmlParser()

        with caplog.at_level(logging.INFO):
            result = parser.parse(html)

        assert result == []
        # Warning about missing table
        assert any("No product table with class 'table-hover' found." in r.getMessage() for r in caplog.records)

    def test_returns_empty_when_no_rows_in_tbody(self, caplog):
        html = wrap_table("", header_cols=10)
        parser = HtmlParser()

        with caplog.at_level(logging.INFO):
            result = parser.parse(html)

        assert result == []
        assert any("No rows found in table body." in r.getMessage() for r in caplog.records)

    def test_skips_rows_with_insufficient_columns(self):
        # Create a row with fewer than EXPECTED_COLUMN_COUNT (e.g., 5 td)
        short_row = "<tr>" + "".join(["<td>v</td>" for _ in range(5)]) + "</tr>"
        html = wrap_table(short_row, header_cols=10)

        parser = HtmlParser()
        result = parser.parse(html)

        # Should skip the row and return empty list
        assert result == []

    def test_parses_valid_row_with_image_url(self):
        # Build a row with 10 columns; we care about indexes 0..6 and 9 with img
        tds = [
            "<td>CODE123</td>",  # 0 distributor_code
            "<td>Awesome Product</td>",  # 1 raw_description
            "<td>10</td>",  # 2 stock_principal
            "<td>1</td>",  # 3 stock_colon
            "<td>2</td>",  # 4 stock_sur
            "<td>3</td>",  # 5 stock_gye_norte
            "<td>4</td>",  # 6 stock_gye_sur
            "<td>unused7</td>",  # 7 unused
            "<td>unused8</td>",  # 8 unused
            '<td><img src="https://img.test/p.png" /></td>',  # 9 image
        ]
        row = f"<tr>{''.join(tds)}</tr>"
        html = wrap_table(row, header_cols=10)

        parser = HtmlParser()
        result = parser.parse(html)

        assert result == [
            {
                "distributor_code": "CODE123",
                "raw_description": "Awesome Product",
                "stock_principal": "10",
                "stock_colon": "1",
                "stock_sur": "2",
                "stock_gye_norte": "3",
                "stock_gye_sur": "4",
                "image_url": "https://img.test/p.png",
            }
        ]

    def test_parses_valid_row_without_image_sets_none(self):
        # Same as above but no img in the last column
        tds = [
            "<td>C1</td>",
            "<td>Desc</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>x</td>",
            "<td>y</td>",
            "<td></td>",
        ]
        row = f"<tr>{''.join(tds)}</tr>"
        html = wrap_table(row, header_cols=10)

        parser = HtmlParser()
        result = parser.parse(html)

        assert result[0]["image_url"] is None

    def test_skips_row_without_distributor_code(self):
        # distributor_code empty should skip
        tds = [
            "<td>   </td>",  # empty after strip
            "<td>Desc</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>0</td>",
            "<td>x</td>",
            "<td>y</td>",
            "<td></td>",
        ]
        row = f"<tr>{''.join(tds)}</tr>"
        html = wrap_table(row, header_cols=10)

        parser = HtmlParser()
        result = parser.parse(html)

        assert result == []

    def test_logs_header_warning_when_too_few_columns(self, caplog):
        # Header with fewer than expected columns should warn
        row = ""  # no rows
        html = wrap_table(row, header_cols=5)

        parser = HtmlParser()
        with caplog.at_level(logging.WARNING):
            parser.parse(html)

        assert any("Table header has" in rec.getMessage() for rec in caplog.records)

    def test_logs_start_and_summary(self, caplog):
        tds = [
            "<td>ABC</td>",
            "<td>Desc</td>",
            "<td>1</td>",
            "<td>2</td>",
            "<td>3</td>",
            "<td>4</td>",
            "<td>5</td>",
            "<td>6</td>",
            "<td>7</td>",
            '<td><img src="/a.png"></td>',
        ]
        row = f"<tr>{''.join(tds)}</tr>"
        html = wrap_table(row, header_cols=10)

        parser = HtmlParser()
        with caplog.at_level(logging.INFO):
            parser.parse(html)

        messages = [r.getMessage() for r in caplog.records]
        assert any("Starting HTML parsing." in m for m in messages)
        assert any("Found 1 rows to process." in m for m in messages)
        assert any("Successfully parsed 1 valid product rows." in m for m in messages)

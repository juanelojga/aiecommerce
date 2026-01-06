# Tecnomega Detail Sync Command

This document outlines the architecture and usage of the `sync_tecnomega_details` management command. This command is designed for manual, single-item deep-scraping of product details from the Tecnomega website.

## 1. Purpose

The primary use case for this command is to diagnose scraping issues or manually enrich a specific product with detailed information that is not available in the general, high-level scrapes. It follows a "Fetch -> Parse -> Persist" pipeline to retrieve, structure, and save data.

## 2. Usage

The command is executed via `manage.py` and requires a single product code to target a specific `ProductMaster` instance.

### Default (Dry Run)

By default, the command runs in a safe, read-only "dry run" mode. It will perform the fetch and parse steps and print the extracted, structured data to the console without making any changes to the database.

```bash
python manage.py sync_tecnomega_details <product_code>
```

**Example Output (Dry Run):**
```json
{
  "name": "Product Full Name",
  "price": 123.45,
  "currency": "USD",
  "images": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ],
  "attributes": {
    "sku": "MFG-PART-NO",
    "Marca": "BrandName",
    "Peso": "1.5 kg"
  }
}
```

### Live Sync

To disable the dry run and persist the scraped data to the database, use the `--no-dry-run` flag.

```bash
python manage.py sync_tecnomega_details <product_code> --no-dry-run
```

## 3. Architectural Flow

The command orchestrates a sequence of services to perform its task.

### Fetch

- **Component**: `TecnomegaDetailFetcher`
- **Process**: The orchestrator takes the `code` from the `ProductMaster` instance and uses the fetcher to construct the correct product detail page URL on the Tecnomega site. It then fetches the raw HTML content of that page.

### Parse

- **Component**: `TecnomegaDetailParser`
- **Process**: The raw HTML is passed to the parser, which is responsible for extracting structured data from the page. It isolates key information such as the product name, price, image URLs, and a dictionary of detailed attributes (like SKU, brand, weight, etc.).

### Persist

- **Process**: If `dry_run` is disabled, the orchestrator commits the parsed data to the database in a single atomic transaction:
    1.  **Update SKU**: The `sku` attribute (often the Manufacturer Part Number) is saved to the `ProductMaster.sku` field. This is a crucial piece of data for product identification.
    2.  **Create Detail Record**: A new record is created in the `ProductDetailScrape` table. This record stores the bulk of the scraped data (`name`, `price`, `attributes`, `image_urls`) and is linked back to the parent `ProductMaster` via a ForeignKey.
    3.  **Sync Images**: The list of scraped image URLs is used to create new `ProductImage` records, also linked to the `ProductMaster`. This populates the product's image gallery.

## 4. Data Mapping

The following table shows how the key scraped data points are mapped to the Django models.

| Scraped Attribute        | Destination Model       | Field                  | Type               | Notes                                                    |
| ------------------------ | ----------------------- | ---------------------- | ------------------ | -------------------------------------------------------- |
| `attributes['sku']`      | `ProductMaster`         | `sku`                  | `CharField`        | Updates the master record directly.                      |
| `name`                   | `ProductDetailScrape`   | `name`                 | `TextField`        | The full product name from the detail page.              |
| `price`                  | `ProductDetailScrape`   | `price`                | `DecimalField`     | The extracted price.                                     |
| `images` (list of URLs)  | `ProductDetailScrape`   | `image_urls`           | `JSONField`        | Stores a JSON array of all found image URLs.             |
| `images` (list of URLs)  | `ProductImage`          | `url`                  | `URLField`         | Creates one `ProductImage` record for each URL in the list. |
| `attributes` (dict)      | `ProductDetailScrape`   | `attributes`           | `JSONField`        | Stores the complete dictionary of scraped specifications. |

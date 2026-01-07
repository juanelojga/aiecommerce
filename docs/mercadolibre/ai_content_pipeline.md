### 3) Enrich Products

Enriches product master records by scraping for missing details (like SKU and images) and then generating structured specifications and SEO content using AI.

This command coordinates two main sub-processes:
- **Detail Scraping:** Uses `TecnomegaDetailOrchestrator` to find a product's SKU and additional images if they are missing.
- **AI Enrichment:** Uses `ProductSpecificationsOrchestrator` to generate technical specs and `AIContentOrchestrator` to create SEO-friendly titles and descriptions.

The process is designed to be efficient and resilient:
- **Lazy Execution:** It intelligently skips steps. If a product already has a SKU, scraping is skipped. If it already has specifications, AI enrichment is skipped. This can be overridden with the `--force` flag.
- **Isolation:** A failure during scraping or AI enrichment for a single product is logged but does not stop the entire batch process.

- **Command:**

```bash
python manage.py enrich_products [--force] [--delay <seconds>] [--dry-run]
```

- **Arguments:**
  - `--force`: If set, forces the reprocessing of all products, even those that already have SKUs or specifications.
  - `--delay`: A floating-point number specifying the delay in seconds between processing each product. Defaults to `0.5`.
  - `--dry-run`: Performs all lookups and AI calls but does not save any changes to the database.

- **Example usages:**

```bash
# Enrich all products that are missing a SKU or specs
python manage.py enrich_products

# Force reprocessing of all products with a 2-second delay between each
python manage.py enrich_products --force --delay 2

# Run in test mode without saving anything
python manage.py enrich_products --dry-run
```

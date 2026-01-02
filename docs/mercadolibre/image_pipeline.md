# Mercado Libre Image Pipeline Documentation

## 1. Trigger Mechanism: Identifying Products Missing Images

The `fetch_ml_images` process identifies products that need images by utilizing the `ImageCandidateSelector`.

The `ImageCandidateSelector`'s `get_pending_image_products` method performs two main steps:
1.  It uses `MercadoLibreFilter().get_eligible_products()` to retrieve `ProductMaster` entries that are marked as eligible for Mercado Libre (e.g., `is_for_mercadolibre=True` and other criteria defined in `MercadoLibreFilter`).
2.  From this set of eligible products, it further filters for those where `images__isnull=True`, effectively selecting products that do not yet have any associated `ProductImage` records.

This ensures that only relevant products missing images are considered for the image fetching process.

## 2. Asynchronous Workflow with Celery

The image fetching and processing workflow is handled asynchronously using Celery to ensure efficiency and avoid blocking the main application thread.

The `process_product_image` Celery task (found in `aiecommerce/tasks/images.py`) is triggered for each identified product. Its workflow is as follows:

1.  **Fetch Product:** Retrieves the `ProductMaster` record.
2.  **Search Images:** Uses `ImageSearchService` to find up to 5 image URLs based on the product's details.
3.  **Process and Upload:** It loops through the found image URLs:
    *   Downloads each image.
    *   **Image Processing:** `ImageProcessorService` processes the image (e.g., resize, center). Critically, `rembg` (background removal) is applied *only to the first image* (`i == 0`) to optimize costs and resources. Subsequent images are processed without background removal.
    *   Uploads the processed image to S3.
4.  **Create Records:** For each successfully uploaded image, a `ProductImage` record is created, associating it with the `ProductMaster`.
5.  **Error Handling:** If no images are successfully processed, the associated `MercadoLibreListing`'s status is updated to 'ERROR'.

## 3. Management Commands

The image pipeline can be triggered and managed using Django management commands.

### `python manage.py fetch_ml_images`

This command initiates the process of fetching and processing images for Mercado Libre products.

#### `--limit <number>`

**Usage:** `python manage.py fetch_ml_images --limit 10`

This optional flag allows you to limit the number of products for which images will be fetched. This is useful for testing or processing in batches.

#### `--dry-run`

**Usage:** `python manage.py fetch_ml_images --dry-run`

When this flag is used, the command will execute all identification and selection logic but will *not* perform any actual image fetching, processing, or database writes. It will report what *would* have happened, making it useful for verifying the selection criteria and preventing unintended changes.

## 4. Storage Model: `ProductImage` Records

Image URLs and their associated metadata are stored in the database using the `ProductImage` model (defined in `aiecommerce/models/product.py`).

Each `ProductImage` record has the following key fields:
*   **`product`**: A `ForeignKey` linking it to its parent `ProductMaster` record.
*   **`url`**: The URL where the processed image is stored (e.g., on S3).
*   **`order`**: A `PositiveIntegerField` (defaulting to 0) that defines the display order of the images for a given product. The `ProductImage` model's `Meta` class specifies `ordering = ["order"]`, ensuring that images are retrieved in the correct sequence. The first image (order 0) is typically the primary one and the one that undergoes background removal.
*   **`is_processed`**: A `BooleanField` indicating whether the image has gone through the processing pipeline.

## How to execute your tests

Before running any image-related tests, it's essential to ensure that the products are correctly flagged as eligible for Mercado Libre.

### Prerequisites: Flagging Eligible Products

The system identifies which products to process based on a set of business rules (e.g., stock availability, brand policies). To run this check and flag products accordingly, execute the following command:

```bash
python manage.py update_ml_eligibility
```
This command inspects the product catalog and sets `is_for_mercadolibre=True` on all products that meet the criteria, making them available for the image pipeline.

### Scenario 1: Deep Dry Run (Search Verification)

To test the image search query generation and URL candidacy without writing to the database or S3, use the `--dry-run` flag. This mode is perfect for verifying that your search logic is constructing the correct queries.

- **Command:**
  ```bash
  python manage.py fetch_ml_images --dry-run
  ```
- **Behavior:**
  - The system generates search queries for eligible products.
  - It prints the candidate URLs for the first 5 search results directly to the console.
  - No images are downloaded, processed, or uploaded. No database records are created.

### Scenario 2: Targeted Full Execution

If you need to test the entire pipeline for a single, specific product, you can use the `--id` flag. This is useful for debugging issues with a particular item.

- **Command:**
  ```bash
  python manage.py fetch_ml_images --id 123
  ```
- **Behavior:**
  - Performs the complete workflow for the product with `id=123`.
  - This includes image search, background removal (for the primary image), processing, and uploading to S3.
  - A `ProductImage` record will be created in the database upon success.

### Scenario 3: Controlled Batch Processing

To test the full automated pipeline on a small, manageable subset of products, combine flags like `--limit`. This allows you to validate the end-to-end workflow without processing your entire catalog.

- **Command:**
  ```bash
  python manage.py fetch_ml_images --limit 2
  ```
- **Behavior:**
  - The system will fetch and process images for a maximum of 2 eligible products.
  - This is ideal for a final sanity check before running a large-scale batch job.

### Script Verification

For developers looking to test the Google Search API and query construction logic in complete isolation from the Django management infrastructure, a dedicated script is available.

- **Script:**
  ```
  scripts/verify_image_search.py
  ```
- **Use Case:**
  - This script allows for direct, low-level testing of the search service.
  - It helps diagnose issues related to API credentials, query formatting, or upstream API changes without involving the Django ORM or Celery.

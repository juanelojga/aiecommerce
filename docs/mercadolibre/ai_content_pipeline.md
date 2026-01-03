# AI Content Generation Pipeline (ML-08 & ML-10)

This document outlines the architecture and usage of the AI Content Generation system, a core component of the Mercado Libre integration. It covers the content generation (ML-08) and the testing CLI (ML-10).

## 1. Architectural Overview

The system is designed around a **"Source of Truth"** strategy. AI-generated content is not stored transiently; instead, it is persisted centrally within the `ProductMaster` model, specifically in the `seo_title` and `seo_description` fields.

This approach ensures that high-quality, SEO-optimized content is generated once and can be reused across multiple sales channels, maintaining consistency and reducing redundant API calls.

## 2. The Services

The content generation process is handled by two specialized, single-responsibility services.

### TitleGeneratorService

This service is responsible for creating concise, effective, and compliant titles for listings.

- **Role:** Generate a 60-character title.
- **Structure:** Follows the recommended format: `[Product + Brand + Model + Key Specs]`.
- **Constraints:** Automatically excludes forbidden terms such as "stock," "warranty," "oferta," etc., to comply with platform rules.

### DescriptionGeneratorService

This service crafts detailed, well-structured product descriptions.

- **Role:** Produce a comprehensive, plain-text description.
- **Structure:** The output is organized into clear paragraphs:
    1.  **Introduction:** A brief, engaging overview of the product.
    2.  **Specifications:** A list or paragraph detailing key technical specs.
    3.  **Usage/Compatibility:** Information on how to use the product or its compatibility with other devices.
    4.  **Warranty & Seller Information:** Standardized text regarding warranty and seller policies.

## 3. AIContentOrchestrator (The Brain)

The `AIContentOrchestrator` coordinates the services and manages the overall workflow, acting as the primary entry point for all content generation tasks.

### `process_product_content` method

This is the core method for processing a single product.
- It first checks if SEO content already exists for the given `ProductMaster` instance.
- To avoid redundant API calls and costs, it will skip generation unless the `force_refresh=True` flag is passed.

### `process_batch` method

Designed for background tasks and bulk operations, this method efficiently processes multiple products.
- The `limit` parameter is crucial for safety, allowing you to control the number of products processed in a single run. This helps manage API costs and avoids hitting rate limits.

### `dry_run` Logic

A key safety feature of the orchestrator is its `dry_run` mode.
- By default, the orchestrator runs in `dry_run=True` mode. In this state, it will generate content and display it without persisting anything to the database.
- Data is only saved when the process is explicitly invoked with `dry_run=False`.

## 4. Testing Command (`test_ai_content`)

A dedicated management command provides a powerful tool for diagnostics, testing, and manual content generation.

### Command Syntax

```bash
python manage.py test_ai_content <product_code>
```
- `<product_code>`: The unique identifier of the `ProductMaster` to process.

### Flags

- `--dry-run`: (Default: `True`) Runs the entire pipeline and prints the generated title and description to the console without saving to the database. This is the safe mode for previewing AI output.
- `--no-dry-run`: Persists the generated content to the `seo_title` and `seo_description` fields of the specified product.
- `--force`: Overwrites existing SEO content. Must be used if the product already has generated content.

### Output

The command provides clear console output, showing:
- A comparison of the original (if any) vs. the newly generated content.
- Character count validation for the title to ensure it meets the 60-character limit.

**Example Usage:**

```bash
# Preview content for product 'PROD-123' without saving
python manage.py test_ai_content PROD-123

# Generate and save content for 'PROD-123', overwriting if it exists
python manage.py test_ai_content PROD-123 --no-dry-run --force
```

## 5. Error Handling & Logging

The system is designed for robustness. If an external AI service fails or returns an error, the pipeline has fallbacks:
- It will log the error for debugging.
- It will gracefully fall back to using the product's original, non-AI-enhanced name and description. This ensures that the overall listing process is not blocked by a single point of failure.

## 6. Best Practices

- **Batch Processing:** When running batch updates (e.g., via a periodic task), always use a small `limit` (e.g., 10-20 products) to control costs and stay within API rate limits.
- **Dry Runs:** Always perform a `--dry-run` to preview changes before applying them with `--no-dry-run`, especially when dealing with a large number of products.

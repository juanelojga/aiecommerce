# On-Demand Product Image Refresh

## Overview

Product images occasionally come from incorrect or outdated sources (e.g. a
supplier swaps a photo, or the original scrape picked up the wrong variant).
The image-refresh action discards the current image set for a single product
and re-runs the high-resolution image pipeline from scratch.

Flow:

1. Delete every `ProductImage` row belonging to the product.
2. Delete every S3 object under the prefix `products/<product_code>/` in
   `AWS_STORAGE_BUCKET_NAME`.
3. Enqueue `process_highres_image_task(product_code)` so a Celery worker
   re-downloads, re-transforms, and re-uploads the images, and recreates the
   `ProductImage` rows.

The delete step runs inline (fast). The re-fetch is asynchronous — callers
get the Celery task id back immediately and can monitor progress via the
worker logs.

Two entry points are supported: a management command (for ops/CLI) and a
REST endpoint (for applications and ad-hoc triggers).

## Management command

```bash
python manage.py refresh_product_images <product_code>
```

Example:

```bash
$ python manage.py refresh_product_images TM-12345
Queued image refresh for TM-12345. Task id: 6f1b8c2a-...
```

Errors:

- Unknown product code → `CommandError: Product with code 'TM-12345' not found.`

## REST endpoint

```
POST /api/v1/products/{id}/refresh-images/
```

- `{id}` is the `ProductMaster` primary key (the same id used by the other
  `/products/` endpoints).
- Authentication and IP-whitelisting follow the project default
  (`ApiKeyAuthentication` + `SessionAuthentication`, `IPWhitelistPermission` +
  `IsAuthenticated`). See [`api-authentication.md`](../api-authentication.md).

### curl example

```bash
curl -X POST \
  -H "X-API-Key: $AIECOMMERCE_API_KEY" \
  https://api.example.com/api/v1/products/42/refresh-images/
```

### Success response — `202 Accepted`

```json
{
  "task_id": "6f1b8c2a-7a8c-4a4e-9a1d-0b2d3e4f5c6a",
  "product_code": "TM-12345"
}
```

### Error responses

| Status | Cause |
| ------ | ----- |
| `401` / `403` | Missing/invalid API key or IP not whitelisted. |
| `404` | No `ProductMaster` with the given id. |

## What it does and does not do

**Does:**

- Deletes all `ProductImage` rows for the product.
- Deletes all S3 objects under `products/<product_code>/` in the configured
  bucket (uses `list_objects_v2` + batched `delete_objects`).
- Enqueues the existing `process_highres_image_task` to rebuild the image
  set from the latest `ProductDetailScrape`.

**Does not:**

- Touch `ProductMaster` or any other related data (specs, prices, listings).
- Re-run scraping. It reuses the most recent `ProductDetailScrape`; if that
  scrape itself is stale, run the scrape command first.
- Block the HTTP request on image processing — the response returns as soon
  as the task is enqueued.

## Operational notes

- A Celery worker **must** be running for the re-fetch to happen. See
  [`infrastructure/celery_guide.md`](../infrastructure/celery_guide.md).
- Underlying pipeline internals are documented in
  [`image_pipeline.md`](image_pipeline.md).
- Monitor progress via worker logs — look for
  `Starting high-resolution image processing for product: <code>` and the
  matching `Finished ...` line.
- If `AWS_STORAGE_BUCKET_NAME` is unset (local/dev), the S3 cleanup step is
  skipped with a warning and the DB delete + enqueue still run.

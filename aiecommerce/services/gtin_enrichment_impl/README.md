# GTIN Enrichment Service

A Django service that uses LLM with online search capabilities to find GTIN (EAN/UPC) codes for products.

## Overview

The `GTINSearchService` implements a multi-strategy approach to search for GTIN codes:

1. **Strategy 1: SKU + Normalized Name** - Searches using the product's SKU and normalized name
2. **Strategy 2: Model + Brand** - Searches using the model name and brand from specs
3. **Strategy 3: Raw Description** - Searches using detailed scrape data from ProductDetailScrape

Each strategy is executed sequentially until a valid GTIN (8-14 digits) is found.

## Requirements

- Django 5.x
- Python 3.12+
- OpenRouter API key (for LLM access)
- Instructor library (for structured LLM output)

## Configuration

Add the following to your Django settings:

```python
# Required settings
OPENROUTER_API_KEY = "your-api-key"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GTIN_SEARCH_MODEL = "google/gemini-flash-1.5-8b"  # or any other model
```

## Usage

### Basic Usage

```python
from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_enrichment_impl import GTINSearchService

# Initialize the service
service = GTINSearchService()

# Get a product without GTIN
product = ProductMaster.objects.get(code="PROD123")

# Search for GTIN
gtin, strategy = service.search_gtin(product)

if gtin:
    print(f"Found GTIN: {gtin} (using {strategy})")
    # Update the product
    product.gtin = gtin
    product.gtin_source = strategy
    product.save()
else:
    print(f"No GTIN found (strategy: {strategy})")
```

### Batch Processing

```python
from aiecommerce.services.gtin_enrichment_impl import GTINSearchService

service = GTINSearchService()

# Get all products without GTIN
products = ProductMaster.objects.filter(gtin__isnull=True)

results = {"found": 0, "not_found": 0}

for product in products:
    gtin, strategy = service.search_gtin(product)
    
    if gtin:
        product.gtin = gtin
        product.gtin_source = strategy
        product.save()
        results["found"] += 1
    else:
        results["not_found"] += 1

print(f"Results: {results}")
```

## Strategies

### Strategy 1: sku_normalized_name

**Trigger Condition:** Product has both `sku` and `normalized_name`

**Example Query:**
```
SKU: MPN12345, Product: Dell Latitude 5430 Intel Core i5 16GB
```

### Strategy 2: model_brand

**Trigger Condition:** Product has `model_name` and specs contain Brand/brand/Marca

**Example Query:**
```
Brand: Dell, Model: Latitude 5430
```

### Strategy 3: raw_description

**Trigger Condition:** Product has associated ProductDetailScrape records

**Example Query:**
```
Dell Latitude 5430 Notebook | Marca: Dell | Modelo: Latitude 5430 | RAM: 16GB | Storage: 512GB SSD
```

## Response

The `search_gtin()` method returns a tuple:

```python
(gtin_code: str | None, strategy_name: str)
```

**Strategy Names:**
- `"sku_normalized_name"` - Strategy 1 succeeded
- `"model_brand"` - Strategy 2 succeeded
- `"raw_description"` - Strategy 3 succeeded
- `"NOT_FOUND"` - All strategies failed

## GTIN Validation

The service validates that returned GTINs:
- Are numeric only (no letters or special characters)
- Are between 8 and 14 digits long
- Match the pattern: `^\d{8,14}$`

Invalid GTINs are rejected and the search continues to the next strategy.

## Error Handling

The service handles the following errors gracefully:

- **APIError** - OpenRouter API errors
- **TimeoutError** - Network timeouts
- **ValidationError** - Invalid LLM response format
- **ConfigurationError** - Missing required settings

All errors are logged and the search continues to the next strategy.

## Logging

The service uses Python's logging module with the logger name:

```python
aiecommerce.services.gtin_enrichment_impl.service
```

**Log Levels:**
- `INFO` - Strategy successes and progress
- `DEBUG` - Strategy skips and detailed search info
- `WARNING` - No GTIN found after all strategies
- `ERROR` - API/network/validation errors
- `CRITICAL` - Unexpected errors

## Testing

Run the comprehensive test suite:

```bash
python -m pytest aiecommerce/tests/services/gtin_enrichment_impl/test_service.py -v
```

**Test Coverage:**
- Initialization with valid/invalid settings
- GTIN validation (8-14 digits)
- All three search strategies
- Error handling and fallback
- Integration workflows
- LLM prompt structure

## Architecture

```
gtin_enrichment_impl/
├── __init__.py           # Package exports
├── service.py            # GTINSearchService class
├── schemas.py            # Pydantic models
├── exceptions.py         # Custom exceptions
├── example_usage.py      # Usage examples
└── README.md            # This file
```

## Dependencies

The service depends on:

1. **Django Models:**
   - `ProductMaster` - Main product model
   - `ProductDetailScrape` - Detailed scrape data

2. **External Libraries:**
   - `instructor` - Structured LLM outputs
   - `openai` - OpenAI client (used with OpenRouter)
   - `pydantic` - Data validation

3. **Django Settings:**
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_BASE_URL`
   - `GTIN_SEARCH_MODEL`

## Performance Considerations

- Each strategy makes an LLM API call (with online search)
- Expect 2-5 seconds per strategy execution
- Use batch processing with delays to avoid rate limits
- Consider caching successful results

## Future Enhancements

Potential improvements:

1. Add caching layer to avoid redundant searches
2. Implement parallel strategy execution (with fallback)
3. Add more specialized strategies for specific product types
4. Integrate with additional GTIN databases (UPC Database, GS1)
5. Add confidence scoring for GTIN accuracy

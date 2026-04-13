# MercadoLibre Listings — Sync Error Analysis Report

**Total listings with ERROR status: 90**
**Data source: `SyncError` field on each listing**

---

## Error Category Breakdown

### 🔴 CATEGORY 1 — Invalid GTIN Format

**`item.attribute.product_identifier.invalid_format`**
**Count: ~45 listings**

The GTIN value submitted does not pass MercadoLibre's checksum/format validation. These are manufacturer part numbers or internal codes that were incorrectly mapped to the GTIN attribute.

**Affected listings (sample):**

| ID | Product |
|----|---------|
| 1002 | MONSAMLS27D300G — Samsung Monitor S3 27" |
| 989 | MONSAT1073FPH — SAT Monitor 17" Touch |
| 916 | CELSAMSMX075CBK — Samsung Galaxy A07 |
| 917 | MONASUPA278QV — Asus PA278QV Monitor |
| 894 | COMLEN82YY04QLM — Lenovo V15 G4 |
| 677 | PROINTCI512400F — Intel Core i5-12400F |
| 676 | PROINTCOI312100 — Intel Core i3-12100 |
| 661 | MBOASUH810M-E — Asus H810M-E |
| 415 | (HDD Adata series) |
| 418–434 | (Multiple HDD/SSD/Monitor entries) |
| 940 | COMAPLMHFF4LLAI — MacBook Neo A18 Indigo |
| 407, 412, 420, 423, 424, 426, 427, 431, 432, 433, 434 | Various monitors, NAS drives, RAM |

**Root cause in the agent/prompt:**
The agent is taking whatever number appears in a GTIN/EAN/barcode field from the product data source and directly inserting it into the `GTIN` attribute without validating the checksum. Many of these are 12-digit codes (not EAN-13), internal distributor codes (e.g. `4530000000000`, `8128500000000`), or simply wrong-length numbers that fail MercadoLibre's GTIN-13 check digit validation.

**Example invalid GTINs submitted:**

- `8806095484838` (Samsung monitor — checksum fails)
- `4070047000103` (SAT monitor)
- `7861000318042` (Samsung A07)
- `4718017565985` (Asus monitor)
- `8128500000000` / `8128501900300` (placeholder-looking codes)
- `453759310231` (12 digits, not 13)
- `453000004001` (12 digits)
- `0195941113063` (Apple MacBook)

---

### 🔴 CATEGORY 2 — Duplicate / Invalid Product Identifier (GTIN used in another category)

**`item.attribute.invalid_product_identifier`**
**Count: ~8 listings**

MercadoLibre detected the GTIN is already registered in a different category on the platform.

**Affected listings:**

| ID | Product |
|----|---------|
| 774 | CASCORCC9011325 — Corsair 3500X White |
| 773 | CASCORCC9011324 — Corsair 3500X Black |
| 421 | (Adata HDD series) |
| 416 | (LG Monitor series) |
| 419 | (WD HDD series) |
| 428 | (LG Monitor series) |

**Root cause:**
The same GTIN code is being reused across listings or was originally registered in a different MercadoLibre category (e.g., a barcode used for a product in "Monitors" also exists in "Cases"). MercadoLibre enforces unique GTIN-per-category. The agent is not checking for cross-category GTIN conflicts.

---

### 🔴 CATEGORY 3 — Missing Price

**`item.price.invalid` / `item.price.invalid` (no price set)**
**Count: ~14 listings**

The `final_price` field is empty (null/blank). MercadoLibre requires a minimum price > 0 for listing creation.

**Affected listings:**

| ID | Product | Category |
|----|---------|---------|
| 966 | PROAMD100001973 — Ryzen 7 9850X3D | MEC1693 |
| 967 | PROAMD100001368 — Ryzen 9 9900X3D | MEC1693 |
| 652 | PROAMD100001585 — Ryzen 5 5600XT | MEC1693 |
| 711 | COMDELCTV12 — Dell Pro 16 Core7 | MEC95057 |
| 712 | COMDEL37TWC — Dell Pro 16 Ultra5 | MEC95057 |
| 717 | COPHPXB88BKAT — HP AIO ProOne 240 G10 | MEC1649 |
| 844 | PROAMD100001591 — Ryzen 5 8400F | MEC1693 |
| 848 | CASCORCC9011297 — Corsair 4000D White | — |
| 850 | CASCORCC9011296 — Corsair 4000D Black | — |
| 867, 869 | (Corsair/Gigabyte cases) | — |
| 877, 880 | (WD NAS drives) | — |

**Root cause:**
The sync agent is attempting to publish listings where the pricing pipeline has not yet calculated or provided a `final_price`. The agent submits the listing to MercadoLibre before prices are populated. There is also a secondary symptom in some of these (e.g. ID 652, 880): the agent is sending a fake attribute `"PRICE"` inside the `attributes` JSON array instead of using the correct `final_price` field — `"Attribute: PRICE was dropped because does not exists"`.

---

### 🔴 CATEGORY 4 — Missing Required Attributes

**`item.attributes.missing_required`**
**Count: ~12 listings**

MercadoLibre rejected the listing because one or more attributes that are **required for the target category** were absent from the submitted payload.

**Affected listings and missing attributes:**

| ID | Product | Category | Missing Attributes |
|----|---------|----------|--------------------|
| 648 | MBOASUB860PLSWF — Asus TUF B860+ | MEC95057 | `DISPLAY_SIZE`, `PROCESSOR_BRAND`, `PROCESSOR_LINE`, `PROCESSOR_MODEL` |
| 624 | PROINTCI713700F — Intel Core i7-13700F | MEC1693 | `LINE`, `COMPATIBLE_SOCKETS` |
| 631 | MONGIBMO27Q28G — Gigabyte Mo27Q28G | MEC1656 | `IS_CURVED`, `RESOLUTION_TYPE` |
| 642 | MONSAM27FG600EN — Samsung Odyssey G6 | MEC1656 | `IS_CURVED`, `RESOLUTION_TYPE` |
| 379 | CELSAMSMX075CBK (variant) | MEC1055 | `COLOR`, `IS_DUAL_SIM`, `CARRIER` |
| 390 | (Phone listing) | MEC1055 | `COLOR`, `IS_DUAL_SIM`, `CARRIER` |
| 707, 708 | (Notebook listings — Dell/Asus) | MEC1649 | `PROCESSOR_LINE`, `PROCESSOR_MODEL`, `DISPLAY_SIZE` |
| 660 | (Notebook) | — | `PROCESSOR_LINE` |
| 727 | MBOASUB1I30M0UB — Asus Q670M | MEC95057 | `DISPLAY_SIZE`, `PROCESSOR_BRAND`, `PROCESSOR_LINE` |

**Root cause:**
The agent generates attributes based on product description data but does not validate the full list of **required attributes for the specific MercadoLibre category** before submitting. It only includes attributes it can "infer" from the product title/specs and misses mandatory fields like:

- `LINE` (processor line/generation series, e.g. "Raptor Lake")
- `IS_CURVED` (monitor curved yes/no)
- `RESOLUTION_TYPE` (e.g. "QHD", "Full HD")
- `IS_DUAL_SIM` and `CARRIER` (for phones)
- `PROCESSOR_BRAND`, `PROCESSOR_LINE`, `PROCESSOR_MODEL` (for motherboards/AIO PCs)

---

### 🔴 CATEGORY 5 — Null / Missing Category ID

**`body.invalid_field_types` — category_id is null**
**Count: ~3 listings**

The `category_id` field was never set (null), so MercadoLibre rejects the entire request before any attribute validation.

**Affected listings:**

| ID | Product |
|----|---------|
| 380 | MONLGX55VL5F-A — LG 55" Videowall |
| 388 | (Adata external drive series) |
| 389 | (Corsair/related) |

**Root cause:**
The agent failed to determine or assign a MercadoLibre category for these products. This likely happens when the category prediction/mapping step fails silently and the agent proceeds to create the listing with a null `category_id`.

---

### 🔴 CATEGORY 6 — Invalid Attribute Value (MODEL not resolvable)

**`item.attribute.invalid` — MODEL value could not be resolved**
**Count: ~5 listings**

MercadoLibre could not resolve the `MODEL` attribute value against its internal attributes database (no matching `value_id` found and the value name was insufficient or empty).

**Affected listings:**

| ID | Product |
|----|---------|
| 955 | CELSAMSMA366ELG — Samsung Galaxy A36 |
| 939 | COMAPLMHFD4LLAC — MacBook Neo A18 Citrus |
| 941 | COMAPLMHFA4LLAS — MacBook Neo A18 Silver |
| 706 | COMASUR0L67M04S — Asus ROG G614pp |

**Root cause:**
The agent provides a `value_name` for `MODEL` but does not supply a valid `value_id`, and the string it provides does not match any known model in MercadoLibre's catalog. This is particularly problematic for **new/unreleased products** (e.g. Apple MacBook Neo A18, which doesn't exist in ML's database yet) or for **MODEL strings that are too generic or abbreviated**. For listing 939, the `MODEL` attribute was dropped entirely (`value_id` and `value_name` both null).

---

### 🟡 CATEGORY 7 — Build-Title Attributes Required

**`Error getting resource /decorations/build-title` — attributes are required**
**Count: ~2 listings**

MercadoLibre's title-building service failed because essential attributes are missing. The listing gets rejected at the title generation step before attribute validation even runs.

**Affected listings:**

| ID | Product |
|----|---------|
| 840 | PROAMD100000662 — AMD Ryzen 9 9900X |

**Root cause:**
Similar to Category 4, but caught earlier in the pipeline. The category (MEC1693 — Processors) requires enough attributes to build a title, and the submitted payload is missing key fields needed by MercadoLibre's title template.

---

### 🟡 CATEGORY 8 — Missing GTIN (Required by Category)

**`item.attribute.missing_conditional_required` — GTIN is required**
**Count: ~2 listings**

The opposite of Categories 1 & 2: these categories **require** a GTIN, but none was provided.

**Affected listings:**

| ID | Product | Category |
|----|---------|---------|
| 999 | COPHPXBM6X6LA — HP OmniStudio X AIO | MEC126843 |

**Root cause:**
The agent omitted the GTIN attribute for this product. For certain high-tier AIO/desktop categories, MercadoLibre mandates a GTIN. The agent must provide a valid one or resolve the issue with the product data source.

---

## Summary Table

| # | Error Code | Description | Count | Fix Direction |
|---|-----------|-------------|-------|--------------|
| 1 | `item.attribute.product_identifier.invalid_format` | GTIN fails checksum validation | ~45 | Remove invalid GTIN from attributes |
| 2 | `item.attribute.invalid_product_identifier` | GTIN duplicated across categories | ~8 | Remove GTIN or use category-specific one |
| 3 | `item.price.invalid` | No price set at time of sync | ~14 | Ensure price exists before syncing; don't send `PRICE` as an attribute |
| 4 | `item.attributes.missing_required` | Required category attributes absent | ~12 | Expand attribute extraction per category requirements |
| 5 | `body.invalid_field_types` (null category_id) | No category assigned | ~3 | Validate category mapping before submission |
| 6 | `item.attribute.invalid` (MODEL) | MODEL value not resolvable in ML database | ~5 | Use known ML `value_id`s or omit MODEL for new products |
| 7 | `build-title bad_request` | Attributes missing for title generation | ~2 | Same as #4 |
| 8 | `item.attribute.missing_conditional_required` | GTIN required but not provided | ~2 | Provide valid GTIN when category mandates it |

---

## Key Prompt / Agent Improvements Recommended

**1. GTIN Validation Before Submission**
The agent must validate any GTIN before including it. Specifically: verify it is exactly 13 digits (EAN-13) and passes the standard check digit algorithm. If it fails, **omit the GTIN attribute entirely** rather than submitting an invalid one. Internal codes, part numbers, and distributor codes must not be submitted as GTINs.

**2. No PRICE in Attributes Array**
The agent must never include `PRICE` as an element inside the `attributes` JSON array. Price must only be set via the `final_price` field. The agent appears to be confusing product spec attributes with the price field.

**3. Pre-submission Price Guard**
The agent should verify `final_price > 0` before attempting to create or sync a listing. If the price is not yet available, the listing should remain in PENDING/DRAFT state instead of attempting submission and recording an error.

**4. Category-Aware Required Attribute Checklist**
For each target category, the agent should maintain or query a checklist of required attributes and validate the payload before submission. Key gaps identified:

- **MEC1693 (Processors):** must include `LINE`, `COMPATIBLE_SOCKETS`
- **MEC1656 (Monitors):** must include `IS_CURVED`, `RESOLUTION_TYPE`
- **MEC95057 (Motherboards/AIO PCs):** must include `DISPLAY_SIZE`, `PROCESSOR_BRAND`, `PROCESSOR_LINE`, `PROCESSOR_MODEL`
- **MEC1649 (Laptops/AIO):** must include `PROCESSOR_LINE`, `PROCESSOR_MODEL`, `DISPLAY_SIZE`
- **MEC1055 (Phones):** must include `COLOR`, `IS_DUAL_SIM`, `CARRIER`

**5. Category ID Validation**
The agent must never submit a listing with a null/empty `category_id`. If category mapping fails, the sync process should abort with a clear internal error rather than submitting a malformed request.

**6. MODEL Attribute — Known Products Only**
For the `MODEL` attribute, the agent should only submit it when a valid `value_id` can be resolved from MercadoLibre's attribute database. For brand-new or unreleased products not yet in ML's catalog, omit the `MODEL` attribute rather than submitting an unresolvable string.

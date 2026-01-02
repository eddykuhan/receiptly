# Retail ETL Pipeline - Scraping & Canonicalization Guide

**Last Updated**: January 1, 2026

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Scraping (Extract Phase)](#scraping-extract-phase)
4. [Canonicalization (Transform Phase)](#canonicalization-transform-phase)
5. [Loading (Load Phase)](#loading-load-phase)
6. [Orchestration](#orchestration)
7. [Database Schema](#database-schema)
8. [Configuration](#configuration)
9. [Key Design Patterns](#key-design-patterns)
10. [Performance Optimizations](#performance-optimizations)

---

## System Overview

The Retail ETL Pipeline is a sophisticated **Extract-Transform-Load (ETL)** system that:
- **Scrapes** product price data from Malaysian retail chains
- **Canonicalizes** product names using AI-powered matching
- **Loads** standardized data into PostgreSQL for analytics

**Key Value Proposition**: Converts disparate product names like "Coca Cola 1.5L", "Coke 1.5 Liter", "COCA-COLA 1.5L BOTTLE" into a single canonical item for accurate price comparison across stores.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     ETL PIPELINE FLOW                         │
└──────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  SCRAPERS   │ -> │ CANONICALIZER│ -> │   LOADER    │
│  (Extract)  │    │  (Transform)  │    │   (Load)    │
└─────────────┘    └──────────────┘    └─────────────┘
       ↓                   ↓                    ↓
  Raw Products      Canonical IDs      PostgreSQL
  - MYDIN API       + Embeddings       Gold Table
  - Jaya API        + Match Method     (Historical)
  - AEON Selenium
```

### Component Locations
- **Scrapers**: `scrapers/` (base_scraper.py, mydin.py, jaya_grocer.py, aeon.py, lotus.py)
- **Canonicalizer**: `etl_transformers/canonicalizer.py`
- **Loader**: `loaders/postgres_loader.py`
- **Orchestrator**: `etl_manager.py`
- **Scheduler**: `scheduler.py`
- **Config**: `config/settings.py`

---

## Scraping (Extract Phase)

### Base Scraper Architecture

**File**: `scrapers/base_scraper.py`

All scrapers inherit from the `BaseScraper` abstract class, ensuring uniform output and behavior.

#### Key Concepts

**1. Pricing Zone Model**
- Scraped data represents **regional pricing zones**, not individual stores
- Examples: `MYDIN_NATIONAL`, `JG_PENANG`
- Physical store locations are stored separately in the `stores` table
- Scraped records have `latitude=None` and `longitude=None`

**2. Abstract Interface**
```python
class BaseScraper(ABC):
    def __init__(self, pricing_zone_id, store_name, store_address, latitude=None, longitude=None)
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """Must return list of product dictionaries"""
        pass
    
    def clean(self, records: List[Dict]) -> List[Dict]:
        """Validates and adds metadata"""
        pass
    
    def run(self) -> List[Dict]:
        """Executes scrape() then clean()"""
        pass
```

**3. Required Output Schema**
Every scraper must return this standardized format:
```python
{
    'item_name': str,           # Raw product name from source
    'unit_price': float,        # Price in MYR
    'category': str,            # Product category
    'brand': str,               # Brand name (optional, default '')
    'sku': str,                 # SKU/product code (optional, default '')
    'available': bool,          # Stock availability (default True)
    'scraped_at': str,          # ISO timestamp
    'source': str               # Scraper identifier (e.g., 'mydin_graphql')
}
```

**4. Automatic Metadata Injection**
The `clean()` method adds:
- `store_name`: Set to `pricing_zone_id` for consistency
- `pricing_zone_id`: Zone identifier
- `store_address`: Regional address
- `latitude`: None (zone-based, not location-based)
- `longitude`: None (zone-based, not location-based)

### Scraper Implementations

#### 1. MYDIN Scraper
**File**: `scrapers/mydin.py`

**Method**: GraphQL API
```python
class MydinScraper(BaseScraper):
    TARGET_CATEGORIES = [1222, 1513, 2665, 2667, 2668, 2669]
```

**Strategy**:
- Multi-category iteration (Food & Beverages, Groceries, Home & Living, etc.)
- Pagination: 48 items per page, configurable max pages (default 100)
- Polite scraping: 1 second delay between requests

**GraphQL Query Structure**:
```python
query_body = [
    {"filter": {"category_id": {"eq": str(category_id)}}, 
     "pageSize": 48, 
     "currentPage": page},
    {"products": "products-custom-query", 
     "metadata": {"fields": "items { id, sku, name, price_range ... }"}}
]
```

**Data Transformation**:
- Name: `custom_productname` OR `name`
- Price: Extracted from `price_range.minimum_price.final_price.value`
- Availability: Based on `salable_quantity > 0`
- Category: First category name from `categories[0].name`

**Example Output**:
```python
{
    'item_name': 'Wonda Coffee Kopi Tarik 240ml',
    'unit_price': 2.50,
    'category': 'Food & Beverages',
    'sku': 'WON12345',
    'product_url': 'https://mydin.my/wonda-coffee-kopi-tarik.html',
    'image_url': 'https://...',
    'available': True,
    'source': 'mydin_graphql'
}
```

#### 2. Jaya Grocer Scraper
**File**: `scrapers/jaya_grocer.py`

**Method**: Shopify API adapter (wraps existing `store-scraper` implementation)

**Strategy**:
- Reuses battle-tested `JayaGrocerScraper` from `store-scraper/`
- Adapts output to conform to `BaseScraper` schema
- Zone: Penang region (`JG_PENANG`)

**Key Code**:
```python
def scrape(self) -> List[Dict]:
    # Use original scraper
    products = self.original_scraper.scrape_all_products(delay=1.5)
    
    # Transform to BaseScraper schema
    for product in products:
        record = {
            'item_name': product['item_name'],
            'unit_price': product['unit_price'],
            'category': product.get('category', 'Unknown'),
            'source': 'jaya_grocer_shopify_api'
        }
```

#### 3. AEON Scraper
**File**: `scrapers/aeon.py`

**Method**: Selenium WebDriver

**Strategy**:
- Headless Chrome automation
- Heuristic DOM parsing (generic product card detection)
- Fallback strategies for element selection

**Challenges**:
- No public API available
- DOM structure varies across page updates
- Requires CSS selector maintenance

**Extraction Logic**:
```python
# Primary: CSS selector
product_cards = driver.find_elements(By.CSS_SELECTOR, '.product-item, .item-card')

# Fallback: XPath heuristic
product_cards = driver.find_elements(By.XPATH, '//div[contains(., "RM")]/ancestor::div[...]')

# Parse card text
for line in card.text.split('\n'):
    if 'RM' in line:
        price = extract_price(line)
    else:
        name = line
```

#### 4. Lotus's Scraper
**File**: `scrapers/lotus.py`

**Method**: Similar to AEON (Selenium-based)
**Status**: Currently commented out in config
**Note**: See `LOTUSS_SCRAPING_ANALYSIS.md` for implementation details

---

## Canonicalization (Transform Phase)

### Overview

**File**: `etl_transformers/canonicalizer.py`

The **most sophisticated component** of the ETL pipeline. Converts varying product names into standardized canonical items using a **multi-strategy waterfall approach**.

### Why Canonicalization is Critical

**Problem**: Different stores use different naming conventions
```
Store A: "Coca Cola 1.5L Bottle"
Store B: "Coke 1.5 Liter"
Store C: "COCA-COLA 1.5L PET"
User Receipt: "coke 1.5l"
```

**Solution**: All map to single canonical item with UUID
```
CanonicalItemId: 550e8400-e29b-41d4-a716-446655440000
Name: "coca cola 1 5l bottle"
```

### 6-Step Processing Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  INPUT: "Coca Cola 1.5L Bottle"                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 0: Memory Cache Lookup                            │
│  Check: self._cache dictionary                          │
│  Purpose: Avoid redundant processing in same run        │
│  Result: HIT → return cached result / MISS → continue   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 1: Text Normalization                             │
│  Input:  "Coca Cola 1.5L Bottle"                        │
│  Output: "coca cola 1 5l bottle"                        │
│  Actions:                                               │
│    - Convert to lowercase                               │
│    - Remove special characters → spaces                 │
│    - Remove " 1 unit" suffix                            │
│    - Collapse whitespace                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 2: Exact Match (Database)                         │
│  Query: SELECT "Id" FROM canonical_items                │
│         WHERE LOWER("Name") = 'coca cola 1 5l bottle'   │
│  Result: Found → return canonical_item_id               │
│          Not Found → continue                           │
│  Match Method: 'exact_or_alias'                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 3: Alias Match (Database)                         │
│  Query: SELECT "CanonicalItemId"                        │
│         FROM canonical_item_aliases                     │
│         WHERE LOWER("Alias") = 'coca cola 1 5l bottle'  │
│  Purpose: Handle known variants                         │
│  Result: Found → return canonical_item_id               │
│          Not Found → continue                           │
│  Match Method: 'exact_or_alias'                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 4: Vector Similarity (AI-Powered)                 │
│  Action:                                                │
│    1. Generate embedding using SentenceTransformer      │
│       Model: 'all-MiniLM-L6-v2'                         │
│       Output: 384-dimensional vector                    │
│                                                         │
│    2. Search using pgvector cosine similarity           │
│       Query: SELECT "CanonicalItemId",                  │
│              1 - ("Embedding" <=> %s::vector) AS sim    │
│              FROM canonical_item_embeddings             │
│              ORDER BY "Embedding" <=> %s::vector        │
│              LIMIT 1                                    │
│                                                         │
│    3. Threshold check: similarity >= 0.90               │
│  Result: Match → return (canonical_item_id, score)      │
│          No match → continue                            │
│  Match Method: 'embedding'                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 5: Create New Canonical Item                      │
│  Action:                                                │
│    1. Generate new UUID                                 │
│    2. INSERT INTO canonical_items                       │
│       VALUES (uuid, normalized_name, category, NOW())   │
│    3. Store embedding in canonical_item_embeddings      │
│       INSERT INTO canonical_item_embeddings             │
│       VALUES (uuid, embedding::vector, NOW())           │
│  Result: Return new canonical_item_id                   │
│  Match Method: 'new'                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  OUTPUT:                                                │
│  {                                                      │
│    'canonical_item_id': '550e8400-...',                 │
│    'match_method': 'exact_or_alias' | 'embedding' |     │
│                     'new',                              │
│    'similarity_score': 0.95  (if embedding match)       │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

### Key Methods

#### Individual Canonicalization
```python
def canonicalize(self, item_name: str, category: str = "Unknown") -> Dict:
    """
    Process a single item through the 6-step pipeline.
    Returns: {canonical_item_id, match_method, similarity_score?}
    """
```

#### Batch Canonicalization (Optimized)
```python
def canonicalize_batch(self, items: List[Dict]) -> List[Dict]:
    """
    Process multiple items efficiently with:
    1. Deduplication: Group identical normalized names
    2. Bulk DB queries: Single query for all exact/alias matches
    3. Batch AI encoding: model.encode([list]) is 10x faster
    4. Result distribution: Apply results to all duplicates
    """
```

### Batch Processing Optimizations

**Problem**: Processing 1000 items individually = 1000 DB queries + 1000 AI calls

**Solution**: Intelligent batching

```python
# BEFORE (Slow - Individual Processing)
for item in items:  # 1000 items
    canonical_id = check_exact_match(item)     # 1000 DB queries
    if not canonical_id:
        embedding = model.encode(item)          # 1000 AI calls
        canonical_id = find_similar(embedding)  # 1000 vector searches

# AFTER (Fast - Batch Processing)
# 1. Deduplicate
unique_names = set(normalize(item) for item in items)  # 1000 → 300 unique

# 2. Bulk exact match
exact_matches = check_exact_matches_bulk(unique_names)  # 1 DB query

# 3. Batch AI encoding
remaining = [n for n in unique_names if n not in exact_matches]  # 100 items
embeddings = model.encode(remaining)  # 1 AI call for 100 items (10x faster!)

# 4. Distribute results to all duplicates
for item in items:
    item['canonical_id'] = lookup_from_cache(item)
```

**Performance Gain**:
- DB Queries: 1000 → ~3 (99% reduction)
- AI Calls: 1000 → 1 (99% reduction, ~10x faster per call)
- Total Time: ~30 minutes → ~2 minutes (93% faster)

### Embedding Strategy

**Model**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Dimensions**: 384
- **Type**: Sentence embedding optimized for semantic similarity
- **Speed**: Fast inference (~1ms per item in batch mode)

**Storage**: PostgreSQL pgvector extension
```sql
CREATE EXTENSION vector;

CREATE TABLE canonical_item_embeddings (
    "CanonicalItemId" UUID PRIMARY KEY,
    "Embedding" vector(384),
    "CreatedAt" TIMESTAMP
);

-- Cosine similarity index
CREATE INDEX ON canonical_item_embeddings 
USING ivfflat ("Embedding" vector_cosine_ops);
```

**Similarity Calculation**:
```sql
-- pgvector cosine distance operator: <=>
-- Returns: 0 = identical, 2 = opposite
-- Convert to similarity: 1 - distance = similarity

SELECT 
    "CanonicalItemId",
    1 - ("Embedding" <=> %s::vector) AS similarity
FROM canonical_item_embeddings
ORDER BY "Embedding" <=> %s::vector
LIMIT 1
```

**Threshold**: 0.90 (90% similarity required for auto-match)
- Conservative threshold prevents false matches
- Allows for spelling variations and abbreviations
- Rejects semantically different items

### Memory Caching

```python
self._cache = {}  # Dict[normalized_name, canon_result]
```

**Purpose**:
- Avoid redundant DB/AI calls within same ETL run
- Common scenario: Multiple stores sell "Coca Cola 1.5L"
- First occurrence: Full pipeline (DB + AI)
- Subsequent occurrences: Instant cache hit

**Lifecycle**: Cleared between ETL runs

---

## Loading (Load Phase)

### PostgreSQL Loader

**File**: `loaders/postgres_loader.py`

Handles efficient insertion into `purchase_analytics_gold` table with smart update logic.

### Smart Upsert Strategy

**Goal**: Track price changes over time while avoiding duplicate records

**Algorithm**:
```python
For each (CanonicalItemId, StoreName) pair:
    1. Fetch latest record:
       SELECT "Id", "UnitPrice", "PurchaseDate"
       FROM purchase_analytics_gold
       WHERE "CanonicalItemId" = ? AND "StoreName" = ?
       ORDER BY "PurchaseDate" DESC
       LIMIT 1
    
    2. Compare prices:
       IF abs(latest_price - new_price) < 0.01:  # Same price
           → UPDATE purchase_analytics_gold
             SET "PurchaseDate" = NOW()
             WHERE "Id" = latest_id
           → Result: Timestamp refresh, no new record
       
       ELSE:  # Price changed
           → INSERT new record
           → Result: Historical price tracking
```

**Why This Design?**

✅ **Historical Tracking**: Preserves price change events
```sql
-- Price history for Coca Cola at MYDIN
Id | CanonicalItemId | StoreName | UnitPrice | PurchaseDate
---+----------------+-----------+-----------+-------------
1  | abc-123...     | MYDIN_NAT | 2.50      | 2025-12-01
2  | abc-123...     | MYDIN_NAT | 2.70      | 2025-12-15  (price increase!)
3  | abc-123...     | MYDIN_NAT | 2.70      | 2025-12-30  (same, timestamp updated)
```

✅ **Reduced Writes**: Skips inserts when prices are stable (~80% reduction)

✅ **Freshness Indicator**: `PurchaseDate` shows last verification

### Batch Processing

```python
def upsert_gold_price(self, records: List[Dict], batch_size: int = 100) -> Dict:
    """Process records in batches for efficiency"""
```

**Features**:
- **Default**: 100 records per batch
- **Connection Health**: Checks before each batch
- **Auto-Reconnect**: Handles broken connections gracefully
- **Transaction Safety**: Commits per batch, rollback on error
- **Progress Logging**: Updates every batch

**Example Log Output**:
```
INFO - Batch Progress: 100/1000 processed...
INFO - Batch Progress: 200/1000 processed...
INFO - Loaded 250 new records, skipped 750 unchanged
```

### Record Insertion

```python
def _insert_record(self, cur, record: Dict):
    """Insert single record into purchase_analytics_gold"""
    
    INSERT INTO purchase_analytics_gold (
        "Id",                    # New UUID
        "ItemId",                # New UUID  
        "Source",                # 'ETL' or scraper name
        "ItemName",              # Raw product name
        "CanonicalItemId",       # FK to canonical_items
        "UnitPrice",             # Price from scraper
        "TotalPrice",            # Same as UnitPrice (Quantity=1)
        "Quantity",              # Always 1 for scraped data
        "Category",              # Product category
        "PurchaseDate",          # NOW()
        "StoreName",             # Pricing Zone ID
        "StoreAddress",          # Regional address
        "Latitude",              # NULL (zone-based)
        "Longitude",             # NULL (zone-based)
        "LocationConfidence",    # 1.0 (zone data is authoritative)
        "PricingZoneId",         # Zone identifier
        "CreatedAt"              # NOW()
    )
```

**Note**: `Latitude` and `Longitude` are NULL for scraped data because it represents pricing zones, not specific store locations.

---

## Orchestration

### ETL Manager

**File**: `etl_manager.py`

Main coordinator that executes the full ETL pipeline.

#### Pipeline Flow

```python
class ETLManager:
    def run_pipeline(self):
        # 1. EXTRACT
        for scraper_config in SCRAPERS:
            records = self.run_scraper(**scraper_config)
            all_records.extend(records)
        
        # 2. TRANSFORM
        transformed = self.transform(all_records, batch_size=100)
        
        # 3. LOAD
        load_result = self.load(transformed)
        
        # 4. CLEANUP
        self.canonicalizer.close()
        self.loader.close()
        
        # 5. REPORT
        self.log_statistics()
```

#### Local Cache Feature

**Purpose**: Development efficiency - avoid re-scraping during canonicalization testing

**Configuration**:
```bash
# .env
USE_LOCAL_CACHE=true
```

**Behavior**:
```python
def run_scraper(self, scraper_class, **kwargs):
    if USE_LOCAL_CACHE:
        # Try loading from data/raw/{store}_{date}.json
        cached = self.load_from_local_cache(store_name)
        if cached:
            return cached
    
    # No cache, perform actual scrape
    scraper = scraper_class(**kwargs)
    records = scraper.run()
    
    # Always save for future use
    self.save_to_local_cache(records, store_name)
    return records
```

**Cache Location**: `data/raw/`
```
data/raw/
├── jaya_grocer_20260101.json
├── mydin_20260101.json
└── aeon_20260101.json
```

**Use Cases**:
- Testing canonicalization logic changes
- Debugging transformer issues
- Avoiding API rate limits during development

#### Statistics Tracking

```python
self.stats = {
    'scraped': 0,        # Total products scraped
    'canonicalized': 0,  # Successfully canonicalized
    'loaded': 0,         # New records inserted
    'errors': 0          # Errors encountered
}
```

**Output Example**:
```
============================================================
ETL Pipeline Summary:
  Scraped: 2,456 products
  Canonicalized: 2,456 products
  Loaded: 312 new records
  Skipped: 2,144 unchanged records
  Errors: 0
============================================================
Database Statistics:
  Total records: 15,234
  Unique items: 3,456
  Unique stores: 4
  With location: 0
============================================================
```

### Scheduler

**File**: `scheduler.py`

APScheduler-based daemon for automated nightly execution.

#### Configuration

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Default: 2:00 AM daily
scheduler.add_job(
    run_etl_job,
    trigger=CronTrigger(hour=2, minute=0),
    id='etl_job',
    name='Retail Price ETL Pipeline'
)
```

#### Features

**1. Graceful Shutdown**
```python
signal.signal(signal.SIGINT, shutdown)   # Ctrl+C
signal.signal(signal.SIGTERM, shutdown)  # systemd stop
```

**2. Error Handling**
```python
def run_etl_job(self):
    try:
        manager = ETLManager()
        manager.run_pipeline()
    except Exception as e:
        logger.error(f"Error in scheduled ETL job: {e}", exc_info=True)
        # Continue running - don't crash on single failure
```

**3. Systemd Integration**
```bash
# receiptly-etl.service
[Unit]
Description=Receiptly ETL Scheduler

[Service]
Type=simple
User=etl
WorkingDirectory=/opt/receiptly/retail-etl
ExecStart=/usr/bin/python3 scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Database Schema

### Core Tables

#### 1. canonical_items
**Purpose**: Master catalog of standardized products

```sql
CREATE TABLE canonical_items (
    "Id" UUID PRIMARY KEY,
    "Name" VARCHAR NOT NULL,         -- Normalized name
    "Category" VARCHAR,               -- Product category
    "CreatedAt" TIMESTAMP NOT NULL,
    "UpdatedAt" TIMESTAMP NOT NULL
);

CREATE INDEX idx_canonical_items_name ON canonical_items(LOWER("Name"));
```

**Example Data**:
```
Id                                   | Name                  | Category
-------------------------------------+-----------------------+------------------
550e8400-e29b-41d4-a716-446655440000 | coca cola 1 5l bottle | Beverages
7c9e6679-7425-40de-944b-e07fc1f90ae7 | wonda coffee kopi     | Beverages
```

#### 2. canonical_item_aliases
**Purpose**: Map alternative names to canonical items

```sql
CREATE TABLE canonical_item_aliases (
    "Id" UUID PRIMARY KEY,
    "CanonicalItemId" UUID NOT NULL REFERENCES canonical_items("Id"),
    "Alias" VARCHAR NOT NULL,         -- Alternative name (normalized)
    "CreatedAt" TIMESTAMP NOT NULL
);

CREATE INDEX idx_aliases_canonical ON canonical_item_aliases("CanonicalItemId");
CREATE INDEX idx_aliases_alias ON canonical_item_aliases(LOWER("Alias"));
```

**Example Data**:
```
CanonicalItemId                      | Alias
-------------------------------------+------------------
550e8400-e29b-41d4-a716-446655440000 | coke 1 5l
550e8400-e29b-41d4-a716-446655440000 | coca cola 1 5 liter
```

#### 3. canonical_item_embeddings
**Purpose**: Store vector embeddings for similarity search

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE canonical_item_embeddings (
    "CanonicalItemId" UUID PRIMARY KEY REFERENCES canonical_items("Id"),
    "Embedding" vector(384) NOT NULL,  -- 384-dim from all-MiniLM-L6-v2
    "CreatedAt" TIMESTAMP NOT NULL
);

-- Cosine similarity index (IVFFlat)
CREATE INDEX idx_embeddings_vector ON canonical_item_embeddings 
USING ivfflat ("Embedding" vector_cosine_ops)
WITH (lists = 100);
```

**Vector Operations**:
```sql
-- Find most similar items
SELECT 
    "CanonicalItemId",
    1 - ("Embedding" <=> '[0.123, 0.456, ...]'::vector) AS similarity
FROM canonical_item_embeddings
ORDER BY "Embedding" <=> '[0.123, 0.456, ...]'::vector
LIMIT 10;
```

#### 4. purchase_analytics_gold
**Purpose**: Unified price history (scraped + user receipts)

```sql
CREATE TABLE purchase_analytics_gold (
    "Id" UUID PRIMARY KEY,
    "ItemId" UUID NOT NULL,
    "Source" VARCHAR NOT NULL,              -- 'ETL', 'user_receipt', etc.
    "ItemName" VARCHAR NOT NULL,            -- Original product name
    "CanonicalItemId" UUID REFERENCES canonical_items("Id"),
    "UnitPrice" DECIMAL(10,2) NOT NULL,
    "TotalPrice" DECIMAL(10,2) NOT NULL,
    "Quantity" INTEGER NOT NULL DEFAULT 1,
    "Category" VARCHAR,
    "PurchaseDate" TIMESTAMP NOT NULL,
    "StoreName" VARCHAR NOT NULL,           -- Zone ID or specific store
    "StoreAddress" VARCHAR,
    "Latitude" DECIMAL(10,6),               -- NULL for scraped data
    "Longitude" DECIMAL(10,6),              -- NULL for scraped data
    "LocationConfidence" DECIMAL(3,2),
    "PricingZoneId" VARCHAR,                -- Zone identifier
    "CreatedAt" TIMESTAMP NOT NULL
);

CREATE INDEX idx_gold_canonical ON purchase_analytics_gold("CanonicalItemId");
CREATE INDEX idx_gold_store ON purchase_analytics_gold("StoreName");
CREATE INDEX idx_gold_date ON purchase_analytics_gold("PurchaseDate");
CREATE INDEX idx_gold_zone ON purchase_analytics_gold("PricingZoneId");
```

**Data Types**:

| Field | Scraped Data | User Receipt |
|-------|--------------|--------------|
| Source | 'ETL' | 'user_receipt' |
| StoreName | 'MYDIN_NATIONAL' | 'Mydin Bukit Jambul' |
| Latitude | NULL | 5.3456 |
| Longitude | NULL | 100.2789 |
| PricingZoneId | 'MYDIN_NATIONAL' | NULL or matched zone |
| LocationConfidence | 1.0 | 0.85 |

### Relationships

```
canonical_items (1) ─── (many) canonical_item_aliases
       │
       │ (1)
       │
       ├─── (1) canonical_item_embeddings
       │
       │ (1)
       │
       └─── (many) purchase_analytics_gold
```

---

## Configuration

### Settings File

**File**: `config/settings.py`

#### Database Configuration
```python
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'receiptly'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}
```

#### Active Scrapers
```python
SCRAPERS = [
    {
        'scraper_class': JayaGrocerScraper,
        'store_url': 'https://jggp.jayagrocer.com',
        'pricing_zone_id': 'JG_PENANG'
    },
    {
        'scraper_class': MydinScraper,
        'store_url': 'https://myapi.mydin.my/magento/products',
        'max_pages': 100,
        'pricing_zone_id': 'MYDIN_NATIONAL',
        'target_categories': [1222, 1513]  # Food & Groceries
    }
]
```

**Note**: Lotus and AEON scrapers are commented out - enable when ready

#### Canonicalization Settings
```python
SIMILARITY_THRESHOLD = 0.90  # 90% similarity for auto-match
```

**Tuning Guide**:
- **0.95+**: Very strict, more new items created
- **0.90**: Balanced (recommended)
- **0.85**: Lenient, more matches but higher false positive risk

#### Scheduler Settings
```python
SCHEDULE_HOUR = 2    # Run at 2:00 AM
SCHEDULE_MINUTE = 0
```

**Why 2 AM?**
- Low server load
- Retail APIs less busy
- Completes before business hours
- Daily price updates ready for morning users

#### Storage Paths
```python
RAW_DATA_DIR = './data/raw'           # Local cache storage
LOG_DIR = './logs'                     # ETL execution logs
LOG_FILE = './logs/etl.log'
USE_LOCAL_CACHE = os.getenv('USE_LOCAL_CACHE', 'false').lower() == 'true'
```

### Environment Variables

**File**: `.env` (create from `.env.example`)

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=receiptly
DB_USER=postgres
DB_PASSWORD=your_password

# Cache (development)
USE_LOCAL_CACHE=false

# Logging
LOG_DIR=./logs
```

---

## Key Design Patterns

### 1. Template Method Pattern
**Location**: `BaseScraper` abstract class

```python
class BaseScraper(ABC):
    def run(self):               # Template method
        raw = self.scrape()      # Abstract - subclass implements
        cleaned = self.clean()   # Concrete - shared logic
        return cleaned
```

**Benefits**: Consistent scraper behavior, DRY principle

### 2. Strategy Pattern
**Location**: Canonicalization pipeline

```python
# Multiple strategies, tried in order
strategies = [
    check_exact_match,
    check_alias_match,
    find_similar_embedding,
    create_new_item
]
```

**Benefits**: Flexible matching, easy to add new strategies

### 3. Batch Processing Pattern
**Location**: Throughout the pipeline

```python
# Transform
for i in range(0, total, batch_size):
    batch = records[i:i+batch_size]
    process_batch(batch)  # Bulk operations

# Load
for i in range(0, total, batch_size):
    batch = records[i:i+batch_size]
    upsert_batch(batch)  # Transaction per batch
```

**Benefits**: Controlled memory usage, better error isolation

### 4. Cache-Aside Pattern
**Location**: Canonicalizer memory cache

```python
def canonicalize(name):
    if name in self._cache:
        return self._cache[name]  # Fast path
    
    result = expensive_lookup(name)  # Slow path
    self._cache[name] = result
    return result
```

**Benefits**: Massive performance gain for repeated items

### 5. Repository Pattern
**Location**: `PostgresLoader`

```python
class PostgresLoader:
    def upsert_gold_price(records): pass
    def get_stats(): pass
    # Abstracts database operations
```

**Benefits**: Clean separation, easier testing, database agnostic

### 6. Adapter Pattern
**Location**: `JayaGrocerScraper`

```python
class JayaGrocerScraper(BaseScraper):
    def __init__(self):
        self.original_scraper = OriginalScraper()  # Existing code
    
    def scrape(self):
        products = self.original_scraper.scrape()  # Reuse
        return self.transform_to_schema(products)   # Adapt
```

**Benefits**: Reuse existing code without modification

---

## Performance Optimizations

### 1. Batch AI Encoding
**Impact**: 10x faster than individual encoding

```python
# SLOW: Individual encoding
for item in items:
    embedding = model.encode(item)  # 100ms each × 1000 = 100 seconds

# FAST: Batch encoding
embeddings = model.encode(items)  # 10 seconds total
```

**Why?**: GPU parallelization, reduced overhead

### 2. Memory Caching
**Impact**: 99% reduction in redundant processing

```python
self._cache = {}  # In-memory cache per ETL run

# First "Coca Cola": Full pipeline (200ms)
# Next 50 "Coca Cola": Cache hit (< 1ms)
```

**Typical Run**: 2,000 products → 500 unique → 1,500 cache hits

### 3. Bulk Database Queries
**Impact**: 99% reduction in DB round trips

```python
# SLOW: Individual queries
for item in items:
    check_exact_match(item)  # 1000 queries

# FAST: Bulk query
check_exact_matches_bulk(items)  # 1 query
```

### 4. Conditional Inserts
**Impact**: 80% reduction in database writes

```python
# Skip insert if price unchanged
if abs(old_price - new_price) < 0.01:
    UPDATE "PurchaseDate" only  # Cheap
else:
    INSERT new record           # Expensive
```

**Typical Scenario**: 2,000 scraped → 400 price changes → 1,600 skipped

### 5. Connection Pooling
**Impact**: Handles broken connections gracefully

```python
def connect(self):
    if not self.conn or self.conn.closed or is_broken:
        self.conn = psycopg2.connect(**config)
```

**Benefit**: Resilient to network issues, long-running processes

### 6. Deduplication Before Processing
**Impact**: Reduces AI calls by 60-70%

```python
# 1000 items → 300 unique normalized names
normalized_map = {}
for item in items:
    norm = normalize(item)
    normalized_map[norm].append(item)

# Process only 300 unique → distribute to 1000
```

### 7. Local Cache for Development
**Impact**: Avoid re-scraping during development

```bash
USE_LOCAL_CACHE=true  # Skip scraping, use JSON files
```

**Time Saved**: 5-10 minutes per test run

---

## Execution Flow Summary

### Full Pipeline Execution

```
1. STARTUP
   ├─ Load configuration
   ├─ Initialize database connections
   ├─ Load SentenceTransformer model
   └─ Create log file

2. EXTRACT (Scraping)
   ├─ JayaGrocerScraper
   │  ├─ Shopify API calls
   │  ├─ Parse JSON responses
   │  └─ Return 800 products
   ├─ MydinScraper
   │  ├─ GraphQL API calls (categories 1222, 1513)
   │  ├─ Paginate 100 pages per category
   │  └─ Return 1,600 products
   └─ Total: 2,400 raw products

3. TRANSFORM (Canonicalization)
   ├─ Normalize all names
   ├─ Deduplicate → 600 unique names
   ├─ Bulk exact match → 400 hits
   ├─ Bulk alias match → 100 hits
   ├─ Batch AI encoding → 100 items
   │  ├─ Generate embeddings
   │  ├─ Vector similarity search
   │  ├─ Find 80 matches (>0.90 similarity)
   │  └─ Create 20 new canonical items
   └─ Attach canonical IDs to all 2,400 records

4. LOAD (Database Insertion)
   ├─ Batch upsert (100 records per batch)
   ├─ Check latest price for each (CanonicalItemId, StoreName)
   ├─ Insert 450 new records (price changed)
   ├─ Update 1,950 timestamps (price same)
   └─ Commit transactions

5. CLEANUP
   ├─ Close database connections
   ├─ Log statistics
   └─ Exit

Total Time: ~2-3 minutes for 2,400 products
```

### Scheduled Execution (Production)

```
Daily at 2:00 AM:
├─ Scheduler wakes up
├─ Triggers ETL pipeline
├─ Logs results to logs/etl.log
└─ Waits until next 2:00 AM
```

---

## Troubleshooting Guide

### Common Issues

**1. Scraper Returns Zero Products**
```python
# Check logs for:
- HTTP errors (403, 429, 500)
- Timeout exceptions
- JSON parsing errors

# Solutions:
- Verify API endpoint still valid
- Check rate limiting
- Update selectors if DOM changed (Selenium scrapers)
```

**2. Canonicalization Creates Too Many New Items**
```python
# Symptoms: Every scrape creates duplicates
# Causes:
- Similarity threshold too high (>0.95)
- Text normalization insufficient
- Embeddings not stored properly

# Solutions:
- Lower threshold to 0.90
- Enhance normalization (e.g., remove brand prefixes)
- Check pgvector index exists
```

**3. Database Connection Errors**
```python
# Error: "psycopg2.OperationalError: connection closed"
# Solution: Auto-reconnect logic handles this
# Verify: Check logs for "Reconnecting..." messages
```

**4. Memory Issues with Large Batches**
```python
# Error: "MemoryError" during batch encoding
# Solution: Reduce batch_size in config
CANONICALIZATION_BATCH_SIZE = 50  # Default 100
```

### Debug Mode

**Enable verbose logging**:
```python
logging.basicConfig(level=logging.DEBUG)
```

**Use local cache for testing**:
```bash
USE_LOCAL_CACHE=true
python etl_manager.py
```

**Manual scraper test**:
```bash
cd scrapers
python mydin.py  # Run individual scraper
```

---

## Future Enhancements

### Planned Improvements

1. **Smart Alias Generation**: Automatically create aliases from high-similarity matches
2. **Brand Extraction**: Parse brand names for better categorization
3. **Price Alert System**: Detect unusual price changes (>20% swing)
4. **Category Standardization**: Map store categories to unified taxonomy
5. **Multi-language Support**: Handle Malay/Chinese product names
6. **Image Embeddings**: Visual similarity for better matching (CLIP model)
7. **Incremental Updates**: Track "last scraped" to only fetch new/changed products
8. **Monitoring Dashboard**: Real-time ETL status and statistics

---

## References

### Key Files
- `scrapers/base_scraper.py` - Abstract scraper interface
- `scrapers/mydin.py` - MYDIN GraphQL scraper
- `etl_transformers/canonicalizer.py` - AI-powered canonicalization
- `loaders/postgres_loader.py` - Database loading logic
- `etl_manager.py` - Main orchestrator
- `scheduler.py` - Automated scheduling
- `config/settings.py` - Configuration management

### External Dependencies
- **SentenceTransformers**: `all-MiniLM-L6-v2` model
- **pgvector**: PostgreSQL vector extension
- **psycopg2**: PostgreSQL adapter
- **APScheduler**: Task scheduling
- **Selenium**: Web automation
- **requests**: HTTP client

### Related Documentation
- `MYDIN_SCRAPING_ANALYSIS.md` - MYDIN API reverse engineering
- `LOTUSS_SCRAPING_ANALYSIS.md` - Lotus's scraper implementation
- `AEON2GO_SCRAPING_ANALYSIS.md` - AEON API details

---

**Document Version**: 1.0  
**Last Updated**: January 1, 2026  
**Maintained By**: Receiptly ETL Team

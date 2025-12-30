# Retail ETL Pipeline

Unified ETL tool for scraping, transforming (canonicalizing), and loading product price data from Malaysian retail chains into PostgreSQL.

## Features

- **Regional Pricing**: Hybrid model supporting:
  - **Zone-based Pricing**: Scraped data (e.g., `JG_PENANG`, `MYDIN_NATIONAL`)
  - **Location-based Pricing**: User-uploaded receipts (specific GPS coordinates)
- **Store Management**: Seeding script to map physical stores to pricing zones automatically.
- **Smart Canonicalization**: Multi-strategy approach using:
  - Text normalization
  - Exact match lookup
  - Alias matching
  - Vector similarity (sentence-transformers with 384-dim embeddings)
  - Automatic creation of new canonical items
- **Efficient Loading**: Conditional updates - only inserts when prices change
- **Automated Scheduling**: Runs nightly at 2 AM via APScheduler
- **Category Preservation**: Maintains product categories from source data

## Directory Structure

```
retail-etl/
├── scrapers/          # Store-specific scrapers
│   ├── base_scraper.py
│   └── jaya_grocer.py
├── transformers/      # Canonicalization logic
│   └── canonicalizer.py
├── loaders/          # Database loading
│   └── postgres_loader.py
├── config/           # Configuration files
│   └── settings.py
├── tests/            # Unit and integration tests
├── logs/             # ETL execution logs
├── etl_manager.py    # Main orchestrator
├── scheduler.py      # APScheduler daemon
└── requirements.txt  # Python dependencies
```

## Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension
- Database migration applied (see below)

## Installation

1. **Install Python dependencies:**
   ```bash
   cd retail-etl
   pip install -r requirements.txt
   ```

2. **Apply database migration:**
   ```bash
   cd ../dotnet-api
   dotnet ef database update --project src/Receiptly.Infrastructure --startup-project src/Receiptly.API
   ```

3. **Configure environment:**
   ```bash
   cd ../retail-etl
   cp .env.example .env
   # Edit .env with your database credentials
   ```

## Configuration

Edit `.env` file:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=receiptly
DB_USER=postgres
DB_PASSWORD=your_password

LOG_DIR=./logs
```

## Usage

### Run ETL Manually

```bash
python etl_manager.py
```

This will:
1. Scrape products from all configured stores
2. Canonicalize product names using embeddings
3. Load data into `purchase_analytics_gold` table
4. Log results to `logs/etl.log`

### Run Scheduler (Daemon Mode)

```bash
python scheduler.py
```

The scheduler will run the ETL pipeline daily at 2 AM.

### Run Store Seeding (One-Time Setup)

To populate the `Stores` table mapping physical locations to pricing zones:

```bash
python seed_stores.py
```

To verify the seeded data:
```bash
python check_stores.py
```

### Test Individual Scraper

```bash
python scrapers/jaya_grocer.py
```

## Adding a New Scraper

1. **Create scraper file** in `scrapers/`:

```python
from scrapers.base_scraper import BaseScraper
from typing import List, Dict

class NewStoreScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            store_name="Store Name",
            store_address="Store Address",
            latitude=0.0,
            longitude=0.0
        )
    
    def scrape(self) -> List[Dict]:
        # Implement scraping logic
        products = []
        # ... scraping code ...
        return products
```

2. **Register in `config/settings.py`:**

```python
from scrapers.new_store import NewStoreScraper

SCRAPERS = [
    {'scraper_class': JayaGrocerScraper, 'store_url': '...'},
    {'scraper_class': NewStoreScraper},  # Add here
]
```

## Database Schema

### Canonical Items Tables

- **`canonical_items`**: Unique product definitions
  - `id` (UUID): Primary key
  - `name` (VARCHAR): Normalized product name
  - `category` (VARCHAR): Product category
  - `created_at`, `updated_at`: Timestamps

- **`canonical_item_aliases`**: Alternative names
  - `id` (UUID): Primary key
  - `canonical_item_id` (UUID): FK to canonical_items
  - `alias` (VARCHAR): Alternative name
  - `created_at`: Timestamp

- **`canonical_item_embeddings`**: Vector embeddings
  - `canonical_item_id` (UUID): PK, FK to canonical_items
  - `embedding` (VECTOR(384)): Sentence embedding
  - `created_at`: Timestamp

### Updated Table

- **`purchase_analytics_gold`**: Now includes
  - `canonical_item_id` (UUID): FK to canonical_items (nullable)
  - `pricing_zone_id` (VARCHAR): ID of the pricing zone (e.g. `JG_PENANG`)
  - Indexed for fast lookups

### New Table

- **`stores`**: Physical store locations
  - `id` (UUID): Primary Key
  - `name` (VARCHAR): Store branch name
  - `retail_chain` (VARCHAR): e.g. "Jaya Grocer", "Mydin"
  - `pricing_zone_id` (VARCHAR): Maps store to a price list
  - `latitude`/`longitude`: GPS coordinates
  - `address`: Physical address

## How It Works

### 1. Extract (Scrape)
- Each scraper inherits from `BaseScraper`
- Implements `scrape()` method returning standardized product dicts
- `clean()` method validates and adds store metadata

### 2. Transform (Canonicalize)
Multi-layered canonicalization strategy:

1. **Normalize**: Lowercase, remove special chars
2. **Exact Match**: Check `canonical_items` table
3. **Alias Match**: Check `canonical_item_aliases` table
4. **Vector Similarity**: 
   - Generate embedding using `all-MiniLM-L6-v2`
   - Query `canonical_item_embeddings` using pgvector
   - Match if similarity > 0.90
5. **Create New**: If no match, create new canonical item

### 3. Load
- Check last recorded price for `canonical_item_id` + `store_name`
- **If price changed**: Insert new record
- **If price same**: Update `updated_at` timestamp only
- Maintains complete price history

## Logging

Logs are written to `logs/etl.log` (or `/var/log/receiptly/etl.log` in production).

Example log output:
```
2025-12-29 02:00:00 - INFO - Starting ETL pipeline
2025-12-29 02:00:05 - INFO - Scraped 1234 products from Jaya Grocer Gurney Paragon
2025-12-29 02:01:30 - INFO - Canonicalized 1234 products
2025-12-29 02:02:15 - INFO - Loaded 87 new records, skipped 1147 unchanged
```

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/receiptly-etl.service`:

```ini
[Unit]
Description=Receiptly ETL Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=receiptly
WorkingDirectory=/opt/receiptly/retail-etl
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable receiptly-etl
sudo systemctl start receiptly-etl
sudo systemctl status receiptly-etl
```

## Troubleshooting

### Database Connection Errors
- Verify `.env` credentials
- Ensure PostgreSQL is running
- Check pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`

### Import Errors
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python path includes project root

### Scraper Failures
- Check store website availability
- Verify API endpoints haven't changed
- Review logs for specific error messages

## Next Steps

- [x] Implement MYDIN scraper adapter
- [x] Implement Lotus scraper
- [x] Implement Aeon scraper
- [x] Implement Regional Pricing (Stores + Zones)
- [x] Add Store Seeding script
- [ ] Add unit tests for canonicalization
- [ ] Add integration tests for ETL pipeline
- [ ] Set up monitoring and alerting

## Plan: Build Unified ETL Tool for Retail Price Data

Design and implement a modular ETL pipeline in Python that extracts product prices from Malaysian retail chains (Jaya Grocer, MYDIN, Lotus, Aeon), performs advanced item name canonicalization using the Canonical Items layer (normalize text, alias lookup, vector similarity matching with embeddings generated during transformation, create items immediately, store aliases), and loads data into PostgreSQL with conditional updates only when prices change, using APScheduler for nightly automation at 2 AM.

### Steps
1. Modify PostgreSQL schemas via EF Core migration: Add canonical_items, canonical_item_embeddings, canonical_item_aliases tables; update purchase_analytics_gold and items to reference canonical_item_id (UUID) instead of canonical_name.
2. Implement advanced transformation pipeline with sentence-transformers for embeddings, pgvector for similarity queries, alias lookups, and real-time canonical item creation during ETL (no delayed jobs).
3. Create database loading module with upsert logic using SQLAlchemy's ON CONFLICT, updating only if price changed and refreshing UpdatedAt/CreatedAt timestamps, ensuring Gold loads with canonical_item_id.
4. Integrate existing scrapers and develop new ones for Lotus and Aeon, adding configuration-driven execution and error handling, with alias accumulation for user corrections.
5. Configure APScheduler daemon with BlockingScheduler, cron trigger at 2 AM, comprehensive logging to /var/log/receiptly/etl.log, idempotency checks, and graceful shutdown handling.

### Further Considerations
1. Ensure append-only behavior for purchase_analytics_gold by inserting new records only on price changes, maintaining historical data integrity, with Gold consuming only canonical IDs for pricing.
2. Test canonicalization logic extensively with real data samples to achieve high similarity scores (>0.90 for auto-match), handle edge cases like new products, and backfill existing data from canonical_cache.
3. Deploy as a systemd service for production reliability, monitor job execution via APScheduler's event listeners and database job store, and enable pgvector extension in PostgreSQL for embedding queries.

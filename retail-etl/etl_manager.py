"""
ETL Manager - Main orchestrator for the retail price ETL pipeline.

Coordinates scraping, transformation (canonicalization), and loading.
"""
import sys
import os
from typing import List, Dict
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl_transformers.canonicalizer import Canonicalizer
from loaders.postgres_loader import PostgresLoader
from config.settings import DB_CONFIG, SCRAPERS, LOG_FILE, RAW_DATA_DIR, USE_LOCAL_CACHE, CHECKPOINT_FILE
import json


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ETLManager:
    """Orchestrates the ETL pipeline."""
    
    def __init__(self):
        """Initialize ETL components."""
        self.canonicalizer = Canonicalizer(DB_CONFIG)
        self.loader = PostgresLoader(DB_CONFIG)
        self.stats = {
            'scraped': 0,
            'canonicalized': 0,
            'loaded': 0,
            'errors': 0
        }
        self.checkpoint_file = CHECKPOINT_FILE
    
    def save_to_local_cache(self, records: List[Dict], store_name: str):
        """Save scraped records to local JSON file."""
        filename = f"{store_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(RAW_DATA_DIR, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(records, f, indent=2)
            logger.info(f"Saved {len(records)} records to local cache: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save to local cache: {e}")

    def load_from_local_cache(self, store_name: str) -> List[Dict]:
        """Load records from the most recent local JSON file."""
        try:
            files = [f for f in os.listdir(RAW_DATA_DIR) if f.startswith(store_name.lower().replace(' ', '_'))]
            if not files:
                return []
            
            # Get the latest file
            latest_file = sorted(files)[-1]
            filepath = os.path.join(RAW_DATA_DIR, latest_file)
            
            with open(filepath, 'r') as f:
                records = json.load(f)
            
            logger.info(f"Loaded {len(records)} records from local cache: {latest_file}")
            return records
        except Exception as e:
            logger.error(f"Failed to load from local cache: {e}")
            return []
    
    def save_checkpoint(self, data: Dict):
        """Save checkpoint data to resume pipeline after interruption."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Checkpoint saved: {len(data.get('transformed', []))} transformed records")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Dict:
        """Load checkpoint data if exists."""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Checkpoint loaded: {len(data.get('transformed', []))} previously transformed records")
                return data
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
        return {}
    
    def clear_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logger.info("Checkpoint cleared")
        except Exception as e:
            logger.error(f"Failed to clear checkpoint: {e}")

    def run_scraper(self, scraper_class, **kwargs) -> List[Dict]:
        """
        Run a single scraper with optional local caching.
        """
        store_name = scraper_class.__name__.replace('Scraper', '')
        
        if USE_LOCAL_CACHE:
            cached_records = self.load_from_local_cache(store_name)
            if cached_records:
                self.stats['scraped'] += len(cached_records)
                return cached_records
            logger.info(f"No local cache found for {store_name}, proceeding to scrape.")

        try:
            scraper = scraper_class(**kwargs)
            records = scraper.run()
            self.stats['scraped'] += len(records)
            logger.info(f"Scraped {len(records)} products from {scraper.store_name}")
            
            # Always save to cache for future debug runs
            if records:
                self.save_to_local_cache(records, store_name)
                
            return records
        except Exception as e:
            logger.error(f"Error running scraper {scraper_class.__name__}: {e}")
            self.stats['errors'] += 1
            return []
    
    def transform(self, records: List[Dict], batch_size: int = 25, checkpoint_data: Dict = None) -> List[Dict]:
        """
        Transform records with canonicalization using Amazon-style approach.
        Scraped items are processed as MASTERS (IsMaster=true) in batches.
        Supports resume from checkpoint after interruption.
        
        Args:
            records: Raw scraped records to transform
            batch_size: Number of records per batch
            checkpoint_data: Previously transformed records to skip
        """
        # Step 1: Check database for items already processed in previous runs
        logger.info("Checking database for existing items...")
        existing_items = self.loader.get_existing_items(records)
        
        # Separate records into already-processed and new
        already_processed = []
        new_records = []
        
        for record in records:
            item_name = record.get('item_name', '').strip()
            store_name = record.get('store_name', '').strip()
            lookup_key = f"{item_name}|{store_name}"
            
            if lookup_key in existing_items:
                # Item already exists in DB - use existing canonical ID
                record['canonical_item_id'] = existing_items[lookup_key]
                record['match_method'] = 'existing_in_db'
                already_processed.append(record)
            else:
                new_records.append(record)
        
        logger.info(f"Found {len(already_processed)} items already in database, {len(new_records)} new items to process")
        
        # Step 2: Load previously transformed records from checkpoint (current run)
        transformed = checkpoint_data.get('transformed', []) if checkpoint_data else []
        checkpoint_count = len(transformed)
        
        if checkpoint_count > 0:
            logger.info(f"Resuming from checkpoint: {checkpoint_count} records already transformed in this run")
            new_records = new_records[checkpoint_count:]  # Skip already processed in current run
        
        # Combine already-processed items with checkpoint items
        all_transformed = already_processed + transformed
        
        total = len(new_records)
        if total == 0:
            logger.info("All records already processed (from database or checkpoint)")
            return all_transformed
        
        logger.info(f"Transforming {total} remaining new records...")
        
        # Step 3: Process new records
        for i in range(0, total, batch_size):
            batch = new_records[i:i + batch_size]
            try:
                # Batch process all items at once (MUCH faster)
                canonical_ids = self.canonicalizer.process_scraped_items_batch(batch)
                
                # Assign canonical IDs back to records
                for record, canonical_id in zip(batch, canonical_ids):
                    record['canonical_item_id'] = canonical_id
                    record['match_method'] = 'master_created'
                    all_transformed.append(record)
                    self.stats['canonicalized'] += 1
                
                # Save checkpoint after each batch (only new transformed items)
                self.save_checkpoint({'transformed': transformed + batch})
                
                logger.info(f"Transform Progress: {min(i + batch_size, total)}/{total} new products...")
                
            except Exception as e:
                logger.error(f"Error in batch transformation at batch {i}: {e}")
                logger.exception(e)
                self.stats['errors'] += 1
                # Save checkpoint even on error so we can resume
                self.save_checkpoint({'transformed': transformed + batch[:len(canonical_ids)] if 'canonical_ids' in locals() else transformed})
                raise  # Re-raise to stop pipeline but keep checkpoint
        
        logger.info(f"Successfully processed {len(all_transformed)} total products ({len(already_processed)} from DB, {len(all_transformed) - len(already_processed)} newly canonicalized)")
        
        # Ensure all canonical items are committed before load phase
        logger.info("Flushing canonical items to database...")
        try:
            self.canonicalizer.connect()  # Ensure connection is alive
            self.canonicalizer.conn.commit()  # Final commit
            logger.info("✓ All canonical items committed")
        except Exception as e:
            logger.error(f"Error committing canonical items: {e}")
            raise
        
        return all_transformed
    
    def load(self, records: List[Dict]) -> Dict:
        """
        Load records into the database.
        
        Args:
            records: Transformed records with canonical_item_id
            
        Returns:
            Loading statistics
        """
        try:
            result = self.loader.upsert_gold_price(records, 500)  # Smaller batches to avoid timeout
            self.stats['loaded'] = result['inserted']
            logger.info(f"Loaded {result['inserted']} new records, skipped {result['skipped']} unchanged")
            return result
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.stats['errors'] += 1
            return {'inserted': 0, 'skipped': 0, 'total': 0}
    
    def run_pipeline(self):
        """Execute the full ETL pipeline for all configured scrapers."""
        logger.info("=" * 60)
        logger.info(f"Starting ETL pipeline at {datetime.utcnow().isoformat()}")
        logger.info("=" * 60)
        
        # Check for existing checkpoint
        checkpoint_data = self.load_checkpoint()
        
        all_records = []
        
        # Extract: Run all scrapers
        for scraper_config in SCRAPERS:
            records = self.run_scraper(**scraper_config)
            all_records.extend(records)
        
        if not all_records:
            logger.warning("No records scraped. Exiting.")
            return
        
        # Transform: Canonicalize (with resume support)
        try:
            transformed_records = self.transform(all_records, checkpoint_data=checkpoint_data)
        except Exception as e:
            logger.error(f"Transform failed: {e}. Checkpoint saved for resume.")
            self.canonicalizer.close()
            self.loader.close()
            raise
        
        # Load: Insert into database
        load_result = self.load(transformed_records)
        
        # Clear checkpoint after successful load
        self.clear_checkpoint()
        
        # Cleanup
        self.canonicalizer.close()
        self.loader.close()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("ETL Pipeline Summary:")
        logger.info(f"  Scraped: {self.stats['scraped']} products")
        logger.info(f"  Canonicalized: {self.stats['canonicalized']} products")
        logger.info(f"  Loaded: {self.stats['loaded']} new records")
        logger.info(f"  Skipped: {load_result.get('skipped', 0)} unchanged records")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)
        
        # Get database stats
        db_stats = self.loader.get_stats()
        logger.info("Database Statistics:")
        logger.info(f"  Total records: {db_stats['total_records']}")
        logger.info(f"  Unique items: {db_stats['unique_items']}")
        logger.info(f"  Unique stores: {db_stats['unique_stores']}")
        logger.info(f"  With location: {db_stats['with_location']}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    try:
        manager = ETLManager()
        manager.run_pipeline()
    except Exception as e:
        logger.error(f"Fatal error in ETL pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

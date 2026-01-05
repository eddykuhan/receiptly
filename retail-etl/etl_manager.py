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
        
        Args:
            records: Raw scraped records to transform
            batch_size: Number of records per batch
            checkpoint_data: Not used in chunked mode (kept for compatibility)
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
        
        # Combine already-processed items
        all_transformed = already_processed[:]
        
        total = len(new_records)
        if total == 0:
            logger.info("All records already processed in database")
            return all_transformed
        
        logger.info(f"Transforming {total} new records in batches of {batch_size}...")
        
        # Step 2: Process new records
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
                
                if (i + batch_size) % 100 == 0 or i + batch_size >= total:
                    logger.info(f"Transform Progress: {min(i + batch_size, total)}/{total} new products...")
                
            except Exception as e:
                logger.error(f"Error in batch transformation at batch {i}: {e}")
                logger.exception(e)
                self.stats['errors'] += 1
                raise  # Re-raise to stop pipeline
        
        logger.info(f"✓ Transformed {len(all_transformed)} total products ({len(already_processed)} from DB, {total} newly canonicalized)")
        
        # Ensure all canonical items are committed before load phase
        logger.info("Flushing canonical items to database...")
        try:
            # Check connection health before commit
            self.canonicalizer.connect()
            with self.canonicalizer.conn.cursor() as cur:
                cur.execute("SELECT 1")  # Health check
            self.canonicalizer.conn.commit()
            logger.info("✓ All canonical items committed")
        except Exception as e:
            logger.error(f"Error committing canonical items: {e}")
            logger.error("Connection may have been lost. Attempting reconnect...")
            try:
                self.canonicalizer.connect()
                self.canonicalizer.conn.commit()
                logger.info("✓ Reconnected and committed")
            except Exception as e2:
                logger.error(f"Reconnect failed: {e2}")
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
    
    def run_pipeline(self, chunk_size: int = 1000):
        """
        Execute the full ETL pipeline for all configured scrapers with chunked processing.
        
        Processes data in chunks to avoid connection timeouts and memory issues:
        1. Scrape all data
        2. Split into chunks (default 1000 items)
        3. For each chunk: transform → load → commit
        
        Args:
            chunk_size: Number of items to process per chunk (default 1000)
        """
        logger.info("=" * 60)
        logger.info(f"Starting ETL pipeline at {datetime.utcnow().isoformat()}")
        logger.info(f"Chunk size: {chunk_size} items per batch")
        logger.info("=" * 60)
        
        # Check for existing checkpoint
        checkpoint_data = self.load_checkpoint()
        chunks_completed = checkpoint_data.get('chunks_completed', 0) if checkpoint_data else 0
        
        all_records = []
        
        # Extract: Run all scrapers
        for scraper_config in SCRAPERS:
            records = self.run_scraper(**scraper_config)
            all_records.extend(records)
        
        if not all_records:
            logger.warning("No records scraped. Exiting.")
            return
        
        # Split into chunks
        total_records = len(all_records)
        num_chunks = (total_records + chunk_size - 1) // chunk_size  # Ceiling division
        logger.info(f"Processing {total_records} records in {num_chunks} chunks of {chunk_size}")
        
        total_loaded = 0
        total_skipped = 0
        
        # Process each chunk: transform → load immediately
        for chunk_idx in range(chunks_completed, num_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min(start_idx + chunk_size, total_records)
            chunk_records = all_records[start_idx:end_idx]
            
            logger.info("=" * 60)
            logger.info(f"Processing Chunk {chunk_idx + 1}/{num_chunks} (items {start_idx + 1}-{end_idx})")
            logger.info("=" * 60)
            
            try:
                # Transform this chunk
                transformed_chunk = self.transform(chunk_records, checkpoint_data=None)
                
                # Immediately load this chunk
                load_result = self.load(transformed_chunk)
                total_loaded += load_result.get('inserted', 0)
                total_skipped += load_result.get('skipped', 0)
                
                # Update checkpoint
                self.save_checkpoint({
                    'chunks_completed': chunk_idx + 1,
                    'total_chunks': num_chunks,
                    'records_loaded': total_loaded,
                    'records_skipped': total_skipped
                })
                
                logger.info(f"✓ Chunk {chunk_idx + 1}/{num_chunks} completed: {load_result.get('inserted', 0)} loaded, {load_result.get('skipped', 0)} skipped")
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_idx + 1}: {e}")
                logger.error(f"Checkpoint saved. Resume from chunk {chunk_idx + 1}")
                self.canonicalizer.close()
                self.loader.close()
                raise
        
        # Clear checkpoint after successful completion
        self.clear_checkpoint()
        
        # Cleanup
        self.canonicalizer.close()
        self.loader.close()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("ETL Pipeline Summary:")
        logger.info(f"  Scraped: {self.stats['scraped']} products")
        logger.info(f"  Canonicalized: {self.stats['canonicalized']} products")
        logger.info(f"  Loaded: {total_loaded} new records")
        logger.info(f"  Skipped: {total_skipped} unchanged records")
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

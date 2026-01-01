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
from config.settings import DB_CONFIG, SCRAPERS, LOG_FILE, RAW_DATA_DIR, USE_LOCAL_CACHE
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
    
    def transform(self, records: List[Dict], batch_size: int = 100) -> List[Dict]:
        """
        Transform records with canonicalization using Amazon-style approach.
        Scraped items are processed as MASTERS (IsMaster=true) in batches.
        """
        transformed = []
        total = len(records)
        
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            try:
                # Batch process all items at once (MUCH faster)
                canonical_ids = self.canonicalizer.process_scraped_items_batch(batch)
                
                # Assign canonical IDs back to records
                for record, canonical_id in zip(batch, canonical_ids):
                    record['canonical_item_id'] = canonical_id
                    record['match_method'] = 'master_created'
                    transformed.append(record)
                    self.stats['canonicalized'] += 1
                
                logger.info(f"Transform Progress: {min(i + batch_size, total)}/{total} products...")
                
            except Exception as e:
                logger.error(f"Error in batch transformation: {e}")
                logger.exception(e)
                self.stats['errors'] += 1
        
        logger.info(f"Successfully processed {len(transformed)} products as masters")
        return transformed
    
    def load(self, records: List[Dict]) -> Dict:
        """
        Load records into the database.
        
        Args:
            records: Transformed records with canonical_item_id
            
        Returns:
            Loading statistics
        """
        try:
            result = self.loader.upsert_gold_price(records,10000)
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
        
        all_records = []
        
        # Extract: Run all scrapers
        for scraper_config in SCRAPERS:
            records = self.run_scraper(**scraper_config)
            all_records.extend(records)
        
        if not all_records:
            logger.warning("No records scraped. Exiting.")
            return
        
        # Transform: Canonicalize
        transformed_records = self.transform(all_records)
        
        # Load: Insert into database
        load_result = self.load(transformed_records)
        
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

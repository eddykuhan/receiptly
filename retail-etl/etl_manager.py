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
from config.settings import DB_CONFIG, SCRAPERS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/kuhan/Projects/receiptly/retail-etl/etl.log'),
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
    
    def run_scraper(self, scraper_class, **kwargs) -> List[Dict]:
        """
        Run a single scraper.
        
        Args:
            scraper_class: Scraper class to instantiate
            **kwargs: Arguments for scraper initialization
            
        Returns:
            List of scraped product records
        """
        try:
            scraper = scraper_class(**kwargs)
            records = scraper.run()
            self.stats['scraped'] += len(records)
            logger.info(f"Scraped {len(records)} products from {scraper.store_name}")
            return records
        except Exception as e:
            logger.error(f"Error running scraper {scraper_class.__name__}: {e}")
            self.stats['errors'] += 1
            return []
    
    def transform(self, records: List[Dict]) -> List[Dict]:
        """
        Transform records by canonicalizing product names.
        
        Args:
            records: Raw scraped records
            
        Returns:
            Records with canonical_item_id added
        """
        transformed = []
        
        for record in records:
            try:
                # Canonicalize the item name
                canon_result = self.canonicalizer.canonicalize(
                    record['item_name'],
                    record.get('category', 'Unknown')
                )
                
                # Add canonical_item_id to record
                record['canonical_item_id'] = canon_result['canonical_item_id']
                record['match_method'] = canon_result['match_method']
                
                transformed.append(record)
                self.stats['canonicalized'] += 1
                
            except Exception as e:
                logger.error(f"Error canonicalizing '{record.get('item_name')}': {e}")
                self.stats['errors'] += 1
        
        logger.info(f"Canonicalized {len(transformed)} products")
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
            result = self.loader.upsert_gold_price(records)
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

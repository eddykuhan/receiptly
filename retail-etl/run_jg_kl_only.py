"""
Run ETL for JG_KL only to load missing data.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl_manager import ETLManager
from scrapers.jaya_grocer import JayaGrocerScraper
from config.settings import DB_CONFIG
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run ETL for JG_KL only."""
    logger.info("=" * 60)
    logger.info("Running ETL for JG_KL only")
    logger.info("=" * 60)
    
    manager = ETLManager()
    
    # Clear any existing checkpoint
    manager.clear_checkpoint()
    
    # Scrape JG_KL (will use cache if available)
    records = manager.run_scraper(
        scraper_class=JayaGrocerScraper,
        store_url='https://klec.jayagrocer.com',
        pricing_zone_id='JG_KL'
    )
    
    logger.info(f"Scraped/loaded {len(records)} JG_KL products from cache")
    
    if not records:
        logger.error("No records found. Exiting.")
        return
    
    # Transform
    logger.info("Transforming records...")
    transformed = manager.transform(records)
    
    # Load
    logger.info("Loading to database...")
    result = manager.load(transformed)
    
    # Cleanup
    manager.canonicalizer.close()
    manager.loader.close()
    
    logger.info("=" * 60)
    logger.info("JG_KL ETL Complete")
    logger.info(f"  Loaded: {result['inserted']} new records")
    logger.info(f"  Skipped: {result['skipped']} unchanged records")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()

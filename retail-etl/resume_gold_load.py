"""
Resume gold layer insert from existing canonical items.

Use this when transformation completed but gold layer insert failed.
"""
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loaders.postgres_loader import PostgresLoader
from config.settings import DB_CONFIG, RAW_DATA_DIR, SCRAPERS
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_scraped_data_with_canonical_ids():
    """Load scraped data and enrich with canonical IDs from database."""
    import psycopg2
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    all_records = []
    
    # Define store mappings to cache file patterns and SourceType
    store_mappings = {
        'JG_PENANG': {
            'cache_patterns': ['jayagrocer', 'jaya_grocer_(penang)'],
            'source_type': 'JG_PENANG'
        },
        'MYDIN_NATIONAL': {
            'cache_patterns': ['mydin'],
            'source_type': 'MYDIN_NATIONAL'
        },
        'LOTUS_NATIONAL': {
            'cache_patterns': ['lotus', 'lotus_malaysia'],
            'source_type': 'Lotus Malaysia'  # Database uses this value
        }
    }
    
    # Load each scraper's cached data
    for scraper_config in SCRAPERS:
        pricing_zone_id = scraper_config['pricing_zone_id']
        store_config = store_mappings.get(pricing_zone_id, {
            'cache_patterns': [pricing_zone_id.lower()],
            'source_type': pricing_zone_id
        })
        possible_names = store_config['cache_patterns']
        source_type = store_config['source_type']
        
        cache_path = None
        
        # Try all possible cache file names (with and without date)
        for base_name in possible_names:
            # Try with today's date
            for ext in ['', f"_{datetime.now().strftime('%Y%m%d')}", f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"]:
                test_file = f"{base_name}{ext}.json"
                test_path = os.path.join(RAW_DATA_DIR, test_file)
                if os.path.exists(test_path):
                    cache_path = test_path
                    break
            if cache_path:
                break
            
            # Try with wildcard (latest file)
            import glob
            pattern = os.path.join(RAW_DATA_DIR, f"{base_name}*.json")
            matches = glob.glob(pattern)
            if matches:
                cache_path = max(matches, key=os.path.getctime)  # Latest file
                break
        
        if not cache_path:
            logger.warning(f"No cache file found for {pricing_zone_id} - skipping")
            continue
        
        logger.info(f"Loading {pricing_zone_id} from {cache_path}")
        
        with open(cache_path, 'r') as f:
            records = json.load(f)
        
        logger.info(f"  Loaded {len(records)} records from cache")
        
        # Load ALL canonical items for this store at once (MUCH faster than individual queries)
        logger.info(f"  Loading canonical items for {source_type}...")
        cur.execute('''
            SELECT "Id", "Name"
            FROM canonical_items 
            WHERE "SourceType" = %s
        ''', (source_type,))
        
        # Create lookup dictionary: name -> canonical_id
        canonical_lookup = {row[1]: str(row[0]) for row in cur.fetchall()}
        logger.info(f"  Loaded {len(canonical_lookup)} canonical items")
        
        # Match records to canonical items using in-memory lookup
        matched_count = 0
        for record in records:
            item_name = record.get('item_name', '')
            
            # Clean the item name
            # 1. Remove "- 1 UNIT" / "- 1 PACK" suffix (from old JG cache)
            item_name_cleaned = item_name.replace(' - 1 UNIT', '').replace(' - 1 unit', '')
            item_name_cleaned = item_name_cleaned.replace(' - 1 PACK', '').replace(' - 1 pack', '')
            
            # 2. Remove Lotus prefix codes (e.g., "CP25_", "FV01_")
            if '_' in item_name_cleaned and pricing_zone_id == 'LOTUS_NATIONAL':
                parts = item_name_cleaned.split('_', 1)
                if len(parts) == 2 and parts[0].replace('CP', '').replace('FV', '').replace('GM', '').replace('BK', '').isdigit():
                    item_name_cleaned = parts[1]  # Remove prefix
            
            # Lookup canonical ID from in-memory dictionary
            canonical_id = canonical_lookup.get(item_name_cleaned)
            if canonical_id:
                record['canonical_item_id'] = canonical_id
                # Update the item_name in record to match canonical (without suffix/prefix)
                record['item_name'] = item_name_cleaned
                all_records.append(record)
                matched_count += 1
        
        logger.info(f"  Matched {matched_count}/{len(records)} records to canonical items")
    
    cur.close()
    conn.close()
    
    return all_records


def main():
    """Resume gold layer loading from existing canonical items."""
    logger.info("=== Resuming Gold Layer Load ===")
    
    # Load scraped data with canonical IDs
    logger.info("Loading scraped data and matching to canonical items...")
    records = load_scraped_data_with_canonical_ids()
    
    if not records:
        logger.error("No records found to load!")
        return
    
    logger.info(f"Found {len(records)} records with canonical IDs")
    
    # Load to gold layer
    loader = PostgresLoader(DB_CONFIG)
    logger.info("Inserting into purchase_analytics_gold...")
    
    try:
        result = loader.upsert_gold_price(records, batch_size=500)
        logger.info(f"✅ Gold layer load complete:")
        logger.info(f"   Inserted: {result['inserted']}")
        logger.info(f"   Updated: {result['updated']}")
        logger.info(f"   Errors: {result['errors']}")
    except Exception as e:
        logger.error(f"❌ Gold layer load failed: {e}")
        logger.exception(e)
        raise


if __name__ == "__main__":
    main()

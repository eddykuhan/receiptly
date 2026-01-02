"""
Quick test script for canonicalization without full ETL run.

Tests cross-store matching with small sample datasets.
"""
import json
import logging
import os
from datetime import datetime
from etl_transformers.canonicalizer import Canonicalizer
from config.settings import DB_CONFIG

# Enable DEBUG logging for canonicalizer components
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set specific loggers to INFO to reduce noise
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def load_sample_data(file_path, sample_size=50):
    """Load a sample of products from cached data."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Take first N products
    sample = data[:sample_size]
    
    # Clean item names (remove "- 1 UNIT")
    for item in sample:
        if 'item_name' in item:
            item['item_name'] = item['item_name'].replace(' - 1 UNIT', '').replace(' - 1 unit', '')
    
    return sample


def test_canonicalization():
    """Test canonicalization with small samples from each store."""
    
    # Load samples - focus on products likely to match
    logger.info("Loading sample data...")
    jg_sample = load_sample_data('data/raw/jayagrocer_20251230.json', sample_size=200)
    lotus_sample = load_sample_data('data/raw/lotus_20260101_182308.json', sample_size=200)
    mydin_sample = load_sample_data('data/raw/mydin_20251230.json', sample_size=200)
    
    logger.info(f"Loaded {len(jg_sample)} JG + {len(lotus_sample)} Lotus + {len(mydin_sample)} Mydin = {len(jg_sample) + len(lotus_sample) + len(mydin_sample)} total products")
    
    # Show some sample names to verify cleaning
    logger.info("\nSample product names:")
    for i in range(min(3, len(jg_sample))):
        logger.info(f"  JG: {jg_sample[i]['item_name']}")
    for i in range(min(3, len(lotus_sample))):
        logger.info(f"  Lotus: {lotus_sample[i]['item_name']}")
    
    # Initialize canonicalizer
    canonicalizer = Canonicalizer(DB_CONFIG)
    
    # Process ALL stores together in sequence (so later stores can match earlier ones)
    all_batches = []
    
    # Prepare batches
    for item in jg_sample:
        all_batches.append({
            'item_name': item['item_name'],
            'category': item.get('category', 'Unknown'),
            'store_name': 'JG_PENANG'
        })
    
    for item in lotus_sample:
        all_batches.append({
            'item_name': item['item_name'],
            'category': item.get('category', 'Unknown'),
            'store_name': 'Lotus Malaysia'
        })
    
    for item in mydin_sample:
        all_batches.append({
            'item_name': item['item_name'],
            'category': item.get('category', 'Unknown'),
            'store_name': 'MYDIN_NATIONAL'
        })
    
    logger.info(f"\n=== Processing {len(all_batches)} products from all stores ===")
    
    # Process in batches of 100 (like real ETL)
    batch_size = 100
    all_canonical_ids = []
    
    for i in range(0, len(all_batches), batch_size):
        batch = all_batches[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_batches) + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)...")
        
        start = datetime.now()
        canonical_ids = canonicalizer.process_scraped_items_batch(batch)
        duration = (datetime.now() - start).total_seconds()
        
        all_canonical_ids.extend(canonical_ids)
        
        logger.info(f"  Batch {batch_num}: {len(set(canonical_ids))} unique IDs from {len(canonical_ids)} products ({duration:.2f}s)")
    
    # Analyze results
    logger.info("\n=== Cross-Store Match Analysis ===")
    total_products = len(all_canonical_ids)
    unique_canonical_ids = len(set(all_canonical_ids))
    
    logger.info(f"Total products processed: {total_products}")
    logger.info(f"Total unique canonical items: {unique_canonical_ids}")
    logger.info(f"Matched products (cross-store): {total_products - unique_canonical_ids}")
    
    match_rate = ((total_products - unique_canonical_ids) / total_products) * 100
    logger.info(f"Match rate: {match_rate:.1f}%")
    
    # Find examples by querying DB
    logger.info("\n=== Querying database for cross-store matches ===")
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT ci."Name", ci."Brand", ci."Size", ci."SourceType",
               COUNT(*) as product_count
        FROM canonical_items ci
        GROUP BY ci."Id", ci."Name", ci."Brand", ci."Size", ci."SourceType"
        HAVING COUNT(*) > 1
        LIMIT 5
    ''')
    
    examples = cur.fetchall()
    if examples:
        logger.info("Products appearing multiple times (duplicates):")
        for ex in examples:
            logger.info(f"  {ex[0]} | Brand: {ex[1]} | Size: {ex[2]} | Source: {ex[3]} | Count: {ex[4]}")
    
    cur.close()
    conn.close()
    
    canonicalizer.close()


if __name__ == '__main__':
    test_canonicalization()

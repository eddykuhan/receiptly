"""
Test with common grocery brands that are likely in multiple stores.
"""
import json
import logging
from datetime import datetime
from etl_transformers.canonicalizer import Canonicalizer
from config.settings import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common brands likely to be in multiple stores
COMMON_BRANDS = [
    'dutch lady', 'milo', 'maggi', 'nestle', 'nescafe', 'ayam brand',
    'adabi', 'cap', 'sunquick', 'farmfresh', 'farm fresh', 'marigold',
    'f&n', 'yeos', 'ajinomoto', 'knorr', 'heinz', 'kellogg', 'quaker'
]

def find_common_products(file_path, brands, max_per_brand=5):
    """Find products from common brands."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    products = []
    for item in data:
        item_name = item.get('item_name', '').lower()
        # Remove "- 1 UNIT" suffix
        if 'item_name' in item:
            item['item_name'] = item['item_name'].replace(' - 1 UNIT', '').replace(' - 1 unit', '')
        
        # Check if any common brand is in the name
        for brand in brands:
            if brand in item_name and len(products) < max_per_brand * len(brands):
                products.append(item)
                break
    
    return products

# Load products from common brands
logger.info("Loading products from common brands...")
jg_products = find_common_products('data/raw/jayagrocer_20251230.json', COMMON_BRANDS, max_per_brand=10)
lotus_products = find_common_products('data/raw/lotus_20260101_182308.json', COMMON_BRANDS, max_per_brand=10)
mydin_products = find_common_products('data/raw/mydin_20251230.json', COMMON_BRANDS, max_per_brand=10)

logger.info(f"Found {len(jg_products)} JG + {len(lotus_products)} Lotus + {len(mydin_products)} Mydin = {len(jg_products) + len(lotus_products) + len(mydin_products)} branded products")

# Prepare batches
canonicalizer = Canonicalizer(DB_CONFIG)
all_batches = []

for item in jg_products:
    all_batches.append({'item_name': item['item_name'], 'category': item.get('category', 'Unknown'), 'store_name': 'JG_PENANG'})
for item in lotus_products:
    all_batches.append({'item_name': item['item_name'], 'category': item.get('category', 'Unknown'), 'store_name': 'Lotus Malaysia'})
for item in mydin_products:
    all_batches.append({'item_name': item['item_name'], 'category': item.get('category', 'Unknown'), 'store_name': 'MYDIN_NATIONAL'})

logger.info(f"\n=== Processing {len(all_batches)} branded products ===")

# Process in batches
batch_size = 100
all_canonical_ids = []

for i in range(0, len(all_batches), batch_size):
    batch = all_batches[i:i+batch_size]
    canonical_ids = canonicalizer.process_scraped_items_batch(batch)
    all_canonical_ids.extend(canonical_ids)
    logger.info(f"Batch {i//batch_size + 1}: {len(set(canonical_ids))} unique from {len(canonical_ids)} products")

# Analysis
total = len(all_canonical_ids)
unique = len(set(all_canonical_ids))
matches = total - unique
match_rate = (matches / total) * 100

logger.info(f"\n=== Results ===")
logger.info(f"Total products: {total}")
logger.info(f"Unique canonical items: {unique}")
logger.info(f"Cross-store matches: {matches}")
logger.info(f"Match rate: {match_rate:.1f}%")

if match_rate > 5:
    logger.info("✅ Good match rate for branded products!")
elif match_rate > 1:
    logger.info("⚠️  Moderate match rate - some matching working")
else:
    logger.info("❌ Low match rate - matching may need tuning")

canonicalizer.close()

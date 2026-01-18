"""
Minimal test to debug why cross-store matching isn't working.
"""
import logging
from etl_transformers.canonicalizer import Canonicalizer
from config.settings import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test with known products that SHOULD match
test_products = [
    # Batch 1: JG products
    {'item_name': 'Dutch Lady Full Cream Milk 1L', 'category': 'Dairy', 'store_name': 'JG_PENANG'},
    {'item_name': 'Milo Activ-Go 1kg', 'category': 'Beverages', 'store_name': 'JG_PENANG'},
    
    # Batch 2: Lotus products (should match above)
    {'item_name': 'DUTCH LADY FULL CREAM MILK 1L', 'category': 'Dairy', 'store_name': 'Lotus Malaysia'},
    {'item_name': 'MILO ACTIV GO 1KG', 'category': 'Beverages', 'store_name': 'Lotus Malaysia'},
]

canonicalizer = Canonicalizer(DB_CONFIG)

logger.info("=== Processing Batch 1 (JG) ===")
batch1 = test_products[:2]
ids1 = canonicalizer.process_scraped_items_batch(batch1)
logger.info(f"Created {len(set(ids1))} unique canonical IDs from {len(ids1)} products")
for item, cid in zip(batch1, ids1):
    logger.info(f"  {item['item_name']} → {cid[:8]}...")

logger.info("\n=== Processing Batch 2 (Lotus) ===")
batch2 = test_products[2:]
ids2 = canonicalizer.process_scraped_items_batch(batch2)
logger.info(f"Created {len(set(ids2))} unique canonical IDs from {len(ids2)} products")
for item, cid in zip(batch2, ids2):
    logger.info(f"  {item['item_name']} → {cid[:8]}...")

logger.info("\n=== Match Analysis ===")
if ids1[0] == ids2[0]:
    logger.info(f"✅ Dutch Lady MATCHED! Same canonical ID: {ids1[0][:8]}...")
else:
    logger.error(f"❌ Dutch Lady FAILED to match!")
    logger.error(f"   JG ID:    {ids1[0][:8]}...")
    logger.error(f"   Lotus ID: {ids2[0][:8]}...")

if ids1[1] == ids2[1]:
    logger.info(f"✅ Milo MATCHED! Same canonical ID: {ids1[1][:8]}...")
else:
    logger.error(f"❌ Milo FAILED to match!")
    logger.error(f"   JG ID:    {ids1[1][:8]}...")
    logger.error(f"   Lotus ID: {ids2[1][:8]}...")

canonicalizer.close()

"""
Test that incremental batching actually reuses canonical IDs.
Creates 3 batches of duplicate items to verify matching works.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import DB_CONFIG
from etl_transformers.canonicalizer import Canonicalizer
import psycopg2

# Truncate first
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute("TRUNCATE TABLE canonical_items CASCADE")
cur.execute("TRUNCATE TABLE canonical_item_embeddings CASCADE")
conn.commit()
cur.close()
conn.close()

# Create test data: 300 items total
# Batch 1 (items 0-99): Unique products
# Batch 2 (items 100-199): 50 unique + 50 duplicates from batch 1
# Batch 3 (items 200-299): 50 unique + 50 duplicates from batch 1

test_items = []

# Batch 1: 100 unique items
for i in range(100):
    test_items.append({
        'item_name': f'Nestle Product {i} 100g',
        'category': 'Food',
        'store_name': 'Store A'
    })

# Batch 2: 50 unique + 50 duplicates
for i in range(50):
    test_items.append({
        'item_name': f'Maggi Product {i} 200g',  # Unique
        'category': 'Food',
        'store_name': 'Store B'
    })
for i in range(50):
    # DUPLICATE from batch 1
    test_items.append({
        'item_name': f'Nestle Product {i} 100g',  # Same as batch 1
        'category': 'Food',
        'store_name': 'Store B'  # Different store!
    })

# Batch 3: 50 unique + 50 duplicates
for i in range(50):
    test_items.append({
        'item_name': f'Adabi Product {i} 300g',  # Unique
        'category': 'Food',
        'store_name': 'Store C'
    })
for i in range(50):
    # DUPLICATE from batch 1
    test_items.append({
        'item_name': f'Nestle Product {i} 100g',  # Same as batch 1
        'category': 'Food',
        'store_name': 'Store C'  # Different store!
    })

print("🧪 INCREMENTAL BATCHING TEST")
print("="*60)
print(f"Total items: {len(test_items)}")
print(f"Expected canonical items: 200")
print(f"   - Batch 1: 100 unique Nestle products")
print(f"   - Batch 2: 50 unique Maggi + 50 reused Nestle (items 0-49)")
print(f"   - Batch 3: 50 unique Adabi + 50 reused Nestle (items 0-49)")
print(f"\nExpected matches: 100 (50 in batch 2 + 50 in batch 3)")
print("="*60)

# Process with canonicalizer
canonicalizer = Canonicalizer(DB_CONFIG)
canonical_ids = canonicalizer.process_scraped_items_batch(test_items)

print(f"\n✓ Processed {len(canonical_ids)} items")

# Analyze results
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM canonical_items")
actual_canonical = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT id) FROM (SELECT unnest(%s::uuid[]) as id) t", (canonical_ids,))
unique_ids = cur.fetchone()[0]

print(f"\n📊 RESULTS:")
print(f"   Canonical items in DB: {actual_canonical}")
print(f"   Unique canonical IDs used: {unique_ids}")
print(f"   Expected: 200")

# Check for matches
batch2_items = canonical_ids[100:200]
batch3_items = canonical_ids[200:300]
batch1_first50 = canonical_ids[0:50]

batch2_matches = sum(1 for i in range(50, 100) if batch2_items[i] in batch1_first50)
batch3_matches = sum(1 for i in range(50, 100) if batch3_items[i] in batch1_first50)

print(f"\n🎯 MATCHING:")
print(f"   Batch 2 duplicates matched: {batch2_matches}/50")
print(f"   Batch 3 duplicates matched: {batch3_matches}/50")
print(f"   Total matches: {batch2_matches + batch3_matches}/100")

if unique_ids == 200 and (batch2_matches + batch3_matches) == 100:
    print(f"\n✅ SUCCESS: Incremental batching is working perfectly!")
    print(f"   - Items 0-99 created 100 new masters")
    print(f"   - Items 100-199 created 50 new + reused 50 existing")
    print(f"   - Items 200-299 created 50 new + reused 50 existing")
elif unique_ids == 300:
    print(f"\n❌ FAILURE: No matches found!")
    print(f"   All 300 items created separate canonical IDs")
    print(f"   → Incremental batching is NOT working")
else:
    print(f"\n⚠️  PARTIAL: Some matching occurred but not as expected")
    print(f"   Expected 200 canonical items, got {unique_ids}")

cur.close()
conn.close()

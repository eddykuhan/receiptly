"""
Test incremental batching fix with small subset of data.
Processes ~1000 items total to verify cross-store matching works.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import DB_CONFIG
from etl_transformers.canonicalizer import Canonicalizer
from loaders.postgres_loader import PostgresLoader
import psycopg2
import json

# Number of items to test from each source
TEST_SIZE_PER_SOURCE = 1000

def load_test_data():
    """Load small subset from each source."""
    test_items = []
    
    # Jaya Grocer
    jaya_file = "data/raw/jayagrocer_20260101.json"
    if os.path.exists(jaya_file):
        with open(jaya_file, 'r') as f:
            data = json.load(f)
            test_items.extend(data[:TEST_SIZE_PER_SOURCE])
            print(f"✓ Loaded {len(data[:TEST_SIZE_PER_SOURCE])} Jaya Grocer items")
    
    # Mydin
    mydin_file = "data/raw/mydin_20251230.json"
    if os.path.exists(mydin_file):
        with open(mydin_file, 'r') as f:
            data = json.load(f)
            test_items.extend(data[:TEST_SIZE_PER_SOURCE])
            print(f"✓ Loaded {len(data[:TEST_SIZE_PER_SOURCE])} Mydin items")
    
    # Lotus
    lotus_file = "data/raw/lotus_20260101_182308.json"
    if os.path.exists(lotus_file):
        with open(lotus_file, 'r') as f:
            data = json.load(f)
            test_items.extend(data[:TEST_SIZE_PER_SOURCE])
            print(f"✓ Loaded {len(data[:TEST_SIZE_PER_SOURCE])} Lotus items")
    
    return test_items

def analyze_results():
    """Analyze the test results."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("\n" + "="*60)
    print("TEST RESULTS ANALYSIS")
    print("="*60)
    
    # Overall counts
    cur.execute("SELECT COUNT(*) FROM canonical_items")
    canonical_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM purchase_analytics_gold")
    gold_count = cur.fetchone()[0]
    
    print(f"\n📊 Items Processed:")
    print(f"   Canonical Items: {canonical_count:,}")
    print(f"   Gold Records: {gold_count:,}")
    
    # Cross-store matching
    cur.execute("""
        SELECT COUNT(DISTINCT "CanonicalItemId")
        FROM purchase_analytics_gold
        GROUP BY "CanonicalItemId"
        HAVING COUNT(DISTINCT "Source") > 1
    """)
    cross_store_count = cur.fetchone()[0] if cur.rowcount > 0 else 0
    
    match_rate = (cross_store_count / canonical_count * 100) if canonical_count > 0 else 0
    
    print(f"\n🎯 Cross-Store Matching:")
    print(f"   Products in Multiple Stores: {cross_store_count:,}")
    print(f"   Match Rate: {match_rate:.2f}%")
    
    # Distribution
    cur.execute("""
        SELECT store_count, COUNT(*) as products
        FROM (
            SELECT "CanonicalItemId", COUNT(DISTINCT "Source") as store_count
            FROM purchase_analytics_gold
            GROUP BY "CanonicalItemId"
        ) t
        GROUP BY store_count
        ORDER BY store_count DESC
    """)
    print(f"\n   Distribution:")
    for row in cur.fetchall():
        stores, products = row
        pct = (products / canonical_count * 100) if canonical_count > 0 else 0
        print(f"     In {stores} store(s): {products:>4,} products ({pct:>5.1f}%)")
    
    # Sample matches
    print(f"\n🏆 SAMPLE CROSS-STORE MATCHES:")
    cur.execute("""
        SELECT 
            ci."Brand",
            ci."Name",
            COUNT(DISTINCT pag."Source") as store_count,
            STRING_AGG(DISTINCT pag."Source", ', ' ORDER BY pag."Source") as stores,
            MIN(pag."UnitPrice") as min_price,
            MAX(pag."UnitPrice") as max_price
        FROM canonical_items ci
        JOIN purchase_analytics_gold pag ON ci."Id" = pag."CanonicalItemId"
        GROUP BY ci."Id", ci."Brand", ci."Name"
        HAVING COUNT(DISTINCT pag."Source") > 1
        ORDER BY store_count DESC, (MAX(pag."UnitPrice") - MIN(pag."UnitPrice")) DESC
        LIMIT 10
    """)
    
    for row in cur.fetchall():
        brand, name, store_count, stores, min_price, max_price = row
        price_diff = float(max_price) - float(min_price)
        print(f"\n   {brand or 'N/A'} - {name[:60]}")
        print(f"     Stores: {stores}")
        print(f"     Price: RM {float(min_price):.2f} - RM {float(max_price):.2f} (diff: RM {price_diff:.2f})")
    
    # Assessment
    print(f"\n{'='*60}")
    print(f"📈 ASSESSMENT:")
    if match_rate >= 15:
        print(f"   ✅ EXCELLENT: {match_rate:.2f}% match rate - Fix is working!")
        print(f"   → Safe to run full ETL")
    elif match_rate >= 10:
        print(f"   ✓ GOOD: {match_rate:.2f}% match rate")
        print(f"   → Should work well on full dataset")
    elif match_rate >= 5:
        print(f"   ⚠️  MODERATE: {match_rate:.2f}% match rate")
        print(f"   → May need tuning")
    else:
        print(f"   ❌ LOW: {match_rate:.2f}% match rate")
        print(f"   → Fix may not be working correctly")
    
    print("="*60)
    
    cur.close()
    conn.close()

def main():
    print("🧪 TESTING INCREMENTAL BATCHING FIX")
    print("="*60)
    
    # Truncate tables
    print("\n1️⃣  Truncating test tables...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE purchase_analytics_gold CASCADE")
    cur.execute("TRUNCATE TABLE canonical_items CASCADE")
    cur.execute("TRUNCATE TABLE canonical_item_embeddings CASCADE")
    conn.commit()
    cur.close()
    conn.close()
    print("   ✓ Tables truncated")
    
    # Load test data
    print(f"\n2️⃣  Loading test data ({TEST_SIZE_PER_SOURCE} items per source)...")
    test_items = load_test_data()
    print(f"   ✓ Total test items: {len(test_items):,}")
    
    # Transform (canonicalize)
    print(f"\n3️⃣  Canonicalizing items (mini-batch size: 100)...")
    canonicalizer = Canonicalizer(DB_CONFIG)
    canonical_ids = canonicalizer.process_scraped_items_batch(test_items)
    
    # Assign canonical IDs to items
    for item, canonical_id in zip(test_items, canonical_ids):
        item['canonical_item_id'] = canonical_id
        item['match_method'] = 'test'
    
    print(f"   ✓ Canonicalized {len(canonical_ids):,} items")
    
    # Load to gold
    print(f"\n4️⃣  Loading to purchase_analytics_gold...")
    loader = PostgresLoader(DB_CONFIG)
    result = loader.upsert_gold_price(test_items, batch_size=500)
    print(f"   ✓ Inserted {result['inserted']:,} records")
    
    # Analyze results
    print(f"\n5️⃣  Analyzing results...")
    analyze_results()

if __name__ == "__main__":
    main()

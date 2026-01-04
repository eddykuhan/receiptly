#!/usr/bin/env python3
"""Truncate database tables to start fresh."""

import sys
sys.path.insert(0, '/Users/kuhan/Projects/receiptly/retail-etl')
sys.path.insert(0, '/Users/kuhan/Projects/receiptly/shared-lib')

from config.settings import DB_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 100)
print("DATABASE TRUNCATION - CLEARING ALL DATA")
print("=" * 100)

# Confirm before proceeding
print("\n⚠️  WARNING: This will DELETE ALL DATA from the following tables:")
print("   - canonical_items")
print("   - purchase_analytics_gold")
print("   - canonical_item_embeddings")
print("\nThis action CANNOT be undone!")

response = input("\nType 'YES' to confirm truncation: ")

if response != 'YES':
    print("\n❌ Truncation cancelled")
    sys.exit(0)

print("\n🗑️  Proceeding with truncation...\n")

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

try:
    # Get counts before truncation
    print("Before truncation:")
    print("-" * 100)
    
    cur.execute('SELECT COUNT(*) as count FROM canonical_items')
    canonical_count = cur.fetchone()['count']
    print(f"  canonical_items: {canonical_count:,} rows")
    
    cur.execute('SELECT COUNT(*) as count FROM purchase_analytics_gold')
    gold_count = cur.fetchone()['count']
    print(f"  purchase_analytics_gold: {gold_count:,} rows")
    
    cur.execute("SELECT COUNT(*) as count FROM canonical_item_embeddings")
    embeddings_count = cur.fetchone()['count']
    print(f"  canonical_item_embeddings: {embeddings_count:,} rows")
    
    print("\nTruncating tables...")
    print("-" * 100)
    
    # Truncate in correct order (respecting foreign keys)
    cur.execute('TRUNCATE TABLE purchase_analytics_gold CASCADE')
    print("✓ Truncated purchase_analytics_gold")
    
    cur.execute('TRUNCATE TABLE canonical_item_embeddings CASCADE')
    print("✓ Truncated canonical_item_embeddings")
    
    cur.execute('TRUNCATE TABLE canonical_items CASCADE')
    print("✓ Truncated canonical_items")
    
    conn.commit()
    
    # Verify truncation
    print("\nAfter truncation:")
    print("-" * 100)
    
    cur.execute('SELECT COUNT(*) as count FROM canonical_items')
    canonical_count = cur.fetchone()['count']
    print(f"  canonical_items: {canonical_count:,} rows")
    
    cur.execute('SELECT COUNT(*) as count FROM purchase_analytics_gold')
    gold_count = cur.fetchone()['count']
    print(f"  purchase_analytics_gold: {gold_count:,} rows")
    
    cur.execute('SELECT COUNT(*) as count FROM canonical_item_embeddings')
    embeddings_count = cur.fetchone()['count']
    print(f"  canonical_item_embeddings: {embeddings_count:,} rows")
    
    print("\n" + "=" * 100)
    print("✅ DATABASE TRUNCATION COMPLETE")
    print("=" * 100)
    print("\nAll tables have been cleared. You can now run the ETL pipeline with:")
    print("  cd retail-etl && ./run_etl_nosleep.sh")
    
except Exception as e:
    print(f"\n❌ Error during truncation: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    cur.close()
    conn.close()

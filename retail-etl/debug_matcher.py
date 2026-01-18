"""
Debug the matching logic for specific products.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import DB_CONFIG
from etl_transformers.matcher import AmazonStyleMatcher
from etl_transformers.attribute_extractor import AttributeExtractor
import psycopg2

# Two Maggi products that should match
product1 = "Maggi Hot Cup Chicken 58g x 6pcs/pack"  # Jaya Grocer
product2 = "MAGGI HOT CUP CHICKEN 57G"               # Lotus

print("🔍 MATCHER DEBUG TEST\n")
print(f"Product 1: {product1}")
print(f"Product 2: {product2}\n")

# Extract attributes
extractor = AttributeExtractor()
attrs1 = extractor.extract_all_attributes(product1)
attrs2 = extractor.extract_all_attributes(product2)

print("📊 Extracted Attributes:")
print(f"\nProduct 1:")
for key, val in attrs1.items():
    print(f"   {key:20} {val}")

print(f"\nProduct 2:")
for key, val in attrs2.items():
    print(f"   {key:20} {val}")

# Get the canonical item for product 2 (simulating it's already in DB)
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
    SELECT 
        ci."Id" as id,
        ci."Name" as item_name,
        ci."Brand" as brand,
        ci."Size" as size,
        ci."SizeNormalized" as size_normalized,
        ci."SizeUnit" as size_unit,
        ci."PackCount" as pack_count,
        ci."Variant" as variant,
        ci."NameTokens" as name_tokens,
        ci."Category" as category,
        ci."IsMaster" as is_master,
        ci."Confidence" as confidence
    FROM canonical_items ci
    JOIN purchase_analytics_gold pag ON ci."Id" = pag."CanonicalItemId"
    WHERE ci."Name" LIKE %s
    LIMIT 1
""", (f'%{product2}%',))

candidate = cur.fetchone()
if not candidate:
    print(f"\n❌ Product 2 not found in database")
    sys.exit(1)

# Convert to dict
candidate_dict = {
    'id': candidate[0],
    'item_name': candidate[1],
    'brand': candidate[2],
    'size': candidate[3],
    'size_normalized': candidate[4],
    'size_unit': candidate[5],
    'pack_count': candidate[6],
    'variant': candidate[7],
    'name_tokens': candidate[8],
    'category': candidate[9],
    'is_master': candidate[10],
    'confidence': candidate[11]
}

print(f"\n📦 Candidate from DB:")
for key, val in candidate_dict.items():
    print(f"   {key:20} {val}")

# Test the matcher
matcher = AmazonStyleMatcher()  # Will create its own embedding model

query_attrs = {
    'item_name': product1,
    'brand': attrs1['brand'],
    'size': attrs1['size'],
    'size_normalized': attrs1['size_normalized'],
    'size_unit': attrs1['size_unit'],
    'category': 'Unknown',
    'name_tokens': attrs1['name_tokens'],
    'pack_count': attrs1['pack_count']  # Add pack_count
}

print(f"\n🔧 Query attributes:")
for key, val in query_attrs.items():
    print(f"   {key:20} {val}")

best_match, score, breakdown = matcher.find_best_match(
    query_attributes=query_attrs,
    candidates=[candidate_dict],
    threshold=0.65
)

print(f"\n🎯 MATCHING RESULTS:")
print(f"   Score: {score:.4f}")
print(f"   Threshold: 0.65")
print(f"   Match: {'✓ YES' if best_match else '❌ NO'}")

print(f"\n📊 Score Breakdown:")
for key, val in breakdown.items():
    print(f"   {key:30} {val:.4f}" if isinstance(val, float) else f"   {key:30} {val}")

if score < 0.65:
    print(f"\n💡 Score {score:.4f} is below threshold 0.65")
    print(f"   Need to lower threshold or improve scoring weights")

cur.close()
conn.close()

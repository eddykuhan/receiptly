"""Test why Lotus Nescafe isn't matching Jaya Nescafe."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import DB_CONFIG
from etl_transformers.matcher import AmazonStyleMatcher
from etl_transformers.attribute_extractor import AttributeExtractor
import psycopg2

# Products that should match
jaya_product = "Nescafe Gold Refill Pack 170g"
lotus_product = "NESCAFE GOLD REFILL PACK 170G"

print("🔍 MATCHING TEST: Lotus vs Jaya Nescafe\n")
print(f"Jaya:  {jaya_product}")
print(f"Lotus: {lotus_product}\n")

# Extract attributes
extractor = AttributeExtractor()
jaya_attrs = extractor.extract_all_attributes(jaya_product)
lotus_attrs = extractor.extract_all_attributes(lotus_product)

print("📊 Jaya attributes:")
for key, val in jaya_attrs.items():
    print(f"   {key:20} {val}")

print("\n📊 Lotus attributes:")
for key, val in lotus_attrs.items():
    print(f"   {key:20} {val}")

# Get Jaya canonical item from DB
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
    WHERE ci."Name" = %s
    LIMIT 1
""", (jaya_product,))

candidate = cur.fetchone()
if not candidate:
    print(f"\n❌ Jaya product not found in database")
    sys.exit(1)

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

# Test the matcher
matcher = AmazonStyleMatcher()

query_attrs = {
    'item_name': lotus_product,
    'brand': lotus_attrs['brand'],
    'size': lotus_attrs['size'],
    'size_normalized': lotus_attrs['size_normalized'],
    'size_unit': lotus_attrs['size_unit'],
    'pack_count': lotus_attrs['pack_count'],
    'category': 'Unknown',
    'name_tokens': lotus_attrs['name_tokens']
}

print(f"\n🧪 Testing matcher...")
best_match, score, breakdown = matcher.find_best_match(
    query_attributes=query_attrs,
    candidates=[candidate_dict],
    threshold=0.65
)

print(f"\n🎯 MATCHING RESULTS:")
print(f"   Score: {score:.4f}")
print(f"   Threshold: 0.65")
print(f"   Match: {'✅ YES' if best_match else '❌ NO'}")

print(f"\n📊 Score Breakdown:")
for key, val in breakdown.items():
    if isinstance(val, float):
        print(f"   {key:30} {val:.4f}")
    else:
        print(f"   {key:30} {val}")

if score < 0.65:
    print(f"\n💡 Score {score:.4f} is below threshold 0.65")
    print(f"   These IDENTICAL products aren't matching!")
    print(f"   → Need to lower threshold or improve scoring")
else:
    print(f"\n✅ Score {score:.4f} passes threshold")
    print(f"   But they created separate canonical IDs in actual ETL!")
    print(f"   → Need to investigate ETL processing order/logic")

cur.close()
conn.close()

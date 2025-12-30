
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DB_CONFIG

def verify():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=== Verification of Pricing Zones ===")
    
    # Check counts by PricingZoneId
    cur.execute('''
        SELECT "PricingZoneId", COUNT(*) as count 
        FROM purchase_analytics_gold 
        GROUP BY "PricingZoneId"
    ''')
    zones = cur.fetchall()
    print("\nCounts by PricingZoneId:")
    for z in zones:
        print(f"  {z['PricingZoneId']}: {z['count']}")
        
    # Check Lat/Long for scraped data
    cur.execute('''
        SELECT COUNT(*) as count
        FROM purchase_analytics_gold
        WHERE "PricingZoneId" IS NOT NULL 
          AND ("Latitude" IS NOT NULL OR "Longitude" IS NOT NULL)
    ''')
    invalid_coords = cur.fetchone()['count']
    print(f"\nRecords with PricingZoneId but passed Lat/Long (Should be 0): {invalid_coords}")
    
    # Check StoreName matches PricingZoneId
    cur.execute('''
        SELECT COUNT(*) as count
        FROM purchase_analytics_gold
        WHERE "PricingZoneId" IS NOT NULL 
          AND "StoreName" != "PricingZoneId"
    ''')
    mismatch_names = cur.fetchone()['count']
    print(f"Records where StoreName != PricingZoneId (Should be 0): {mismatch_names}")

    # Sample
    cur.execute('''
        SELECT "ItemName", "UnitPrice", "StoreName", "PricingZoneId", "CreatedAt"
        FROM purchase_analytics_gold
        WHERE "PricingZoneId" IS NOT NULL
        LIMIT 5
    ''')
    print("\nSample Records:")
    for r in cur.fetchall():
        print(r)

    conn.close()

if __name__ == "__main__":
    verify()

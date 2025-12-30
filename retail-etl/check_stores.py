
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DB_CONFIG

def check_stores():
    try:
        print(f"Connecting to database at {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Count total
        cur.execute('SELECT COUNT(*) as total FROM stores')
        total = cur.fetchone()['total']
        print(f"Total Stores: {total}")
        
        # Group by Zone
        cur.execute('SELECT "PricingZoneId", COUNT(*) as count FROM stores GROUP BY "PricingZoneId" ORDER BY count DESC')
        print("\nStores by Pricing Zone:")
        for row in cur.fetchall():
            print(f"  {row['PricingZoneId']}: {row['count']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking stores: {e}")

if __name__ == "__main__":
    check_stores()

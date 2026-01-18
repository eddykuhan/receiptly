import psycopg2
from config.settings import DB_CONFIG
import time

while True:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get counts
        cur.execute("SELECT COUNT(*) FROM canonical_items")
        canonical = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM purchase_analytics_gold")
        gold = cur.fetchone()[0]
        
        # Get cross-store matches
        cur.execute("""
            SELECT COUNT(DISTINCT "CanonicalItemId")
            FROM purchase_analytics_gold
            GROUP BY "CanonicalItemId"
            HAVING COUNT(DISTINCT "Source") > 1
        """)
        cross_store = len(cur.fetchall())
        
        match_rate = (cross_store / canonical * 100) if canonical > 0 else 0
        
        print(f"\r[{time.strftime('%H:%M:%S')}] Canonical: {canonical:,} | Gold: {gold:,} | Cross-store: {cross_store} ({match_rate:.1f}%)   ", end='', flush=True)
        
        cur.close()
        conn.close()
        
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
        break
    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(5)

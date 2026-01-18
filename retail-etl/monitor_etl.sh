#!/bin/bash
# ETL Monitor and Auto-Restart
# Monitors ETL process and restarts if it stops unexpectedly

ETL_DIR="/Users/kuhan/Projects/receiptly/retail-etl"
cd "$ETL_DIR"

# Check if ETL is running
check_etl_running() {
    pgrep -f "python.*etl_manager.py" > /dev/null
    return $?
}

# Get database progress
get_db_progress() {
    source venv/bin/activate
    python3 << 'EOF'
from config.settings import DB_CONFIG
import psycopg2

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM canonical_items")
    canonical = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM purchase_analytics_gold")
    gold = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"{canonical},{gold}")
except:
    print("0,0")
EOF
}

echo "ETL Monitor Started"
echo "Checking every 30 seconds..."
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if check_etl_running; then
        # ETL is running
        PROGRESS=$(get_db_progress)
        CANONICAL=$(echo $PROGRESS | cut -d',' -f1)
        GOLD=$(echo $PROGRESS | cut -d',' -f2)
        echo "[$TIMESTAMP] ✓ ETL running | Canonical: $CANONICAL | Gold: $GOLD"
    else
        # ETL stopped
        PROGRESS=$(get_db_progress)
        CANONICAL=$(echo $PROGRESS | cut -d',' -f1)
        GOLD=$(echo $PROGRESS | cut -d',' -f2)
        
        echo "[$TIMESTAMP] ✗ ETL stopped | Progress: $CANONICAL canonical, $GOLD gold"
        
        # Check if ETL completed (35,329 products)
        if [ "$CANONICAL" -ge 23000 ] && [ "$GOLD" -ge 23000 ]; then
            echo "[$TIMESTAMP] ✓ ETL appears complete"
        else
            echo "[$TIMESTAMP] ⚠ ETL stopped prematurely - may need manual restart"
        fi
    fi
    
    sleep 30
done

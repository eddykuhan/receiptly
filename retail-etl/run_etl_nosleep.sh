#!/bin/bash
# ETL Runner with Sleep Prevention
# Prevents MacBook from sleeping during ETL execution

ETL_DIR="/Users/kuhan/Projects/receiptly/retail-etl"
cd "$ETL_DIR"

# Activate virtual environment
source venv/bin/activate

# Generate log filename with timestamp
LOG_FILE="logs/etl_$(date +%Y%m%d_%H%M%S).log"

echo "Starting ETL with sleep prevention..."
echo "Log file: $LOG_FILE"
echo "Process will continue even if terminal is closed"
echo ""

# Use caffeinate to prevent system sleep
# -i: Prevent idle sleep
# -s: Prevent system sleep (even when display sleeps)
# -w: Wait for specified process to complete
caffeinate -is nohup python etl_manager.py > "$LOG_FILE" 2>&1 &

ETL_PID=$!
echo "ETL started with PID: $ETL_PID"
echo "Monitor with: tail -f $LOG_FILE"
echo ""
echo "To stop: kill $ETL_PID"
echo "Check status: ps -p $ETL_PID"

#!/bin/bash
# Protect currently running ETL from sleep

ETL_PID=$(pgrep -f "python.*etl_manager.py")

if [ -z "$ETL_PID" ]; then
    echo "No ETL process found running"
    exit 1
fi

echo "Found ETL process: PID $ETL_PID"
echo "Starting caffeinate to prevent sleep..."

# Run caffeinate in background attached to ETL process
caffeinate -w $ETL_PID &
CAFFEINATE_PID=$!

echo "✓ caffeinate started (PID: $CAFFEINATE_PID)"
echo "  - System will not sleep while ETL (PID: $ETL_PID) is running"
echo "  - caffeinate will exit automatically when ETL completes"
echo ""
echo "To manually stop caffeinate: kill $CAFFEINATE_PID"

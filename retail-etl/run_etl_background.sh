#!/bin/bash
# Run ETL in background with logging

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Create logs directory
mkdir -p logs

# Run ETL with output to log file
echo "Starting ETL at $(date)" >> logs/etl_background.log
python etl_manager.py >> logs/etl_background.log 2>&1

# Log completion
echo "ETL completed at $(date)" >> logs/etl_background.log

# Optional: Send notification (macOS)
osascript -e 'display notification "ETL pipeline completed" with title "Receiptly ETL"'

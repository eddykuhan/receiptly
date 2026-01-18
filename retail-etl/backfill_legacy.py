"""
Legacy Backfill Script - Vector-enabled data migration.

Migrates data from 'items' and 'receipts' tables to 'purchase_analytics_gold'
using the Canonicalizer service for vector similarity matching.
"""
import sys
import os
import logging
from typing import List, Dict
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl_transformers.canonicalizer import Canonicalizer
from loaders.postgres_loader import PostgresLoader
from config.settings import DB_CONFIG, LOG_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LegacyBackfill")

class LegacyBackfiller:
    def __init__(self):
        self.canonicalizer = Canonicalizer(DB_CONFIG)
        self.loader = PostgresLoader(DB_CONFIG)
        self.conn = None
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def fetch_legacy_items(self) -> List[Dict]:
        """Fetch all items joined with receipt data for context."""
        logger.info("Fetching legacy items from database...")
        self.connect()
        query = """
            SELECT 
                i."Id" as item_id,
                i."Name" as item_name,
                i."Category" as item_category,
                i."UnitPrice" as unit_price,
                i."Price" as price,
                i."Quantity" as quantity,
                r."Id" as receipt_id,
                r."UserId" as user_id,
                r."StoreName" as store_name,
                r."StoreAddress" as store_address,
                r."Latitude" as latitude,
                r."Longitude" as longitude,
                r."PurchaseDate" as purchase_date,
                r."ReceiptType" as receipt_type,
                r."TransactionId" as transaction_id,
                r."Status" as receipt_status
            FROM items i
            JOIN receipts r ON i."ReceiptId" = r."Id"
            WHERE r."Id" IS NOT NULL
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()

    def run(self, batch_size: int = 100):
        items = self.fetch_legacy_items()
        total = len(items)
        logger.info(f"Starting backfill for {total} items.")
        
        batch = []
        processed = 0
        
        for item in items:
            try:
                # Canonicalize using Vector/Exact/Alias
                canon_result = self.canonicalizer.canonicalize(
                    item['item_name'],
                    item['item_category'] or 'Unknown'
                )
                
                # Format for gold layer
                price = item['unit_price'] or item['price'] or 0.0
                
                gold_record = {
                    'item_id': str(item['item_id']),
                    'receipt_id': str(item['receipt_id']),
                    'user_id': item['user_id'],
                    'item_name': item['item_name'],
                    'canonical_item_id': canon_result['canonical_item_id'],
                    'category': item['item_category'] or 'Unknown',
                    'unit_price': float(price),
                    'total_price': float(price * (item['quantity'] or 1)),
                    'quantity': item['quantity'] or 1,
                    'purchase_date': item['purchase_date'] or datetime.now(),
                    'store_name': item['store_name'],
                    'store_address': item['store_address'],
                    'latitude': item['latitude'],
                    'longitude': item['longitude'],
                    'receipt_type': item['receipt_type'],
                    'transaction_id': item['transaction_id'],
                    'receipt_status': str(item['receipt_status']),
                    'source': 'UserReceipt', # Explicit source for backfilled data
                    'pricing_zone_id': None  # Legacy data uses GPS coords, not zones
                }
                
                batch.append(gold_record)
                processed += 1
                
                if len(batch) >= batch_size:
                    self.loader.upsert_gold_price(batch)
                    logger.info(f"Progress: {processed}/{total} items backfilled.")
                    batch = []
                    
            except Exception as e:
                logger.error(f"Error processing item {item.get('item_name')}: {e}")

        # Final batch
        if batch:
            self.loader.upsert_gold_price(batch)
            
        logger.info("Backfill completed successfully.")
        self.canonicalizer.close()
        self.loader.close()
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    backfiller = LegacyBackfiller()
    backfiller.run()

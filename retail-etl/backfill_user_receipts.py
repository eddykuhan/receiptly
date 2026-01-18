"""
Backfill Canonical IDs for User Receipt Items

This script processes items from user-uploaded receipts that are missing canonical IDs.
It supports two modes:

MODE 1 (Default): Update existing purchase_analytics_gold records missing canonical IDs
MODE 2 (--from-source): Backfill from receipts + items tables (for truncated gold table)

It uses the same canonicalization logic as the ETL pipeline to:
1. Find existing canonical items if they match
2. Create new canonical items if no match exists
3. Update/insert into purchase_analytics_gold with the canonical_item_id

Usage:
    python backfill_user_receipts.py [--batch-size 100] [--dry-run] [--from-source]
"""
import sys
import os
import logging
import argparse
from typing import List, Dict
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl_transformers.canonicalizer import Canonicalizer
from config.settings import DB_CONFIG, LOG_DIR

# Configure logging
log_file = os.path.join(LOG_DIR, f'backfill_receipts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ReceiptBackfill")


class UserReceiptBackfiller:
    """Backfills canonical IDs for user receipt items."""
    
    def __init__(self, dry_run: bool = False, from_source: bool = False):
        """
        Initialize the backfiller.
        
        Args:
            dry_run: If True, process items but don't update database
            from_source: If True, backfill from receipts + items tables instead of gold table
        """
        self.canonicalizer = Canonicalizer(DB_CONFIG)
        self.conn = None
        self.dry_run = dry_run
        self.from_source = from_source
        self.stats = {
            'total': 0,
            'existing_match': 0,
            'new_canonical': 0,
            'updated': 0,
            'inserted': 0,
            'errors': 0,
            'skipped': 0
        }
        
    def connect(self):
        """Establish or refresh database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.canonicalizer.connect()
            
    def close(self):
        """Close database connections."""
        self.canonicalizer.close()
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def fetch_items_without_canonical_ids(self) -> List[Dict]:
        """
        Fetch all user receipt items that don't have canonical IDs.
        
        Returns:
            List of items with their details
        """
        logger.info("Fetching user receipt items without canonical IDs...")
        self.connect()
        
        query = """
            SELECT 
                "Id" as record_id,
                "ItemName" as item_name,
                "Category" as category,
                "StoreName" as store_name,
                "UnitPrice" as unit_price,
                "PurchaseDate" as purchase_date,
                "Source" as source
            FROM purchase_analytics_gold
            WHERE ("Source" = 'UserReceipt' OR "ReceiptId" IS NOT NULL)
              AND "CanonicalItemId" IS NULL
            ORDER BY "PurchaseDate" DESC
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            items = cur.fetchall()
            
        logger.info(f"Found {len(items)} items without canonical IDs")
        return items
    
    def fetch_items_from_source_tables(self) -> List[Dict]:
        """
        Fetch all items from the original receipts + items tables.
        Used when gold table is truncated and needs full backfill.
        
        Returns:
            List of items with their details formatted for processing
        """
        logger.info("Fetching items from receipts + items source tables...")
        self.connect()
        
        query = """
            SELECT 
                i."Id" as item_id,
                i."Name" as item_name,
                i."Category" as category,
                i."UnitPrice" as unit_price,
                i."Price" as price,
                i."Quantity" as quantity,
                r."Id" as receipt_id,
                r."UserId" as user_id,
                r."StoreName" as store_name,
                r."StoreAddress" as store_address,
                r."StorePhoneNumber" as store_phone,
                r."Latitude" as latitude,
                r."Longitude" as longitude,
                r."LocationConfidence" as location_confidence,
                r."PurchaseDate" as purchase_date,
                r."ReceiptType" as receipt_type,
                r."TransactionId" as transaction_id,
                r."PaymentMethod" as payment_method,
                r."Status" as receipt_status
            FROM items i
            INNER JOIN receipts r ON i."ReceiptId" = r."Id"
            WHERE r."Id" IS NOT NULL
            ORDER BY r."PurchaseDate" DESC
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            items = cur.fetchall()
            
        logger.info(f"Found {len(items)} items in source tables")
        return items
    
    def get_canonical_name(self, canonical_id: str) -> str:
        """
        Get the canonical item name for a given ID.
        
        Args:
            canonical_id: The canonical item ID
            
        Returns:
            Canonical item name
        """
        self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute('''
                SELECT "Name"
                FROM canonical_items
                WHERE "Id" = %s
            ''', (canonical_id,))
            
            result = cur.fetchone()
            if result:
                return result[0]
        
        return "Unknown"
    
    def check_existing_canonical_item(self, item_name: str, store_name: str) -> str:
        """
        Check if a canonical item already exists in canonical_items table.
        
        Uses the canonical_items table directly for better accuracy:
        1. First checks for exact name match
        2. Then checks using name tokens for fuzzy matching
        3. Filters by store to ensure relevance
        
        Args:
            item_name: The item name
            store_name: The store name
            
        Returns:
            Canonical item ID if found, None otherwise
        """
        self.connect()
        
        with self.conn.cursor() as cur:
            # First try: exact match on canonical name (with full normalization including translation)
            normalized_name = self.canonicalizer.normalize_text(item_name)
            cur.execute('''
                SELECT "Id"
                FROM canonical_items
                WHERE LOWER("Name") = %s
                LIMIT 1
            ''', (normalized_name,))
            
            result = cur.fetchone()
            if result:
                return str(result[0])
            
            # Second try: token-based matching using NameTokens column
            # Extract significant tokens from the item name (words >= 3 chars)
            tokens = [t.lower() for t in item_name.split() if len(t) >= 3]
            
            if tokens:
                # Check if any canonical item has ALL these tokens
                cur.execute('''
                    SELECT "Id", "Name", "NameTokens"
                    FROM canonical_items
                    WHERE "NameTokens" @> %s::text[]
                    ORDER BY array_length("NameTokens", 1) ASC
                    LIMIT 1
                ''', (tokens,))
                
                result = cur.fetchone()
                if result:
                    return str(result[0])
            
            # Third try: check if this exact item+store combo exists in gold table
            # This catches cases where scraped data already has this combination
            cur.execute('''
                SELECT DISTINCT "CanonicalItemId"
                FROM purchase_analytics_gold
                WHERE LOWER(TRIM("ItemName")) = %s
                  AND LOWER(TRIM("StoreName")) = %s
                  AND "CanonicalItemId" IS NOT NULL
                  AND "Source" != 'UserReceipt'
                LIMIT 1
            ''', (normalized_name, store_name.lower().strip()))
            
            result = cur.fetchone()
            if result:
                return str(result[0])
                
        return None
    
    def process_batch(self, items: List[Dict], batch_size: int = 25):
        """
        Process a batch of items using the canonicalizer.
        
        Args:
            items: List of item dictionaries
            batch_size: Number of items to process per batch for canonicalization
        """
        total = len(items)
        logger.info(f"Processing {total} items in batches of {batch_size}...")
        
        updates = []
        inserts = []
        
        for i in range(0, total, batch_size):
            batch = items[i:i + batch_size]
            
            for item in batch:
                try:
                    item_name = item['item_name']
                    category = item['category'] or 'Unknown'
                    store_name = item['store_name']
                    record_id = item.get('record_id')  # May be None for source table mode
                    
                    # Check if canonical item already exists from scraped data
                    existing_canonical_id = self.check_existing_canonical_item(item_name, store_name)
                    
                    if existing_canonical_id:
                        canonical_id = existing_canonical_id
                        canonical_name = self.get_canonical_name(canonical_id)
                        self.stats['existing_match'] += 1
                        match_method = 'existing_scraped_data'
                        logger.info(f"  ✓ '{item_name}' → '{canonical_name}' (ID: {canonical_id})")
                    else:
                        # Use canonicalizer to find/create canonical item
                        # This will use the full Amazon-style matching pipeline
                        canonical_result = self.canonicalizer.canonicalize(
                            item_name=item_name,
                            category=category
                        )
                        
                        canonical_id = canonical_result['canonical_item_id']
                        canonical_name = self.get_canonical_name(canonical_id)
                        match_method = canonical_result.get('match_method', 'new_canonical')
                        
                        if match_method == 'exact_match' or match_method.startswith('vector'):
                            self.stats['existing_match'] += 1
                        else:
                            self.stats['new_canonical'] += 1
                        
                        logger.info(f"  ✓ '{item_name}' → '{canonical_name}' (ID: {canonical_id}, method: {match_method})")
                    
                    # Prepare update or insert depending on mode
                    if self.from_source:
                        # Source table mode: prepare for insert into gold table
                        inserts.append({
                            'item_id': str(item.get('item_id')),
                            'receipt_id': str(item.get('receipt_id')),
                            'user_id': item.get('user_id'),
                            'item_name': item_name,
                            'canonical_id': str(canonical_id),
                            'category': category,
                            'unit_price': float(item.get('unit_price') or item.get('price', 0)),
                            'total_price': float((item.get('unit_price') or item.get('price', 0)) * item.get('quantity', 1)),
                            'quantity': item.get('quantity', 1),
                            'purchase_date': item.get('purchase_date'),
                            'store_name': store_name,
                            'store_address': item.get('store_address'),
                            'store_phone': item.get('store_phone'),
                            'latitude': item.get('latitude'),
                            'longitude': item.get('longitude'),
                            'location_confidence': item.get('location_confidence', 1.0),
                            'receipt_type': item.get('receipt_type'),
                            'transaction_id': item.get('transaction_id'),
                            'payment_method': item.get('payment_method'),
                            'receipt_status': str(item.get('receipt_status', 'Completed'))
                        })
                    else:
                        # Gold table mode: prepare for update
                        updates.append({
                            'record_id': str(record_id),
                            'canonical_id': str(canonical_id),
                            'match_method': match_method
                        })
                    
                    self.stats['total'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing item '{item.get('item_name')}': {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Commit canonical items created in this batch
            try:
                self.canonicalizer.conn.commit()
            except Exception as e:
                logger.error(f"Error committing canonical items: {e}")
                self.canonicalizer.connect()
            
            # Progress update
            processed = min(i + batch_size, total)
            logger.info(f"Progress: {processed}/{total} items processed "
                       f"(existing: {self.stats['existing_match']}, "
                       f"new: {self.stats['new_canonical']}, "
                       f"errors: {self.stats['errors']})")
        
        # Update or insert into purchase_analytics_gold
        if self.from_source:
            if inserts and not self.dry_run:
                self._bulk_insert_gold_records(inserts)
            elif self.dry_run:
                logger.info(f"DRY RUN: Would insert {len(inserts)} records into gold table")
        else:
            if updates and not self.dry_run:
                self._bulk_update_canonical_ids(updates)
            elif self.dry_run:
                logger.info(f"DRY RUN: Would update {len(updates)} records")
        
        return updates if not self.from_source else inserts
    
    def _bulk_update_canonical_ids(self, updates: List[Dict]):
        """
        Bulk update purchase_analytics_gold with canonical IDs.
        
        Args:
            updates: List of dicts with record_id and canonical_id
        """
        if not updates:
            return
        
        logger.info(f"Updating {len(updates)} records with canonical IDs...")
        self.connect()
        
        try:
            with self.conn.cursor() as cur:
                # Use CASE statement for efficient bulk update
                update_query = '''
                    UPDATE purchase_analytics_gold
                    SET "CanonicalItemId" = updates.canonical_id::uuid
                    FROM (VALUES %s) AS updates(record_id, canonical_id)
                    WHERE "Id"::text = updates.record_id
                '''
                
                # Prepare values
                values = [(u['record_id'], u['canonical_id']) for u in updates]
                
                # Execute bulk update
                execute_values(cur, update_query, values, page_size=500)
                
                self.conn.commit()
                self.stats['updated'] = len(updates)
                logger.info(f"✓ Successfully updated {len(updates)} records")
                
        except Exception as e:
            logger.error(f"Error during bulk update: {e}")
            self.conn.rollback()
            raise
    
    def _bulk_insert_gold_records(self, records: List[Dict]):
        """
        Bulk insert records into purchase_analytics_gold from source tables.
        
        Args:
            records: List of dicts with all gold table fields
        """
        if not records:
            return
        
        logger.info(f"Inserting {len(records)} records into purchase_analytics_gold...")
        self.connect()
        
        try:
            with self.conn.cursor() as cur:
                insert_query = '''
                    INSERT INTO purchase_analytics_gold (
                        "Id", "ItemId", "ReceiptId", "UserId", "Source",
                        "ItemName", "CanonicalItemId", "UnitPrice", "TotalPrice", 
                        "Quantity", "Category", "PurchaseDate",
                        "StoreName", "StoreAddress", "StorePhoneNumber",
                        "Latitude", "Longitude", "LocationConfidence",
                        "ReceiptType", "TransactionId", "PaymentMethod", 
                        "ReceiptStatus", "CreatedAt"
                    ) VALUES %s
                    ON CONFLICT ("Id") DO UPDATE SET
                        "CanonicalItemId" = EXCLUDED."CanonicalItemId"
                '''
                
                # Prepare values
                values = []
                for r in records:
                    values.append((
                        str(uuid.uuid4()),                      # Id
                        r['item_id'],                           # ItemId
                        r['receipt_id'],                        # ReceiptId
                        r['user_id'],                           # UserId
                        'UserReceipt',                          # Source
                        r['item_name'],                         # ItemName
                        r['canonical_id'],                      # CanonicalItemId
                        r['unit_price'],                        # UnitPrice
                        r['total_price'],                       # TotalPrice
                        r['quantity'],                          # Quantity
                        r['category'],                          # Category
                        r['purchase_date'] or datetime.now(),   # PurchaseDate
                        r['store_name'],                        # StoreName
                        r['store_address'] or '',               # StoreAddress
                        r.get('store_phone'),                   # StorePhoneNumber
                        r.get('latitude'),                      # Latitude
                        r.get('longitude'),                     # Longitude
                        r.get('location_confidence', 1.0),      # LocationConfidence
                        r.get('receipt_type'),                  # ReceiptType
                        r.get('transaction_id'),                # TransactionId
                        r.get('payment_method'),                # PaymentMethod
                        r.get('receipt_status', 'Completed'),   # ReceiptStatus
                        datetime.now()                          # CreatedAt
                    ))
                
                # Execute bulk insert
                execute_values(cur, insert_query, values, page_size=500)
                
                self.conn.commit()
                self.stats['inserted'] = len(records)
                logger.info(f"✓ Successfully inserted {len(records)} records")
                
        except Exception as e:
            logger.error(f"Error during bulk insert: {e}")
            self.conn.rollback()
            raise
    
    def run(self, batch_size: int = 25):
        """
        Run the backfill process.
        
        Args:
            batch_size: Number of items to process per canonicalization batch
        """
        logger.info("=" * 70)
        logger.info(f"Starting User Receipt Backfill - {datetime.now().isoformat()}")
        logger.info(f"Mode: {'FROM SOURCE TABLES' if self.from_source else 'UPDATE GOLD TABLE'}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info("=" * 70)
        
        try:
            # Fetch items based on mode
            if self.from_source:
                items = self.fetch_items_from_source_tables()
            else:
                items = self.fetch_items_without_canonical_ids()
            
            if not items:
                if self.from_source:
                    logger.info("No items found in receipts + items tables.")
                else:
                    logger.info("No items to backfill. All user receipts already have canonical IDs.")
                return
            
            # Process items
            results = self.process_batch(items, batch_size)
            
            # Print summary
            logger.info("=" * 70)
            logger.info("Backfill Summary:")
            logger.info(f"  Total items processed: {self.stats['total']}")
            logger.info(f"  Matched to existing canonical items: {self.stats['existing_match']}")
            logger.info(f"  New canonical items created: {self.stats['new_canonical']}")
            if self.from_source:
                logger.info(f"  Records inserted: {self.stats['inserted']}")
            else:
                logger.info(f"  Records updated: {self.stats['updated']}")
            logger.info(f"  Errors: {self.stats['errors']}")
            logger.info("=" * 70)
            
            if self.dry_run:
                logger.info("DRY RUN COMPLETE - No database changes were made")
            
        except Exception as e:
            logger.error(f"Fatal error during backfill: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Backfill canonical IDs for user receipt items'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Number of items to process per batch (default: 25)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process items but do not update database'
    )
    parser.add_argument(
        '--from-source',
        action='store_true',
        help='Backfill from receipts + items tables instead of updating gold table (use after truncating gold table)'
    )
    
    args = parser.parse_args()
    
    backfiller = UserReceiptBackfiller(dry_run=args.dry_run, from_source=args.from_source)
    backfiller.run(batch_size=args.batch_size)


if __name__ == "__main__":
    main()

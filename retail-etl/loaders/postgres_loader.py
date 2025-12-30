"""
PostgreSQL Loader for Retail ETL.

Handles loading transformed data into the purchase_analytics_gold table.
"""
import uuid
from typing import List, Dict
import logging
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

logger = logging.getLogger(__name__)

class PostgresLoader:
    """Loads product data into PostgreSQL."""
    
    def __init__(self, db_config: Dict):
        """Initialize loader with DB config."""
        self.db_config = db_config
        self.conn = None
        self.connect()

    def connect(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            try:
                self.conn = psycopg2.connect(**self.db_config)
                logger.info("Connected to database")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def get_stats(self) -> Dict:
        """Get current database statistics."""
        if not self.conn or self.conn.closed:
            self.connect()
            
        stats = {}
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # Total records
            cur.execute('SELECT COUNT(*) as count FROM purchase_analytics_gold')
            stats['total_records'] = cur.fetchone()['count']
            
            # Unique items
            cur.execute('SELECT COUNT(DISTINCT "CanonicalItemId") as count FROM purchase_analytics_gold')
            stats['unique_items'] = cur.fetchone()['count']
            
            # Unique stores
            cur.execute('SELECT COUNT(DISTINCT "StoreName") as count FROM purchase_analytics_gold')
            stats['unique_stores'] = cur.fetchone()['count']
            
            # With location
            cur.execute('SELECT COUNT(*) as count FROM purchase_analytics_gold WHERE "Latitude" IS NOT NULL')
            stats['with_location'] = cur.fetchone()['count']
            
        return stats

    def upsert_gold_price(self, records: List[Dict]) -> Dict:
        """
        Insert or update price records in purchase_analytics_gold.
        """
        if not records:
            return {'inserted': 0, 'skipped': 0, 'total': 0}
            
        if not self.conn or self.conn.closed:
            self.connect()
            
        inserted = 0
        skipped = 0
        
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            for record in records:
                try:
                    canonical_id = record.get('canonical_item_id')
                    store_name = record.get('store_name')
                    price = record.get('unit_price')
                    
                    if not canonical_id or not store_name or price is None:
                        continue

                    # Check latest record
                    cur.execute(
                        '''
                        SELECT "Id", "UnitPrice", "PurchaseDate"
                        FROM purchase_analytics_gold 
                        WHERE "CanonicalItemId" = %s AND "StoreName" = %s 
                        ORDER BY "PurchaseDate" DESC 
                        LIMIT 1
                        ''',
                        (canonical_id, store_name)
                    )
                    latest = cur.fetchone()
                    
                    if latest and abs(float(latest['UnitPrice']) - float(price)) < 0.01:
                        # Price same, update PurchaseDate
                        cur.execute(
                            '''
                            UPDATE purchase_analytics_gold 
                            SET "PurchaseDate" = %s 
                            WHERE "Id" = %s
                            ''',
                            (datetime.now(), latest['Id'])
                        )
                        skipped += 1
                    else:
                        # Insert new record
                        self._insert_record(cur, record)
                        inserted += 1
                        
                except Exception as e:
                    logger.error(f"Error loading record {record.get('item_name')}: {e}")
                    self.conn.rollback()
                    continue 
            
            self.conn.commit()
            
        return {'inserted': inserted, 'skipped': skipped, 'total': len(records)}

    def _insert_record(self, cur, record: Dict):
        """Insert a single record into purchase_analytics_gold."""
        item_id = str(uuid.uuid4())
        
        insert_query = '''
        INSERT INTO purchase_analytics_gold (
            "Id", 
            "ItemId", 
            "Source", 
            "ItemName", 
            "CanonicalItemId", 
            "UnitPrice", 
            "TotalPrice", 
            "Quantity", 
            "Category", 
            "PurchaseDate", 
            "StoreName", 
            "StoreAddress", 
            "Latitude", 
            "Longitude", 
            "LocationConfidence",
            "PricingZoneId",
            "CreatedAt"
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        '''
        
        cur.execute(insert_query, (
            str(uuid.uuid4()),      # Id
            item_id,                # ItemId
            record.get('source', 'ETL'),
            record.get('item_name'),
            record.get('canonical_item_id'),
            record.get('unit_price'),
            record.get('unit_price'), 
            1,                        
            record.get('category'),
            datetime.now(),           # PurchaseDate
            record.get('store_name'), # Takes PricingZoneId for scraped data
            record.get('store_address'),
            record.get('latitude'),
            record.get('longitude'),
            1.0,                      
            record.get('pricing_zone_id'), # New column
            datetime.now()            # CreatedAt
        ))

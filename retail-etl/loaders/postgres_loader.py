"""
PostgreSQL Loader for Retail ETL.

Handles loading transformed data into the purchase_analytics_gold table.
"""
import uuid
from typing import List, Dict
import logging
import psycopg2
from psycopg2.extras import DictCursor, execute_values
from datetime import datetime

logger = logging.getLogger(__name__)

class PostgresLoader:
    """Loads product data into PostgreSQL."""
    
    def __init__(self, db_config: Dict):
        """Initialize loader with DB config."""
        self.db_config = db_config
        self.conn = None
        self.store_cache = {}  # Cache store details to avoid repeated queries
        self.connect()

    def connect(self):
        """Establish or refresh database connection."""
        is_broken = False
        if self.conn:
            try:
                # Execution of a simple query to check if connection is alive
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                is_broken = True

        if not self.conn or self.conn.closed or is_broken:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            try:
                # Add connection timeout settings
                db_config_with_timeout = {
                    **self.db_config,
                    'connect_timeout': 30,  # 30 second connection timeout
                    'options': '-c statement_timeout=300000'  # 5 minute query timeout
                }
                self.conn = psycopg2.connect(**db_config_with_timeout)
                self.conn.set_session(autocommit=False)  # Explicit transaction control
                logger.info("Connected to database with timeout settings")
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
    
    def get_existing_items(self, records: List[Dict]) -> Dict[str, str]:
        """
        Check which items already exist in gold_price table and return their canonical IDs.
        Uses item_name + store_name as unique key.
        
        Args:
            records: List of dicts with 'item_name' and 'store_name'
            
        Returns:
            Dict mapping "item_name|store_name" to canonical_item_id
        """
        if not records:
            return {}
        
        if not self.conn or self.conn.closed:
            self.connect()
        
        # Build unique keys for lookup
        lookup_keys = []
        for record in records:
            item_name = record.get('item_name', '').strip()
            store_name = record.get('store_name', '').strip()
            if item_name and store_name:
                lookup_keys.append((item_name, store_name))
        
        if not lookup_keys:
            return {}
        
        existing_map = {}
        
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Process in batches to avoid SQL string size limits
                batch_size = 1000
                for batch_start in range(0, len(lookup_keys), batch_size):
                    batch = lookup_keys[batch_start:batch_start + batch_size]
                    
                    # Create VALUES clause for this batch
                    query = '''
                        SELECT DISTINCT ON ("ItemName", "StoreName")
                            "ItemName", "StoreName", "CanonicalItemId"
                        FROM purchase_analytics_gold
                        WHERE ("ItemName", "StoreName") IN (VALUES %s)
                        AND "CanonicalItemId" IS NOT NULL
                    '''
                    
                    execute_values(cur, query, batch, template='(%s, %s)')
                    results = cur.fetchall()
                    
                    for row in results:
                        key = f"{row['ItemName']}|{row['StoreName']}"
                        existing_map[key] = row['CanonicalItemId']
                
                logger.info(f"Found {len(existing_map)} items already in database")
                
        except Exception as e:
            logger.error(f"Error checking existing items: {e}")
            self.conn.rollback()
        
        return existing_map

    def _get_store_details(self, store_name: str) -> Dict:
        """Get store address and coordinates from the stores table."""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT "Address", "Latitude", "Longitude"
                    FROM stores
                    WHERE "RetailChain" = %s OR "Name" ILIKE %s
                    LIMIT 1
                ''', (store_name, f"%{store_name}%"))
                result = cur.fetchone()
                if result:
                    return {
                        'address': result['Address'],
                        'latitude': result['Latitude'],
                        'longitude': result['Longitude']
                    }
        except Exception as e:
            logger.warning(f"Error fetching store details for {store_name}: {e}")
        return {'address': None, 'latitude': None, 'longitude': None}

    def upsert_gold_price(self, records: List[Dict], batch_size: int = 100) -> Dict:
        """
        Insert or update price records in purchase_analytics_gold in batches.
        Optimized with bulk operations.
        """
        if not records:
            return {'inserted': 0, 'skipped': 0, 'total': 0}
        
        # Health check before starting batch operations
        logger.info("Performing connection health check before load...")
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            logger.info("✓ Connection healthy")
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            self.connect()  # Force reconnect
            
        inserted = 0
        skipped = 0
        total = len(records)
        
        # Enrich records with store details if missing
        store_cache = {}
        for record in records:
            store_name = record.get('store_name')
            if store_name and not store_cache.get(store_name):
                store_cache[store_name] = self._get_store_details(store_name)
            
            # Fill in missing store address/coords from cache
            if store_name and store_cache[store_name]:
                store_info = store_cache[store_name]
                if not record.get('store_address') or record.get('store_address') == 'Malaysia':
                    record['store_address'] = store_info['address']
                if record.get('latitude') is None:
                    record['latitude'] = store_info['latitude']
                if record.get('longitude') is None:
                    record['longitude'] = store_info['longitude']
        
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            self.connect() # Ensure connection is alive for this batch
            
            try:
                with self.conn.cursor(cursor_factory=DictCursor) as cur:
                    # Step 1: Bulk fetch latest prices for this batch
                    canonical_store_pairs = [
                        (r.get('canonical_item_id'), r.get('store_name'))
                        for r in batch
                        if r.get('canonical_item_id') and r.get('store_name')
                    ]
                    
                    if not canonical_store_pairs:
                        continue
                    
                    # Create temporary table for lookup
                    cur.execute('''
                        CREATE TEMP TABLE IF NOT EXISTS batch_lookup (
                            canonical_id UUID,
                            store_name TEXT,
                            PRIMARY KEY (canonical_id, store_name)
                        ) ON COMMIT DROP
                    ''')
                    
                    # Insert batch items to lookup
                    from psycopg2.extras import execute_values
                    execute_values(
                        cur,
                        'INSERT INTO batch_lookup VALUES %s ON CONFLICT DO NOTHING',
                        canonical_store_pairs
                    )
                    
                    # Bulk fetch latest prices
                    cur.execute('''
                        SELECT DISTINCT ON (g."CanonicalItemId", g."StoreName")
                            g."Id", g."CanonicalItemId", g."StoreName", 
                            g."UnitPrice", g."PurchaseDate"
                        FROM purchase_analytics_gold g
                        INNER JOIN batch_lookup b 
                            ON g."CanonicalItemId" = b.canonical_id 
                            AND g."StoreName" = b.store_name
                        ORDER BY g."CanonicalItemId", g."StoreName", g."PurchaseDate" DESC
                    ''')
                    
                    latest_prices = {
                        (row['CanonicalItemId'], row['StoreName']): row
                        for row in cur.fetchall()
                    }
                    
                    # Step 2: Process records with cached lookups
                    records_to_insert = []
                    records_to_update = []
                    
                    for record in batch:
                        canonical_id = record.get('canonical_item_id')
                        store_name = record.get('store_name')
                        price = record.get('unit_price')
                        
                        if not canonical_id or not store_name or price is None:
                            continue
                        
                        latest = latest_prices.get((canonical_id, store_name))
                        
                        if latest and abs(float(latest['UnitPrice']) - float(price)) < 0.01:
                            # Same price, mark for date update
                            records_to_update.append(latest['Id'])
                            skipped += 1
                        else:
                            # New price, mark for insert
                            records_to_insert.append(record)
                            inserted += 1
                    
                    # Step 3: Bulk update dates
                    if records_to_update:
                        # Convert UUIDs to strings for ANY() operator
                        id_list = [str(id_val) for id_val in records_to_update]
                        cur.execute('''
                            UPDATE purchase_analytics_gold 
                            SET "PurchaseDate" = %s 
                            WHERE "Id" = ANY(%s::uuid[])
                        ''', (datetime.now(), id_list))
                    
                    # Step 4: Bulk insert new records using execute_values (MUCH faster)
                    if records_to_insert:
                        # Verify all canonical_item_ids exist before inserting
                        canonical_ids = [r.get('canonical_item_id') for r in records_to_insert if r.get('canonical_item_id')]
                        if canonical_ids:
                            cur.execute('''
                                SELECT "Id" FROM canonical_items WHERE "Id" = ANY(%s::uuid[])
                            ''', ([str(id) for id in canonical_ids],))
                            existing_ids = {row[0] for row in cur.fetchall()}
                            missing_ids = set(canonical_ids) - existing_ids
                            if missing_ids:
                                logger.error(f"Missing canonical_item_ids: {missing_ids}")
                                raise ValueError(f"{len(missing_ids)} canonical items not found in database. First missing: {list(missing_ids)[0]}")
                        
                        self._bulk_insert_records(cur, records_to_insert)
                    
                    self.conn.commit()
                    
                    # Keep connection alive during processing
                    if i % 5000 == 0:  # Every 5 batches, refresh connection
                        self.connect()
                        cur = self.conn.cursor(cursor_factory=DictCursor)
                    
                    logger.info(f"Batch Progress: {min(i + batch_size, total)}/{total} processed (inserted: {inserted}, updated: {skipped})...")
                    
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logger.error(f"Database connection lost during batch: {e}. Reconnecting...")
                self.conn.rollback()
                self.conn = None # Force reconnect on next iteration
                self.connect()
                cur = self.conn.cursor(cursor_factory=DictCursor)
                continue
            except Exception as e:
                logger.error(f"Fatal error in batch load: {e}")
                if self.conn:
                    self.conn.rollback()
                raise

        return {'inserted': inserted, 'skipped': skipped, 'total': total}

    def _bulk_insert_records(self, cur, records: List[Dict]):
        """Bulk insert records using execute_values for 10-100x speed improvement."""
        if not records:
            return
        
        # Prepare data tuples
        values = []
        for record in records:
            # Get store address
            store_address = record.get('store_address')
            if not store_address or store_address in ['Malaysia', 'Unknown']:
                store_name = record.get('store_name')
                if store_name and store_name not in self.store_cache:
                    self.store_cache[store_name] = self._get_store_details(store_name)
                store_info = self.store_cache.get(store_name, {})
                store_address = store_info.get('address') or record.get('store_address')
            
            values.append((
                str(uuid.uuid4()),                        # Id
                str(uuid.uuid4()),                        # ItemId
                record.get('source', 'ETL'),              # Source
                record.get('item_name'),                  # ItemName
                record.get('canonical_item_id'),          # CanonicalItemId
                record.get('unit_price'),                 # UnitPrice
                record.get('unit_price'),                 # TotalPrice
                1,                                        # Quantity
                record.get('category'),                   # Category
                datetime.now(),                           # PurchaseDate
                record.get('store_name'),                 # StoreName
                store_address or record.get('store_name'), # StoreAddress
                record.get('latitude'),                   # Latitude
                record.get('longitude'),                  # Longitude
                1.0,                                      # LocationConfidence
                record.get('pricing_zone_id'),            # PricingZoneId
                datetime.now()                            # CreatedAt
            ))
        
        # Bulk insert with execute_values (10-100x faster than individual inserts)
        insert_query = '''
            INSERT INTO purchase_analytics_gold (
                "Id", "ItemId", "Source", "ItemName", "CanonicalItemId",
                "UnitPrice", "TotalPrice", "Quantity", "Category", "PurchaseDate",
                "StoreName", "StoreAddress", "Latitude", "Longitude", "LocationConfidence",
                "PricingZoneId", "CreatedAt"
            ) VALUES %s
        '''
        
        execute_values(cur, insert_query, values, page_size=500)

    def _insert_record(self, cur, record: Dict):
        """Insert a single record into purchase_analytics_gold."""
        item_id = str(uuid.uuid4())
        
        # Get store address - try lookup first, fallback to record value
        store_address = record.get('store_address')
        if not store_address or store_address in ['Malaysia', 'Unknown']:
            store_name = record.get('store_name')
            if store_name and store_name not in self.store_cache:
                self.store_cache[store_name] = self._get_store_details(store_name)
            store_info = self.store_cache.get(store_name, {})
            store_address = store_info.get('address') or record.get('store_address')
        
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
            store_address or record.get('store_name'),  # Fallback to store name if no address
            record.get('latitude'),
            record.get('longitude'),
            1.0,                      
            record.get('pricing_zone_id'), # New column
            datetime.now()            # CreatedAt
        ))

"""
Candidate Generator for Amazon-style canonicalization.

Generates a small set of high-quality candidates (10-50) from canonical items
using brand, size, and token-based strategies.
"""
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor


class CandidateGenerator:
    """
    Generate candidate matches using structured attributes.
    Amazon approach: narrow to ~10-50 candidates before scoring.
    """
    
    def __init__(self, db_connection):
        """
        Initialize with database connection.
        
        Args:
            db_connection: psycopg2 connection object
        """
        self.conn = db_connection
    
    def refresh_connection(self):
        """Refresh database connection if closed."""
        try:
            # Test if connection is alive
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            # Connection is dead, need to reconnect from parent
            # This will be handled by caller refreshing the connection
            pass
    
    def generate_candidates(
        self,
        brand: Optional[str],
        size_normalized: Optional[float],
        size_unit: Optional[str],
        category: Optional[str],
        name_tokens: List[str],
        max_candidates: int = 50,
        skip_health_check: bool = False
    ) -> List[Dict]:
        """
        Generate candidates using three strategies (ordered by precision):
        1. Brand + Size exact match (highest precision)
        2. Brand + Category match (medium precision)
        3. Token overlap using GIN index (fast broad search)
        
        Args:
            brand: Extracted brand name
            size_normalized: Normalized size value
            size_unit: Normalized size unit
            category: Product category
            name_tokens: List of key tokens
            max_candidates: Maximum candidates to return
            skip_health_check: Skip connection check (use when already verified)
            
        Returns:
            List of candidate canonical items (dicts with all fields)
        """
        candidates = []
        seen_ids = set()
        
        # Check connection health before querying (skip if caller already checked)
        if not skip_health_check:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                # Connection closed - return empty to avoid crash
                # Caller will create new master
                return []
        
        # Strategy 1: Brand + Size exact match (only masters)
        if brand and size_normalized and size_unit:
            strategy1 = self._get_brand_size_matches(
                brand, size_normalized, size_unit
            )
            for item in strategy1:
                if item['id'] not in seen_ids:
                    candidates.append(item)
                    seen_ids.add(item['id'])
        
        # Strategy 2: Brand + Category match (only masters)
        if brand and category and len(candidates) < max_candidates:
            strategy2 = self._get_brand_category_matches(brand, category)
            for item in strategy2:
                if item['id'] not in seen_ids and len(candidates) < max_candidates:
                    candidates.append(item)
                    seen_ids.add(item['id'])
        
        # Strategy 3: Token overlap using GIN index (broader search)
        if name_tokens and len(candidates) < max_candidates:
            strategy3 = self._get_token_overlap_matches(name_tokens)
            for item in strategy3:
                if item['id'] not in seen_ids and len(candidates) < max_candidates:
                    candidates.append(item)
                    seen_ids.add(item['id'])
        
        return candidates[:max_candidates]
    
    def _get_brand_size_matches(
        self,
        brand: str,
        size_normalized: float,
        size_unit: str,
        tolerance: float = 0.05
    ) -> List[Dict]:
        """
        Get items with exact brand + size within tolerance.
        Uses composite index on (brand, size_normalized, size_unit).
        
        Args:
            brand: Brand name
            size_normalized: Normalized size value
            size_unit: Normalized size unit
            tolerance: Size tolerance (default 5%)
            
        Returns:
            List of matching items (masters only)
        """
        min_size = size_normalized * (1 - tolerance)
        max_size = size_normalized * (1 + tolerance)
        
        query = """
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND LOWER("Brand") = LOWER(%s)
              AND "SizeUnit" = %s
              AND "SizeNormalized" BETWEEN %s AND %s
            ORDER BY "Confidence" DESC
            LIMIT 20
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (brand, size_unit, min_size, max_size))
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_brand_category_matches(
        self,
        brand: str,
        category: str
    ) -> List[Dict]:
        """
        Get items with same brand + category.
        Useful when size is missing/unreliable.
        
        Args:
            brand: Brand name
            category: Product category
            
        Returns:
            List of matching items (masters only)
        """
        query = """
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND LOWER("Brand") = LOWER(%s)
              AND LOWER("Category") = LOWER(%s)
            ORDER BY "Confidence" DESC
            LIMIT 30
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (brand, category))
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_token_overlap_matches(
        self,
        name_tokens: List[str],
        min_overlap: int = 2
    ) -> List[Dict]:
        """
        Get items with token overlap using GIN index.
        Fast broad search for edge cases.
        
        Args:
            name_tokens: List of key tokens
            min_overlap: Minimum overlapping tokens required
            
        Returns:
            List of matching items (masters only)
        """
        if len(name_tokens) < min_overlap:
            return []
        
        # Use PostgreSQL array overlap operator && with GIN index
        query = """
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND "NameTokens" && %s::text[]
            ORDER BY 
                -- Rank by number of overlapping tokens
                (
                    SELECT COUNT(*)
                    FROM unnest("NameTokens") t
                    WHERE t = ANY(%s::text[])
                ) DESC,
                "Confidence" DESC
            LIMIT 50
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (name_tokens, name_tokens))
            results = [dict(row) for row in cursor.fetchall()]
            
            # Post-filter: keep only items with min_overlap tokens
            filtered = []
            for item in results:
                overlap_count = len(set(name_tokens) & set(item['name_tokens']))
                if overlap_count >= min_overlap:
                    filtered.append(item)
            
            return filtered
    
    def generate_candidates_batch(
        self,
        items: List[Dict],
        max_candidates: int = 50
    ) -> Dict[int, List[Dict]]:
        """
        Generate candidates for a batch of items efficiently.
        Reduces database queries from 3*N to 3 (100x speedup).
        
        Args:
            items: List of item dicts with keys: brand, size_normalized, size_unit,
                   category, name_tokens
            max_candidates: Maximum candidates per item
            
        Returns:
            Dict mapping item index to list of candidates
        """
        if not items:
            return {}
        
        # Collect all unique attributes from batch
        brands = set()
        size_ranges = []  # List of (brand, min_size, max_size, unit, item_idx)
        categories = set()
        all_tokens = set()
        brand_category_pairs = []  # List of (brand, category, item_idx)
        
        for idx, item in enumerate(items):
            brand = item.get('brand')
            size_normalized = item.get('size_normalized')
            size_unit = item.get('size_unit')
            category = item.get('category')
            name_tokens = item.get('name_tokens', [])
            
            if brand:
                brands.add(brand.lower())
            
            if brand and size_normalized and size_unit:
                tolerance = 0.05
                min_size = size_normalized * (1 - tolerance)
                max_size = size_normalized * (1 + tolerance)
                size_ranges.append((brand.lower(), min_size, max_size, size_unit, idx))
            
            if brand and category:
                brand_category_pairs.append((brand.lower(), category.lower(), idx))
                categories.add(category.lower())
            
            if name_tokens:
                all_tokens.update(name_tokens)
        
        # Initialize results
        results = {idx: [] for idx in range(len(items))}
        seen_per_item = {idx: set() for idx in range(len(items))}
        
        # Strategy 1: Batch brand+size query
        if size_ranges:
            size_candidates = self._get_batch_brand_size_matches(size_ranges)
            for item_idx, candidates in size_candidates.items():
                for candidate in candidates:
                    if candidate['id'] not in seen_per_item[item_idx]:
                        results[item_idx].append(candidate)
                        seen_per_item[item_idx].add(candidate['id'])
        
        # Strategy 2: Batch brand+category query
        if brand_category_pairs:
            category_candidates = self._get_batch_brand_category_matches(brand_category_pairs)
            for item_idx, candidates in category_candidates.items():
                if len(results[item_idx]) < max_candidates:
                    for candidate in candidates:
                        if (candidate['id'] not in seen_per_item[item_idx] and 
                            len(results[item_idx]) < max_candidates):
                            results[item_idx].append(candidate)
                            seen_per_item[item_idx].add(candidate['id'])
        
        # Strategy 3: Batch token overlap query
        if all_tokens:
            token_candidates = self._get_batch_token_overlap_matches(
                list(all_tokens), 
                items
            )
            for item_idx, candidates in token_candidates.items():
                if len(results[item_idx]) < max_candidates:
                    for candidate in candidates:
                        if (candidate['id'] not in seen_per_item[item_idx] and 
                            len(results[item_idx]) < max_candidates):
                            results[item_idx].append(candidate)
                            seen_per_item[item_idx].add(candidate['id'])
        
        # Trim to max_candidates per item
        for idx in results:
            results[idx] = results[idx][:max_candidates]
        
        return results
    
    def _get_batch_brand_size_matches(
        self,
        size_ranges: List[tuple]
    ) -> Dict[int, List[Dict]]:
        """
        Batch query for brand+size matches.
        
        Args:
            size_ranges: List of (brand, min_size, max_size, unit, item_idx)
            
        Returns:
            Dict mapping item_idx to candidates
        """
        if not size_ranges:
            return {}
        
        # Build OR conditions for all size ranges
        conditions = []
        params = []
        
        for brand, min_size, max_size, unit, item_idx in size_ranges:
            conditions.append(
                '(LOWER("Brand") = %s AND "SizeUnit" = %s AND "SizeNormalized" BETWEEN %s AND %s)'
            )
            params.extend([brand, unit, min_size, max_size])
        
        query = f"""
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND ({' OR '.join(conditions)})
            ORDER BY "Confidence" DESC
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            all_matches = [dict(row) for row in cursor.fetchall()]
        
        # Group by item_idx
        results = {}
        for brand, min_size, max_size, unit, item_idx in size_ranges:
            item_matches = [
                m for m in all_matches
                if (m['brand'].lower() == brand and 
                    m['size_unit'] == unit and
                    min_size <= m['size_normalized'] <= max_size)
            ]
            results[item_idx] = item_matches[:20]  # Limit per item
        
        return results
    
    def _get_batch_brand_category_matches(
        self,
        brand_category_pairs: List[tuple]
    ) -> Dict[int, List[Dict]]:
        """
        Batch query for brand+category matches.
        
        Args:
            brand_category_pairs: List of (brand, category, item_idx)
            
        Returns:
            Dict mapping item_idx to candidates
        """
        if not brand_category_pairs:
            return {}
        
        # Build OR conditions
        conditions = []
        params = []
        
        for brand, category, item_idx in brand_category_pairs:
            conditions.append(
                '(LOWER("Brand") = %s AND LOWER("Category") = %s)'
            )
            params.extend([brand, category])
        
        query = f"""
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND ({' OR '.join(conditions)})
            ORDER BY "Confidence" DESC
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            all_matches = [dict(row) for row in cursor.fetchall()]
        
        # Group by item_idx
        results = {}
        for brand, category, item_idx in brand_category_pairs:
            item_matches = [
                m for m in all_matches
                if (m['brand'].lower() == brand and 
                    m['category'].lower() == category)
            ]
            results[item_idx] = item_matches[:30]  # Limit per item
        
        return results
    
    def _get_batch_token_overlap_matches(
        self,
        all_tokens: List[str],
        items: List[Dict],
        min_overlap: int = 2
    ) -> Dict[int, List[Dict]]:
        """
        Batch query for token overlap matches.
        
        Args:
            all_tokens: All unique tokens from batch
            items: Original items to match against
            min_overlap: Minimum overlapping tokens
            
        Returns:
            Dict mapping item_idx to candidates
        """
        if not all_tokens:
            return {}
        
        query = """
            SELECT 
                "Id" as id, "Name" as item_name, "Brand" as brand, "Size" as size,
                "SizeNormalized" as size_normalized, "SizeUnit" as size_unit,
                "PackCount" as pack_count, "Variant" as variant, "NameTokens" as name_tokens,
                "Category" as category,
                "IsMaster" as is_master, "Confidence" as confidence, "CreatedAt" as created_at
            FROM canonical_items
            WHERE "IsMaster" = true
              AND "NameTokens" && %s::text[]
            ORDER BY "Confidence" DESC
            LIMIT 500
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (all_tokens,))
            all_matches = [dict(row) for row in cursor.fetchall()]
        
        # Group by item_idx based on token overlap
        results = {}
        for idx, item in enumerate(items):
            item_tokens = set(item.get('name_tokens', []))
            if len(item_tokens) < min_overlap:
                continue
            
            item_matches = []
            for candidate in all_matches:
                overlap_count = len(item_tokens & set(candidate['name_tokens']))
                if overlap_count >= min_overlap:
                    item_matches.append(candidate)
            
            # Sort by overlap count descending
            item_matches.sort(
                key=lambda c: len(item_tokens & set(c['name_tokens'])),
                reverse=True
            )
            results[idx] = item_matches[:50]  # Limit per item
        
        return results


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    generator = CandidateGenerator(conn)
    
    # Test case: Receipt item "Farm Fresh Pure Fresh /"
    candidates = generator.generate_candidates(
        brand="Farm Fresh",
        size_normalized=2.0,
        size_unit="L",
        category="Dairy",
        name_tokens=["farm", "fresh", "pure", "milk"],
        max_candidates=50
    )
    
    print(f"Generated {len(candidates)} candidates:")
    for i, candidate in enumerate(candidates[:10], 1):
        print(f"{i}. {candidate['item_name']} - {candidate['brand']} {candidate['size']}")
    
    conn.close()

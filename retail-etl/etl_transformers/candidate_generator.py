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
    
    def generate_candidates(
        self,
        brand: Optional[str],
        size_normalized: Optional[float],
        size_unit: Optional[str],
        category: Optional[str],
        name_tokens: List[str],
        max_candidates: int = 50
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
            
        Returns:
            List of candidate canonical items (dicts with all fields)
        """
        candidates = []
        seen_ids = set()
        
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

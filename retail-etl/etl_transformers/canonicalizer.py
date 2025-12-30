"""
Canonicalizer service for standardizing product names.

Uses a combination of:
1. Text normalization
2. Alias lookup
3. Vector similarity matching (embeddings)
"""
import re
from typing import Optional, Dict, Tuple
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid


class Canonicalizer:
    """Handles product name canonicalization using embeddings and aliases."""
    
    def __init__(self, db_config: Dict, similarity_threshold: float = 0.90):
        """
        Initialize the canonicalizer.
        
        Args:
            db_config: PostgreSQL connection config
            similarity_threshold: Minimum similarity score for auto-match (0-1)
        """
        self.db_config = db_config
        self.similarity_threshold = similarity_threshold
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.conn = None
        self._cache = {} # Local cache to avoid DB/AI calls for repeated items in same run
    
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
            self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize product name text.
        
        Args:
            text: Raw product name
            
        Returns:
            Normalized text (lowercase, no extra spaces)
        """
        # Convert to lowercase
        text = text.lower()
        # Replace special characters with space
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Remove ' 1 unit' suffix if present
        text = re.sub(r'\s1\sunit$', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def check_exact_match(self, normalized_name: str) -> Optional[str]:
        """
        Check for exact match in canonical_items.
        
        Args:
            normalized_name: Normalized product name
            
        Returns:
            canonical_item_id if found, None otherwise
        """
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT "Id" FROM canonical_items WHERE LOWER("Name") = %s LIMIT 1',
                (normalized_name,)
            )
            result = cur.fetchone()
            return str(result['Id']) if result else None
    
    def check_alias_match(self, normalized_name: str) -> Optional[str]:
        """
        Check for alias match in canonical_item_aliases.
        
        Args:
            normalized_name: Normalized product name
            
        Returns:
            canonical_item_id if found, None otherwise
        """
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT "CanonicalItemId" FROM canonical_item_aliases WHERE LOWER("Alias") = %s LIMIT 1',
                (normalized_name,)
            )
            result = cur.fetchone()
            return str(result['CanonicalItemId']) if result else None
    
    def find_similar_embedding(self, embedding: list) -> Optional[Tuple[str, float]]:
        """
        Find similar product using vector similarity.
        
        Args:
            embedding: Product name embedding vector
            
        Returns:
            Tuple of (canonical_item_id, similarity_score) if found, None otherwise
        """
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Use pgvector's cosine similarity operator
            cur.execute(
                '''
                SELECT "CanonicalItemId", 1 - ("Embedding" <=> %s::vector) as similarity
                FROM canonical_item_embeddings
                ORDER BY "Embedding" <=> %s::vector
                LIMIT 1
                ''',
                (embedding, embedding)
            )
            result = cur.fetchone()
            if result and result['similarity'] >= self.similarity_threshold:
                return (str(result['CanonicalItemId']), result['similarity'])
            return None
    
            return None

    def check_exact_matches_bulk(self, names: List[str]) -> Dict[str, str]:
        """Check for exact matches for multiple names at once."""
        if not names:
            return {}
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT LOWER("Name") as name, "Id" FROM canonical_items WHERE LOWER("Name") = ANY(%s)',
                (names,)
            )
            return {row['name']: str(row['Id']) for row in cur.fetchall()}

    def check_alias_matches_bulk(self, names: List[str]) -> Dict[str, str]:
        """Check for alias matches for multiple names at once."""
        if not names:
            return {}
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT LOWER("Alias") as alias, "CanonicalItemId" FROM canonical_item_aliases WHERE LOWER("Alias") = ANY(%s)',
                (names,)
            )
            return {row['alias']: str(row['CanonicalItemId']) for row in cur.fetchall()}
    
    def create_canonical_item(self, name: str, category: str) -> str:
        """
        Create a new canonical item.
        
        Args:
            name: Normalized product name
            category: Product category
            
        Returns:
            New canonical_item_id
        """
        self.connect()
        item_id = str(uuid.uuid4())
        
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO canonical_items ("Id", "Name", "Category", "CreatedAt", "UpdatedAt")
                VALUES (%s, %s, %s, NOW(), NOW())
                ''',
                (item_id, name, category)
            )
            self.conn.commit()
        
        return item_id
    
    def store_embedding(self, canonical_item_id: str, embedding: list):
        """
        Store embedding for a canonical item.
        
        Args:
            canonical_item_id: Canonical item UUID
            embedding: Embedding vector
        """
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO canonical_item_embeddings ("CanonicalItemId", "Embedding", "CreatedAt")
                VALUES (%s, %s::vector, NOW())
                ON CONFLICT ("CanonicalItemId") DO UPDATE SET "Embedding" = EXCLUDED."Embedding"
                ''',
                (canonical_item_id, embedding)
            )
            self.conn.commit()
    
    def canonicalize(self, item_name: str, category: str = "Unknown") -> Dict:
        """
        Canonicalize a product name.
        """
        # Step 0: Check memory cache
        normalized = self.normalize_text(item_name)
        if normalized in self._cache:
            return self._cache[normalized]
            
        # Step 1-3: Exact/Alias match
        canonical_id = self.check_exact_match(normalized)
        if not canonical_id:
            canonical_id = self.check_alias_match(normalized)
            
        if canonical_id:
            res = {'canonical_item_id': canonical_id, 'match_method': 'exact_or_alias'}
            self._cache[normalized] = res
            return res
        
        # Step 4: Generate embedding and check similarity
        embedding = self.model.encode(normalized, show_progress_bar=False).tolist()
        similar = self.find_similar_embedding(embedding)
        
        if similar:
            canonical_id, score = similar
            res = {
                'canonical_item_id': canonical_id,
                'match_method': 'embedding',
                'similarity_score': score
            }
        else:
            # Step 5: Create new canonical item
            canonical_id = self.create_canonical_item(normalized, category)
            self.store_embedding(canonical_id, embedding)
            res = {'canonical_item_id': canonical_id, 'match_method': 'new'}

        self._cache[normalized] = res
        return res

    def canonicalize_batch(self, items: List[Dict]) -> List[Dict]:
        """
        Canonicalize a batch of product records efficiently.
        """
        if not items:
            return []
            
        # 1. Normalize and deduplicate items in this batch to avoid redundant AI calls
        to_process = [] # Items we haven't seen in cache
        normalized_map = {} # Maps normalized name to list of original record indices
        
        for idx, item in enumerate(items):
            norm = self.normalize_text(item['item_name'])
            if norm in self._cache:
                items[idx]['canon_res'] = self._cache[norm]
            else:
                if norm not in normalized_map:
                    normalized_map[norm] = []
                    to_process.append(norm)
                normalized_map[norm].append(idx)

        if not to_process:
            return items

        # 2. Bulk exact/alias match from DB for the "to_process" set
        exact_matches = self.check_exact_matches_bulk(to_process)
        
        still_to_alias = [n for n in to_process if n not in exact_matches]
        alias_matches = self.check_alias_matches_bulk(still_to_alias)
        
        still_to_embed = []
        for norm in to_process:
            cid = exact_matches.get(norm) or alias_matches.get(norm)
            
            if cid:
                res = {'canonical_item_id': cid, 'match_method': 'exact_or_alias'}
                self._cache[norm] = res
                for idx in normalized_map[norm]:
                    items[idx]['canon_res'] = res
            else:
                still_to_embed.append(norm)

        if not still_to_embed:
            return items

        # 3. Batch AI Encoding - THIS IS THE FAST PART
        # model.encode is significantly faster when given a large list
        embeddings = self.model.encode(still_to_embed, show_progress_bar=False)
        
        # 4. Process embedding results
        for norm, emb_np in zip(still_to_embed, embeddings):
            emb = emb_np.tolist()
            similar = self.find_similar_embedding(emb)
            
            if similar:
                cid, score = similar
                res = {
                    'canonical_item_id': cid,
                    'match_method': 'embedding',
                    'similarity_score': score
                }
            else:
                # Still need single create for new items
                # Usually new items are rare after first run
                cat = items[normalized_map[norm][0]].get('category', 'Unknown')
                cid = self.create_canonical_item(norm, cat)
                self.store_embedding(cid, emb)
                res = {'canonical_item_id': cid, 'match_method': 'new'}
            
            self._cache[norm] = res
            for idx in normalized_map[norm]:
                items[idx]['canon_res'] = res

        return items

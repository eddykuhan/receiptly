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
    
    def connect(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
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
        
        Args:
            item_name: Raw product name
            category: Product category
            
        Returns:
            Dictionary with canonical_item_id and match_method
        """
        # Step 1: Normalize
        normalized = self.normalize_text(item_name)
        
        # Step 2: Check exact match
        canonical_id = self.check_exact_match(normalized)
        if canonical_id:
            return {'canonical_item_id': canonical_id, 'match_method': 'exact'}
        
        # Step 3: Check alias match
        canonical_id = self.check_alias_match(normalized)
        if canonical_id:
            return {'canonical_item_id': canonical_id, 'match_method': 'alias'}
        
        # Step 4: Generate embedding and check similarity
        embedding = self.model.encode(normalized, show_progress_bar=False).tolist()
        similar = self.find_similar_embedding(embedding)
        
        if similar:
            canonical_id, score = similar
            return {
                'canonical_item_id': canonical_id,
                'match_method': 'embedding',
                'similarity_score': score
            }
        
        # Step 5: Create new canonical item
        canonical_id = self.create_canonical_item(normalized, category)
        self.store_embedding(canonical_id, embedding)
        
        return {'canonical_item_id': canonical_id, 'match_method': 'new'}

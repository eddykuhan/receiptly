"""
Canonicalizer service for standardizing product names.

Uses a combination of:
1. Text normalization
2. Alias lookup
3. Vector similarity matching (embeddings)
4. Amazon-style canonicalization (structured attributes + hard constraints)
"""
import re
from typing import Optional, Dict, Tuple, List
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import torch

# Import from shared library
from receiptly_core import AttributeExtractor, AmazonStyleMatcher, CandidateGenerator, normalize_text


class Canonicalizer:
    """Handles product name canonicalization using embeddings and Amazon-style matching."""
    
    def __init__(self, db_config: Dict, similarity_threshold: float = 0.90):
        """
        Initialize the canonicalizer.
        
        Args:
            db_config: PostgreSQL connection config
            similarity_threshold: Minimum similarity score for auto-match (0-1)
        """
        self.db_config = db_config
        self.similarity_threshold = similarity_threshold
        
        # Auto-detect and use GPU if available (CUDA or MPS for Mac M-series)
        if torch.cuda.is_available():
            device = 'cuda'
        elif torch.backends.mps.is_available():
            device = 'mps'
        else:
            device = 'cpu'
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        self.model.encode(['test'], show_progress_bar=False)  # Set default
        print(f"[Canonicalizer] Using device: {device}")
        
        self.conn = None
        self._cache = {} # Local cache to avoid DB/AI calls for repeated items in same run
        
        # Amazon-style components (from shared library)
        self.attribute_extractor = AttributeExtractor()
        self.candidate_generator = None  # Will be initialized after connection
        self.matcher = AmazonStyleMatcher(embedding_model=self.model)
    
    def connect(self):
        """Establish or refresh database connection."""
        is_broken = False
        if self.conn:
            try:
                # Rollback any failed transaction first
                if self.conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                    self.conn.rollback()
                
                # Execution of a simple query to check if connection is alive
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.InternalError):
                is_broken = True
            except psycopg2.Error:
                # Any other psycopg2 error, rollback and mark as broken
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                is_broken = True

        if not self.conn or self.conn.closed or is_broken:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            self.conn = psycopg2.connect(**self.db_config)
            
            # Update candidate generator with new connection
            if self.candidate_generator:
                self.candidate_generator.conn = self.conn
            else:
                self.candidate_generator = CandidateGenerator(self.conn)
            
            # Matcher doesn't need database connection (uses shared library)
            # It was already initialized in __init__ with the embedding model
    
    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def normalize_text(self, text: str) -> str:
        """Wrapper for shared library normalize_text function."""
        return normalize_text(text)
    
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
    
    def process_scraped_item(
        self,
        item_name: str,
        category: str = "Unknown",
        price: float = None,
        store_source: str = None
    ) -> str:
        """
        Process scraped item as a MASTER canonical item.
        Scraped data becomes the source of truth (IsMaster=true).
        
        Args:
            item_name: Product name from scraper
            category: Product category
            price: Product price
            store_source: Source store (e.g., "MYDIN", "Jaya Grocer")
            
        Returns:
            canonical_item_id (UUID)
        """
        self.connect()
        
        # Extract structured attributes
        attributes = self.attribute_extractor.extract_all_attributes(item_name)
        
        # Check if this exact item already exists as a master
        normalized = normalize_text(item_name)
        canonical_id = self.check_exact_match(normalized)
        
        if canonical_id:
            # Update existing master with latest attributes
            self._update_master_attributes(canonical_id, attributes, price, store_source)
            return canonical_id
        
        # Create new master canonical item
        canonical_id = str(uuid.uuid4())
        
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO canonical_items (
                    "Id", "Name", "Category",
                    "Brand", "Size", "SizeNormalized", "SizeUnit",
                    "PackCount", "Variant", "NameTokens",
                    "IsMaster", "SourceType", "Confidence",
                    "CreatedAt", "UpdatedAt"
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ''',
                (
                    canonical_id,
                    item_name,
                    category,
                    attributes['brand'],
                    attributes['size'],
                    attributes['size_normalized'],
                    attributes['size_unit'],
                    attributes['pack_count'],
                    attributes['variant'],
                    attributes['name_tokens'],
                    True,  # IsMaster
                    store_source or 'scraped',
                    1.0  # High confidence for scraped data
                )
            )
            self.conn.commit()
        
        # Store embedding
        embedding = self.model.encode(normalized, show_progress_bar=False).tolist()
        self.store_embedding(canonical_id, embedding)
        
        return canonical_id
    
    def process_scraped_items_batch(
        self,
        items: List[Dict]
    ) -> List[str]:
        """
        Process multiple scraped items with cross-store matching.
        Uses candidate generation + Amazon-style matching to find existing
        canonical items across all stores before creating new masters.
        
        CRITICAL: Processes items in mini-batches of 100 and commits incrementally
        so that later items can match against earlier items in the same batch.
        
        Args:
            items: List of dicts with keys: item_name, category, store_name
            
        Returns:
            List of canonical_item_ids in same order as input
        """
        if not items:
            return []
        
        # Refresh connection to avoid timeout
        self.connect()
        canonical_ids = []
        
        # Process in mini-batches to allow cross-item matching within the same batch
        MINI_BATCH_SIZE = 100
        total = len(items)
        
        for mini_batch_start in range(0, total, MINI_BATCH_SIZE):
            mini_batch_end = min(mini_batch_start + MINI_BATCH_SIZE, total)
            mini_batch = items[mini_batch_start:mini_batch_end]
            
            items_to_insert = []
            normalized_names = []
            mini_canonical_ids = []
            
            # Verify connection health once per mini-batch
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                connection_ok = True
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                connection_ok = False
                # If connection is dead, all items in this batch become new masters
                for item in mini_batch:
                    canonical_id = str(uuid.uuid4())
                    mini_canonical_ids.append(canonical_id)
                    attributes = self.attribute_extractor.extract_all_attributes(item['item_name'])
                    normalized = self.normalize_text(item['item_name'])
                    items_to_insert.append({
                        'id': canonical_id,
                        'name': item['item_name'],
                        'normalized': normalized,
                        'category': item.get('category', 'Unknown'),
                        'store_source': item.get('store_name', 'scraped'),
                        'attributes': attributes
                    })
                # Skip to insert phase
                continue
            
            # Phase 1: Extract attributes and do cross-store matching for mini-batch
            # Phase 1a: Extract attributes for all items in mini-batch
            batch_items_data = []
            for item in mini_batch:
                attributes = self.attribute_extractor.extract_all_attributes(item['item_name'])
                normalized = self.normalize_text(item['item_name'])
                
                batch_items_data.append({
                    'item': item,
                    'attributes': attributes,
                    'normalized': normalized,
                    'brand': attributes['brand'],
                    'size_normalized': attributes['size_normalized'],
                    'size_unit': attributes['size_unit'],
                    'category': item.get('category', 'Unknown'),
                    'name_tokens': attributes['name_tokens']
                })
            
            # Phase 1b: Batch query for candidates (100x faster than individual queries)
            all_candidates = self.candidate_generator.generate_candidates_batch(
                batch_items_data,
                max_candidates=20
            )
            
            # Phase 1c: Match each item using pre-fetched candidates
            for idx, item_data in enumerate(batch_items_data):
                item = item_data['item']
                attributes = item_data['attributes']
                normalized = item_data['normalized']
                
                # Get candidates for this specific item
                candidates = all_candidates.get(idx, [])
                
                # Use Amazon-style matcher to find best match
                best_match, score, breakdown = self.matcher.find_best_match(
                    query_attributes={
                        'item_name': item['item_name'],
                        'brand': attributes['brand'],
                        'size': attributes['size'],
                        'size_normalized': attributes['size_normalized'],
                        'size_unit': attributes['size_unit'],
                        'pack_count': attributes['pack_count'],
                        'variant': attributes['variant'],  # Include variant for constraint checking
                        'category': item.get('category', 'Unknown'),
                        'name_tokens': attributes['name_tokens']
                    },
                    candidates=candidates,
                    threshold=0.65
                )
                
                if best_match and score >= 0.65:
                    # Match found - reuse existing canonical ID
                    canonical_id = best_match['id']
                    mini_canonical_ids.append(canonical_id)
                    normalized_names.append(normalized)
                else:
                    # No match - create new master
                    canonical_id = str(uuid.uuid4())
                    normalized_names.append(normalized)
                    mini_canonical_ids.append(canonical_id)
                    
                    items_to_insert.append({
                        'id': canonical_id,
                        'name': item['item_name'],
                        'normalized': normalized,
                        'category': item.get('category', 'Unknown'),
                        'store_source': item.get('store_name', 'scraped'),
                        'attributes': attributes
                    })
            
            # Phase 2: Bulk insert new masters from this mini-batch
            if items_to_insert:
                insert_data = []
                for item_data in items_to_insert:
                    attrs = item_data['attributes']
                    insert_data.append((
                        item_data['id'],
                        item_data['name'],
                        item_data['category'],
                        attrs['brand'],
                        attrs['size'],
                        attrs['size_normalized'],
                        attrs['size_unit'],
                        attrs['pack_count'],
                        attrs['variant'],
                        attrs['name_tokens'],
                        True,  # IsMaster
                        item_data['store_source'],
                        1.0  # High confidence
                    ))
                
                insert_query = '''
                    INSERT INTO canonical_items (
                        "Id", "Name", "Category",
                        "Brand", "Size", "SizeNormalized", "SizeUnit",
                        "PackCount", "Variant", "NameTokens",
                        "IsMaster", "SourceType", "Confidence",
                        "CreatedAt", "UpdatedAt"
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                '''
                with self.conn.cursor() as cur:
                    from psycopg2.extras import execute_batch
                    execute_batch(cur, insert_query, insert_data)
                    self.conn.commit()
            
            # Phase 3: Generate embeddings for new items from this mini-batch
            if items_to_insert:
                new_item_embeddings = self.model.encode(
                    [item['normalized'] for item in items_to_insert],
                    show_progress_bar=False
                )
                
                # Insert embeddings for new canonical items
                embedding_query = '''
                    INSERT INTO canonical_item_embeddings ("CanonicalItemId", "Embedding", "CreatedAt")
                    VALUES (%s, %s::vector, NOW())
                    ON CONFLICT ("CanonicalItemId") 
                    DO UPDATE SET "Embedding" = EXCLUDED."Embedding"
                '''
                
                embedding_data = [
                    (item['id'], emb.tolist())
                    for item, emb in zip(items_to_insert, new_item_embeddings)
                ]
                
                with self.conn.cursor() as cur:
                    from psycopg2.extras import execute_batch
                    execute_batch(cur, embedding_query, embedding_data, page_size=100)
                    self.conn.commit()
            
            # Add mini-batch results to overall results
            canonical_ids.extend(mini_canonical_ids)
        
        return canonical_ids
    
    def _update_master_attributes(
        self,
        canonical_id: str,
        attributes: Dict,
        price: float = None,
        store_source: str = None
    ):
        """Update existing master item with latest attributes."""
        self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE canonical_items
                SET 
                    "Brand" = COALESCE(%s, "Brand"),
                    "Size" = COALESCE(%s, "Size"),
                    "SizeNormalized" = COALESCE(%s, "SizeNormalized"),
                    "SizeUnit" = COALESCE(%s, "SizeUnit"),
                    "PackCount" = COALESCE(%s, "PackCount"),
                    "Variant" = COALESCE(%s, "Variant"),
                    "NameTokens" = COALESCE(%s, "NameTokens"),
                    "SourceType" = COALESCE(%s, "SourceType"),
                    "UpdatedAt" = NOW()
                WHERE "Id" = %s
                ''',
                (
                    attributes['brand'],
                    attributes['size'],
                    attributes['size_normalized'],
                    attributes['size_unit'],
                    attributes['pack_count'],
                    attributes['variant'],
                    attributes['name_tokens'],
                    store_source,
                    canonical_id
                )
            )
            self.conn.commit()
    
    def canonicalize_amazon_style(
        self,
        item_name: str,
        category: str = "Unknown",
        price: float = None
    ) -> Dict:
        """
        Canonicalize using Amazon-style approach (for receipt items).
        Receipt items are fuzzy inputs that map TO existing masters.
        
        Args:
            item_name: Product name from receipt
            category: Product category
            price: Product price
            
        Returns:
            Dictionary with canonical_item_id, match_method, confidence, etc.
        """
        self.connect()
        
        # Extract structured attributes
        attributes = self.attribute_extractor.extract_all_attributes(item_name)
        attributes['item_name'] = item_name
        attributes['category'] = category
        attributes['price'] = price
        
        # Generate candidates (only from masters)
        candidates = self.candidate_generator.generate_candidates(
            brand=attributes['brand'],
            size_normalized=attributes['size_normalized'],
            size_unit=attributes['size_unit'],
            category=category,
            name_tokens=attributes['name_tokens'],
            max_candidates=50
        )
        
        if not candidates:
            # No candidates found - fallback to legacy embedding search
            return self._fallback_legacy_match(item_name, category)
        
        # Find best match using hard constraints + scoring
        best_match, confidence, score_breakdown = self.matcher.find_best_match(
            query_attributes=attributes,
            candidates=candidates,
            threshold=0.65
        )
        
        if best_match:
            # Create alias for this receipt variant
            self._create_alias(
                canonical_id=str(best_match['id']),
                alias_name=item_name,
                source='receipt',
                confidence=confidence,
                match_method='amazon_style'
            )
            
            return {
                'canonical_item_id': str(best_match['id']),
                'match_method': 'amazon_style',
                'confidence': confidence,
                'score_breakdown': score_breakdown,
                'matched_name': best_match['item_name']
            }
        else:
            # No match above threshold - fallback to legacy
            return self._fallback_legacy_match(item_name, category)
    
    def _fallback_legacy_match(self, item_name: str, category: str) -> Dict:
        """
        Fallback to legacy embedding-based matching.
        Used when Amazon-style approach finds no viable candidates.
        """
        normalized = self.normalize_text(item_name)
        embedding = self.model.encode(normalized, show_progress_bar=False).tolist()
        similar = self.find_similar_embedding(embedding)
        
        if similar:
            canonical_id, score = similar
            return {
                'canonical_item_id': canonical_id,
                'match_method': 'embedding_fallback',
                'similarity_score': score
            }
        else:
            # Create new canonical item (as receipt-sourced, not master)
            canonical_id = str(uuid.uuid4())
            
            # Extract attributes even for new items
            attributes = self.attribute_extractor.extract_all_attributes(item_name)
            
            with self.conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO canonical_items (
                        "Id", "Name", "Category",
                        "Brand", "Size", "SizeNormalized", "SizeUnit",
                        "PackCount", "Variant", "NameTokens",
                        "IsMaster", "SourceType", "Confidence",
                        "CreatedAt", "UpdatedAt"
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ''',
                    (
                        canonical_id,
                        item_name,
                        category,
                        attributes['brand'],
                        attributes['size'],
                        attributes['size_normalized'],
                        attributes['size_unit'],
                        attributes['pack_count'],
                        attributes['variant'],
                        attributes['name_tokens'],
                        False,  # Not a master (receipt-sourced)
                        'receipt',
                        0.5  # Lower confidence
                    )
                )
                self.conn.commit()
            
            self.store_embedding(canonical_id, embedding)
            
            return {
                'canonical_item_id': canonical_id,
                'match_method': 'new_receipt_item'
            }
    
    def _create_alias(
        self,
        canonical_id: str,
        alias_name: str,
        source: str,
        confidence: float,
        match_method: str
    ):
        """Create or update alias for a canonical item."""
        self.connect()
        
        # Convert numpy types to Python types
        if hasattr(confidence, 'item'):  # numpy scalar
            confidence = float(confidence)
        
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO canonical_item_aliases (
                    "CanonicalItemId", "Alias", "Source",
                    "MatchConfidence", "MatchMethod", "UsageCount",
                    "LastSeenAt", "CreatedAt"
                )
                VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())
                ON CONFLICT ("CanonicalItemId", "Alias")
                DO UPDATE SET
                    "UsageCount" = canonical_item_aliases."UsageCount" + 1,
                    "LastSeenAt" = NOW(),
                    "MatchConfidence" = GREATEST(canonical_item_aliases."MatchConfidence", EXCLUDED."MatchConfidence")
                ''',
                (canonical_id, alias_name, source, confidence, match_method)
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

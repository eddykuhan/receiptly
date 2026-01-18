import re
import uuid
import logging
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import AsyncOpenAI

# Import from shared library
from receiptly_core import AttributeExtractor, AmazonStyleMatcher, CandidateGenerator, normalize_text

from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
llm = LLMClient()
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
attribute_extractor = AttributeExtractor()

# Initialize matcher without SentenceTransformers (will use fuzzy matching for text similarity)
matcher = AmazonStyleMatcher(embedding_model=None)

logger.info("Canonicalizer service initialized with receiptly-core (AttributeExtractor + AmazonStyleMatcher + OpenAI embeddings)")


async def get_embedding(text: str) -> list[float]:
    """Generate embedding using OpenAI's text-embedding-3-small model with 384 dimensions."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=384  # Match existing database vector size
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding for '{text}': {e}")
        raise

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        logger.debug("Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def find_similar_item(clean_name: str, category: str = "Unknown"):
    """
    Find or create canonical item using Amazon-style matching.
    
    Steps:
    1. Extract attributes (brand, size, pack_count, variant)
    2. Generate candidates (brand + size filtering)
    3. Apply hard constraints (pack_count, size within 5pct, brand exact match)
    4. Score viable candidates (weighted: brand 25pct, size 30pct, text 25pct, token 10pct, price 10pct)
    5. Create new item if no match above 0.75 threshold
    """
    logger.info(f"Finding similar item for: '{clean_name}' (category: {category})")
    
    # Step 1: Extract structured attributes
    query_attrs = attribute_extractor.extract_all_attributes(clean_name)
    query_attrs['item_name'] = clean_name  # Add original name for text similarity scoring
    logger.debug(f"Extracted attributes: {query_attrs}")
    
    conn = get_db_connection()
    try:
        # Step 2: Generate candidate pool
        candidate_gen = CandidateGenerator(conn)
        candidates = candidate_gen.generate_candidates(
            brand=query_attrs.get('brand'),
            size_normalized=query_attrs.get('size_normalized'),
            size_unit=query_attrs.get('size_unit'),
            category=category,
            name_tokens=normalize_text(clean_name).split(),
            max_candidates=50
        )
        logger.debug(f"Generated {len(candidates)} candidates")
        
        if not candidates:
            # No candidates found, create new item
            logger.info("No candidates found, creating new canonical item")
            return await _create_new_canonical_item(conn, clean_name, category, query_attrs)
        
        # Step 3 & 4: Apply hard constraints + scoring
        best_match, score, breakdown = matcher.find_best_match(
            query_attributes=query_attrs,
            candidates=candidates,
            threshold=0.75
        )
        
        if best_match:
            canonical_id = str(best_match['id'])
            logger.info(f"Match found: {canonical_id} (score: {score:.3f})")
            logger.info(f"Score breakdown: {breakdown}")
            return canonical_id
        
        # Step 5: No viable match, create new item
        logger.info(f"No match above threshold (best score: {score:.3f}), creating new item")
        logger.info(f"Best score breakdown: {breakdown}")
        return await _create_new_canonical_item(conn, clean_name, category, query_attrs)
        
    except Exception as e:
        logger.error(f"Error in find_similar_item: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


async def _create_new_canonical_item(conn, clean_name: str, category: str, attributes: dict) -> str:
    """Create new canonical item with attributes."""
    norm = normalize_text(clean_name)
    new_id = str(uuid.uuid4())
    logger.debug(f"Generated new ID: {new_id}")
    
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO canonical_items (
                "Id", "Name", "Category", "Brand", "Size", "SizeNormalized", "SizeUnit",
                "PackCount", "Variant", "NameTokens", "CreatedAt", "UpdatedAt"
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ''', (
            new_id, norm, category,
            attributes.get('brand'),
            attributes.get('size'),  # Original size (e.g., "1.0L")
            attributes.get('size_normalized'),  # Normalized value (e.g., 1.0)
            attributes.get('size_unit'),  # Normalized unit (e.g., "L")
            attributes.get('pack_count', 1),
            attributes.get('variant'),
            attributes.get('name_tokens')  # List of key tokens for matching
        ))
        
        # Store embedding using OpenAI
        embedding = await get_embedding(norm)
        cur.execute('''
            INSERT INTO canonical_item_embeddings ("CanonicalItemId", "Embedding", "CreatedAt")
            VALUES (%s, %s::vector, NOW())
        ''', (new_id, embedding))
        
        conn.commit()
    
    logger.info(f"Created new canonical item: {new_id} for '{norm}'")
    return new_id


async def canonicalize_item(raw: str) -> dict:
    """Clean OCR text with LLM then match with Vector ID."""
    start_time = time.time()
    logger.info(f"Canonicalizing item: '{raw}'")

    # 1. Check Memory Cache
    logger.debug("Checking memory cache")
    cached = get_cached(raw)
    if cached and isinstance(cached, dict):
        # Verify cached canonical ID still exists in database
        canonical_id = cached.get('canonical_item_id')
        if canonical_id:
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1 FROM canonical_items WHERE "Id" = %s', (canonical_id,))
                    exists = cur.fetchone() is not None
                    
                if exists:
                    logger.info(f"✅ Cache hit for '{raw}': {canonical_id} ({time.time() - start_time:.2f}s)")
                    return cached
                else:
                    logger.warning(f"⚠️ Cached canonical ID {canonical_id} no longer exists in database. Invalidating cache.")
                    # Cache is stale, continue to re-canonicalize
            finally:
                conn.close()

    logger.debug("Cache miss, proceeding with canonicalization")

    # 2. Step 2-4: Match with Canonical ID using AttributeExtractor + Matcher
    clean_name = raw  # Skip LLM cleaning (using AttributeExtractor directly)
    logger.debug("Finding canonical match")
    match_start = time.time()
    try:
        canonical_id = await find_similar_item(clean_name)
        match_time = time.time() - match_start
        logger.info(f"Matched '{clean_name}' to canonical ID: {canonical_id} ({match_time:.2f}s)")
    except Exception as e:
        logger.error(f"Canonical matching failed for '{clean_name}': {e}")
        raise

    result = {
        "canonical_name": clean_name,
        "canonical_item_id": canonical_id
    }

    # 3. Cache Result
    logger.debug(f"Caching result for '{raw}'")
    set_cached(raw, result)

    total_time = time.time() - start_time
    logger.info(f"Canonicalization complete: '{raw}' -> '{clean_name}' (ID: {canonical_id}) ({total_time:.2f}s)")
    return result


async def canonicalize_batch(items: list[str]) -> list[dict]:
    start_time = time.time()
    logger.info(f"Canonicalizing batch of {len(items)} items")
    results = []
    for i, item in enumerate(items, 1):
        logger.debug(f"Processing item {i}/{len(items)}: '{item}'")
        try:
            result = await canonicalize_item(item)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to canonicalize item {i} '{item}': {e}")
            # Return error result instead of failing the whole batch
            results.append({
                "canonical_name": item,  # fallback to original
                "canonical_item_id": None,
                "error": str(e)
            })

    total_time = time.time() - start_time
    logger.info(f"Batch canonicalization complete: {len(results)} results ({total_time:.2f}s, {total_time/len(items):.2f}s per item)")
    return results

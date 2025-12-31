import re
import uuid
import logging
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
llm = LLMClient()
model = SentenceTransformer('all-MiniLM-L6-v2')

logger.info("Canonicalizer service initialized with LLM and vector model")

SYSTEM_PROMPT = """
You are an expert Malaysian grocery product normalizer.
Convert messy OCR item text into a clean, CANONICAL product name.

**CRITICAL: CONSISTENCY IS KEY**
The SAME product must ALWAYS produce the SAME canonical name, regardless of OCR variations.

**STEP 0: Identify Product Category**
First, determine what type of product this is:
- Dairy: milk, yogurt, cheese, butter
- Meat/Poultry: chicken, beef, lamb, pork
- Seafood: fish, prawn, udang, shrimp, crab
- Beverages: drinks, juice, soda
- Pantry: rice, noodles, beans, nuts (kacang)
- Other

**STEP 1: Extract Brand Name (BE SPECIFIC)**
Identify and normalize the brand ONLY if it's clearly a brand name:

**DAIRY BRANDS**:
- "Farm Fresh Pure Fresh" / "Farm Fresh FRS" → Brand: "Farm Fresh"
- "Dutch Lady" / "DL" / "D Lady" → Brand: "Dutch Lady"

**BEVERAGE/FOOD BRANDS**:
- "F&N" / "F & N" / "FNN" → Brand: "F&N"
- "Milo" / "MILO" / "Mil0" → Brand: "Milo"
- "Tillamook" → Brand: "Tillamook"

**IMPORTANT**: 
- "FARM" alone is NOT a brand - it means farm-raised
- Only match "Farm Fresh" when it's clearly the dairy brand, not just the word "farm"

**STEP 2: Extract Product Type**
Describe what the product actually is:
- For meat/seafood: "Chicken Leg", "Tiger Prawns", "Whole Chicken"
- For dairy: "Fresh Milk", "UHT Milk", "Chocolate Drink"
- For pantry: "Black Beans", "Peanuts", etc.

**STEP 3: Extract Size**
Standardize units and ALWAYS include size if you can find it:
- "1L" / "1 Liter" / "1000ml" → "1L"
- "500ml" / "500ML" → "500ml"
- "1kg" / "1KG" → "1kg"
- "400g" → "400g"

**OUTPUT FORMAT:**
- "Brand Product Size" (Example: "Farm Fresh Fresh Milk 1L")
- "Brand Product" (Example: "Milo")
- "Product Description Size" (Example: "Black Beans 400g")

Return ONLY the canonical name, no explanation.
"""

def get_db_connection():
    try:
        conn = psycopg2.connect(settings.DB_CONNECTION
        )
        logger.debug("Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def normalize_text(text: str) -> str:
    """Same normalization logic as ETL."""
    logger.debug(f"Normalizing text: '{text}'")
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s1\sunit$', '', text)
    text = re.sub(r'\s+', ' ', text.strip())
    logger.debug(f"Normalized to: '{text}'")
    return text

async def find_similar_item(clean_name: str, category: str = "Unknown"):
    """Mirrors the ETL Canonicalizer 5-step match process."""
    logger.info(f"Finding similar item for: '{clean_name}' (category: {category})")
    norm = normalize_text(clean_name)
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Exact Match
            logger.debug("Step 1: Checking exact match")
            cur.execute('SELECT "Id" FROM canonical_items WHERE LOWER("Name") = %s LIMIT 1', (norm,))
            res = cur.fetchone()
            if res:
                logger.info(f"✅ Exact match found: {res['Id']}")
                return str(res['Id'])

            # 2. Alias Match
            logger.debug("Step 2: Checking alias match")
            cur.execute('SELECT "CanonicalItemId" FROM canonical_item_aliases WHERE LOWER("Alias") = %s LIMIT 1', (norm,))
            res = cur.fetchone()
            if res:
                logger.info(f"✅ Alias match found: {res['CanonicalItemId']}")
                return str(res['CanonicalItemId'])

            # 3. Vector Search
            logger.debug("Step 3: Performing vector search")
            embedding = model.encode(norm).tolist()
            cur.execute('''
                SELECT "CanonicalItemId", 1 - ("Embedding" <=> %s::vector) as similarity
                FROM canonical_item_embeddings
                ORDER BY "Embedding" <=> %s::vector
                LIMIT 1
            ''', (embedding, embedding))
            res = cur.fetchone()
            if res and res['similarity'] >= 0.90:
                logger.info(f"✅ Vector match found: {res['CanonicalItemId']} (similarity: {res['similarity']:.3f})")
                return str(res['CanonicalItemId'])
            elif res:
                logger.debug(f"Vector match below threshold: {res['CanonicalItemId']} (similarity: {res['similarity']:.3f})")

            # 4. Create New (if no high-confidence match)
            logger.info("No high-confidence match found, creating new canonical item")
            new_id = str(uuid.uuid4())
            logger.debug(f"Generated new ID: {new_id}")

            cur.execute('''
                INSERT INTO canonical_items ("Id", "Name", "Category", "CreatedAt", "UpdatedAt")
                VALUES (%s, %s, %s, NOW(), NOW())
            ''', (new_id, norm, category))

            cur.execute('''
                INSERT INTO canonical_item_embeddings ("CanonicalItemId", "Embedding", "CreatedAt")
                VALUES (%s, %s::vector, NOW())
            ''', (new_id, embedding))

            conn.commit()
            logger.info(f"✅ Created new canonical item: {new_id} for '{norm}'")
            return new_id
    except Exception as e:
        logger.error(f"Error in find_similar_item: {e}")
        conn.rollback()
        raise

async def canonicalize_item(raw: str) -> dict:
    """Clean OCR text with LLM then match with Vector ID."""
    start_time = time.time()
    logger.info(f"Canonicalizing item: '{raw}'")

    # 1. Check Memory Cache
    logger.debug("Checking memory cache")
    cached = get_cached(raw)
    if cached and isinstance(cached, dict):
        logger.info(f"✅ Cache hit for '{raw}': {cached['canonical_item_id']} ({time.time() - start_time:.2f}s)")
        return cached

    logger.debug("Cache miss, proceeding with canonicalization")

    # # 2. Step 1: LLM Cleaning
    # logger.debug("Calling LLM for text cleaning")
    # llm_start = time.time()
    # try:
    #     clean_name = await llm.chat(
    #         system_prompt=SYSTEM_PROMPT,
    #         user_prompt=raw
    #     )
    #     llm_time = time.time() - llm_start
    #     logger.info(f"LLM cleaned '{raw}' to '{clean_name}' ({llm_time:.2f}s)")
    # except Exception as e:
    #     logger.error(f"LLM call failed for '{raw}': {e}")
    #     raise

    # 3. Step 2-4: Match with Canonical ID
    clean_name = raw  # Temporarily skip LLM step for faster testing
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

    # 4. Cache Result
    logger.debug(f"Caching result for '{raw}'")
    set_cached(raw, result)

    total_time = time.time() - start_time
    logger.info(f"✅ Canonicalization complete: '{raw}' → '{clean_name}' (ID: {canonical_id}) ({total_time:.2f}s)")
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
    logger.info(f"✅ Batch canonicalization complete: {len(results)} results ({total_time:.2f}s, {total_time/len(items):.2f}s per item)")
    return results

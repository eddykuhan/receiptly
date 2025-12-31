import re
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached
from config import get_settings

settings = get_settings()
llm = LLMClient()
model = SentenceTransformer('all-MiniLM-L6-v2')

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
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )

def normalize_text(text: str) -> str:
    """Same normalization logic as ETL."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s1\sunit$', '', text)
    text = re.sub(r'\s+', ' ', text.strip())
    return text

async def find_similar_item(clean_name: str, category: str = "Unknown"):
    """Mirrors the ETL Canonicalizer 5-step match process."""
    norm = normalize_text(clean_name)
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Exact Match
            cur.execute('SELECT "Id" FROM canonical_items WHERE LOWER("Name") = %s LIMIT 1', (norm,))
            res = cur.fetchone()
            if res: return str(res['Id'])

            # 2. Alias Match
            cur.execute('SELECT "CanonicalItemId" FROM canonical_item_aliases WHERE LOWER("Alias") = %s LIMIT 1', (norm,))
            res = cur.fetchone()
            if res: return str(res['CanonicalItemId'])

            # 3. Vector Search
            embedding = model.encode(norm).tolist()
            cur.execute('''
                SELECT "CanonicalItemId", 1 - ("Embedding" <=> %s::vector) as similarity
                FROM canonical_item_embeddings
                ORDER BY "Embedding" <=> %s::vector
                LIMIT 1
            ''', (embedding, embedding))
            res = cur.fetchone()
            if res and res['similarity'] >= 0.90:
                return str(res['CanonicalItemId'])

            # 4. Create New (if no high-confidence match)
            new_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO canonical_items ("Id", "Name", "Category", "CreatedAt", "UpdatedAt")
                VALUES (%s, %s, %s, NOW(), NOW())
            ''', (new_id, norm, category))
            
            cur.execute('''
                INSERT INTO canonical_item_embeddings ("CanonicalItemId", "Embedding", "CreatedAt")
                VALUES (%s, %s::vector, NOW())
            ''', (new_id, embedding))
            
            conn.commit()
            return new_id
    finally:
        conn.close()

async def canonicalize_item(raw: str) -> dict:
    """Clean OCR text with LLM then match with Vector ID."""
    # 1. Check Memory Cache
    cached = get_cached(raw)
    if cached and isinstance(cached, dict):
        return cached

    # 2. Step 1: LLM Cleaning
    clean_name = await llm.chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=raw
    )

    # 3. Step 2-4: Match with Canonical ID
    canonical_id = await find_similar_item(clean_name)

    result = {
        "canonical_name": clean_name,
        "canonical_item_id": canonical_id
    }

    # 4. Cache Result
    set_cached(raw, result)

    return result

async def canonicalize_batch(items: list[str]) -> list[dict]:
    results = []
    for item in items:
        results.append(await canonicalize_item(item))
    return results

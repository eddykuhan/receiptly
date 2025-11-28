from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached

llm = LLMClient()

SYSTEM_PROMPT = """
You are an expert Malaysian grocery product normalizer.
Convert messy OCR item text into a clean, CANONICAL product name.

**CRITICAL: CONSISTENCY IS KEY**
The SAME product must ALWAYS produce the SAME canonical name, regardless of OCR variations.

**STEP 1: Extract Brand Name**
Identify and normalize the brand:
- "Farm Fresh Pure Fresh" → Brand: "Farm Fresh"
- "Farm Fresh FRS" → Brand: "Farm Fresh"  
- "F&N" / "F & N" / "FNN" → Brand: "F&N"
- "Dutch Lady" / "DL" / "D Lady" → Brand: "Dutch Lady"
- "Milo" / "MILO" / "Mil0" → Brand: "Milo"

**STEP 2: Extract Product Type (if clearly stated)**
Only include if explicitly mentioned:
- "Fresh Milk" / "Pure Fresh Milk" / "Pure Milk" → "Fresh Milk"
- "UHT Milk" / "Long Life Milk" → "UHT Milk"
- "Chocolate Drink" / "Choc Drink" → "Chocolate Drink"
- "Low Fat" / "Lite" / "Light" → "Low Fat"

**STEP 3: Extract Size (if present)**
Standardize units:
- "1L" / "1 L" / "1 Liter" → "1L"
- "500ml" / "500 ml" / "500ML" → "500ml"
- "1kg" / "1 kg" / "1KG" → "1kg"

**OUTPUT FORMAT:**
- If only brand is clear: Return just the brand name
  Example: "Farm Fresh FRS" → "Farm Fresh"
  
- If brand + product type is clear: Return "Brand Product"
  Example: "Farm Fresh Pure Fresh" → "Farm Fresh Fresh Milk"
  
- If brand + product + size is clear: Return "Brand Product Size"
  Example: "Farm Fresh Pure Fresh 1L" → "Farm Fresh Fresh Milk 1L"

**IMPORTANT RULES:**
1. ALWAYS normalize brand names to their most common form
2. Remove OCR noise (random numbers, special chars)
3. Be CONSISTENT - same input variations should produce same output
4. Don't add information that isn't in the input
5. Return ONLY the canonical name, no explanation

Examples:
- "Farm Fresh Pure Fresh" → "Farm Fresh Fresh Milk"
- "Farm Fresh FRS" → "Farm Fresh Fresh Milk"
- "MILO 1KG" → "Milo 1kg"
- "Dutch Lady Low Fat 1L" → "Dutch Lady Low Fat 1L"
"""

async def canonicalize_item(raw: str) -> str:

    # 1. Check in-memory cache
    cached = get_cached(raw)
    if cached:
        return cached

    # 2. Call LLM
    canonical = await llm.chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=raw
    )

    # 3. Save to cache
    set_cached(raw, canonical)

    return canonical


async def canonicalize_batch(items: list[str]) -> list[str]:
    results = []
    for item in items:
        results.append(await canonicalize_item(item))
    return results

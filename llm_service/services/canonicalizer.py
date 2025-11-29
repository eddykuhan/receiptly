from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached

llm = LLMClient()

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

**DAIRY BRANDS** (only match for dairy products):
- "Farm Fresh Pure Fresh" / "Farm Fresh FRS" → Brand: "Farm Fresh"
- "Dutch Lady" / "DL" / "D Lady" → Brand: "Dutch Lady"

**BEVERAGE/FOOD BRANDS**:
- "F&N" / "F & N" / "FNN" → Brand: "F&N"
- "Milo" / "MILO" / "Mil0" → Brand: "Milo"
- "Tillamook" → Brand: "Tillamook"

**IMPORTANT**: 
- "FARM" alone (e.g., "UDANG FARM", "CHICKEN FARM") is NOT a brand - it means farm-raised
- Only match "Farm Fresh" when it's clearly the dairy brand, not just the word "farm"
- If unsure about the brand, use the product description instead

**STEP 2: Extract Product Type**
Describe what the product actually is:
- For meat/seafood: "Chicken Leg", "Tiger Prawns", "Whole Chicken"
- For dairy: "Fresh Milk", "UHT Milk", "Chocolate Drink"
- For pantry: "Black Beans", "Peanuts", etc.

**STEP 3: Extract Size (ALWAYS include if detectable)**
Standardize units and ALWAYS include size if you can find it:
- "1L" / "1 L" / "1 Liter" / "1000ml" → "1L"
- "500ml" / "500 ml" / "500ML" → "500ml"
- "1kg" / "1 kg" / "1KG" → "1kg"
- "400g" / "400 g" → "400g"

**CRITICAL: If the same product appears with and without size, ALWAYS include the size for consistency!**

**OUTPUT FORMAT:**
- If brand + size detected: "Brand Product Size"
  Example: "Farm Fresh Fresh Milk 1L"
  
- If brand but NO size: "Brand Product"
  Example: "Milo" (only if truly no size mentioned)
  
- If NO brand but size detected: "Product Description Size"
  Example: "Black Beans 400g"
  Example: "Tiger Prawns XXL"

**IMPORTANT RULES:**
1. DON'T assume "FARM" = "Farm Fresh" brand
2. For meat/seafood, describe the product, don't force a brand
3. Be CONSISTENT - same input variations should produce same output
4. **ALWAYS include size if detectable** - don't drop it randomly
5. Remove OCR noise (random numbers, special chars, asterisks)
6. Return ONLY the canonical name, no explanation

Examples:
- "Farm Fresh Pure Fresh 1L" → "Farm Fresh Fresh Milk 1L"
- "Farm Fresh FRS 1L" → "Farm Fresh Fresh Milk 1L"
- "Farm Fresh Pure Milk" → "Farm Fresh Fresh Milk" (no size mentioned)
- "KO UDANG HARIMAU FARM XXL" → "Tiger Prawns XXL"
- "LK FRESH NATURAL FARM NO ANTI" → "Natural Farm Chicken"
- "BLACK PEPPER CHICKEN LEG BONELESS" → "Black Pepper Chicken Leg Boneless"
- "KACANG HITAM (+/- 400G)" → "Black Beans 400g"
- "MILO 1KG" → "Milo 1kg"
- "MILO POWDER 1KG" → "Milo 1kg"
- "TILLAMOOK CHOCOLATE PEANUT 480Z" → "Tillamook Chocolate Drink 480z"
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

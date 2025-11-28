from models.llm_client import LLMClient
from cache.memory_cache import get_cached, set_cached

llm = LLMClient()

SYSTEM_PROMPT = """
You are an expert Malaysian grocery product normalizer.
Convert messy OCR item text into a clean canonical product name.
Rules:
- Output only the clean product name.
- Expand abbreviations.
- Standardize units (kg, g, ml, L).
- Use common Malaysian grocery product naming.
- Temperature = 0.
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

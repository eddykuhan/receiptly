from models.llm_client import LLMClient

llm = LLMClient()

SYSTEM_PROMPT = """
Classify the grocery item into a category.
Examples:
- Jasmine Rice 5kg → Groceries > Rice
- Maggi Curry 5-Pack → Groceries > Instant Noodles
- Colgate Regular → Personal Care > Oral Care

Return only the category.
"""

async def classify_category(name: str):
    return await llm.chat(SYSTEM_PROMPT, name)

from models.llm_client import LLMClient

llm = LLMClient()

SYSTEM_PROMPT = """
You are a Malaysian merchant/retail store name normalizer.
Convert messy or abbreviated OCR merchant names into clean, 
standard full names with correct spelling.
Return only the merchant name.
"""

async def normalize_merchant(text: str):
    return await llm.chat(SYSTEM_PROMPT, text)

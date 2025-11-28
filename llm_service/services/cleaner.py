from models.llm_client import LLMClient
llm = LLMClient()

SYSTEM_PROMPT = """
You are a receipt cleaner and validator.
Fix OCR errors, decimals, missing zeros, and output valid JSON.
Do not hallucinate new items. Correct numbers only if safe.
"""

async def clean_receipt(ocr_json: str):
    return await llm.chat(SYSTEM_PROMPT, ocr_json)

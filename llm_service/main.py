from fastapi import FastAPI
from services.canonicalizer import canonicalize_item, canonicalize_batch
from services.merchant import normalize_merchant
from services.category import classify_category
from services.cleaner import clean_receipt
from services.location_selector import select_best_location

app = FastAPI(title="Receiptly LLM Service")

@app.post("/canonicalize_item")
async def api_canonicalize_item(body: dict):
    raw = body["raw_item"]
    return {"canonical_name": await canonicalize_item(raw)}

@app.post("/canonicalize_batch")
async def api_canonicalize_batch(body: dict):
    items = body["items"]
    return {"canonical_names": await canonicalize_batch(items)}

@app.post("/normalize_merchant")
async def api_normalize_merchant(body: dict):
    return {"merchant": await normalize_merchant(body["merchant_text"])}

@app.post("/classify_category")
async def api_classify_category(body: dict):
    return {"category": await classify_category(body["name"])}

@app.post("/clean_receipt")
async def api_clean_receipt(body: dict):
    return {"cleaned": await clean_receipt(body["ocr_json"])}

@app.post("/select_best_location")
async def api_select_best_location(body: dict):
    candidates = body.get("candidates", [])
    result = await select_best_location(candidates)
    return result

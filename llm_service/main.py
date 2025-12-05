import config  # Load environment variables first
from fastapi import FastAPI, UploadFile, File
from services.canonicalizer import canonicalize_item, canonicalize_batch
from services.merchant import normalize_merchant
from services.category import classify_category
from services.cleaner import clean_receipt
from services.location_selector import select_best_location
from services.receipt_extractor import extract_merchant_from_image

app = FastAPI(
    title="Receiptly LLM Service",
    description="Microservice for LLM-powered receipt processing tasks",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "llm"}

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


@app.post("/extract_merchant")
async def api_extract_merchant(file: UploadFile = File(...)):
    """
    Extract merchant name and address from receipt image using GPT-4 Vision.
    
    This endpoint accepts a receipt image file and uses GPT-4 Vision to extract
    the merchant/store name and address directly from the image.
    
    Args:
        file: Receipt image file (JPEG, PNG, etc.)
        
    Returns:
        {
            "merchant_name": "Extracted merchant/store name",
            "merchant_address": "Extracted address/location",
            "success": true/false,
            "error": "Error message if failed"
        }
    """
    try:
        # Read image bytes from uploaded file
        image_bytes = await file.read()
        
        # Extract merchant info using GPT-4 Vision
        result = await extract_merchant_from_image(image_bytes)
        
        return result
        
    except Exception as e:
        return {
            "merchant_name": "",
            "merchant_address": "",
            "success": False,
            "error": str(e)
        }

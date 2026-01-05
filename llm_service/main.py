import config  # Load environment variables first
from fastapi import FastAPI, UploadFile, File, Form
from services.canonicalizer import canonicalize_item, canonicalize_batch
from services.merchant import normalize_merchant
from services.category import classify_category
from services.cleaner import clean_receipt
from services.location_selector import select_best_location
from services.receipt_extractor import extract_merchant_from_image
from services.receipt_enhancer import enhance_receipt_data
from services.chat_service import answer_price_question, extract_item_keywords
import json

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
    return await canonicalize_item(raw)

@app.post("/canonicalize_batch")
async def api_canonicalize_batch(body: dict):
    items = body["items"]
    results = await canonicalize_batch(items)
    return {"results": results}

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


@app.post("/enhance_receipt")
async def api_enhance_receipt(
    file: UploadFile = File(...),
    azure_result: str = Form(...),
    options: str = Form(None)
):
    """
    Enhance Azure Document Intelligence OCR results using GPT-4 Vision.
    
    This endpoint takes Azure OCR results + the original receipt image and uses
    GPT-4 Vision to:
    - Complete truncated item names
    - Add missing items Azure didn't detect
    - Remove non-product items (baskets, bags with $0.00)
    - Validate and fix quantities/prices
    - Ensure total matches item sum
    
    Args:
        file: Original receipt image file
        azure_result: JSON string of Azure Document Intelligence result
        options: Optional JSON string of enhancement options
        
    Returns:
        {
            "enhanced_result": {...},  # Enhanced Azure result format
            "corrections": [
                {
                    "field": "items[0].name",
                    "original": "MILO ACT",
                    "corrected": "MILO Activ-Go 1kg",
                    "reason": "Expanded truncated name from image",
                    "confidence": 0.95
                }
            ],
            "overall_confidence": 0.92,
            "requires_review": false,
            "stats": {
                "items_added": 0,
                "items_removed": 1,
                "corrections_made": 3
            }
        }
    """
    try:
        print(f"📨 Received enhancement request")
        print(f"  - Image size: {file.size if hasattr(file, 'size') else 'unknown'} bytes")
        print(f"  - Azure result length: {len(azure_result)} chars")
        
        # Read image bytes
        image_bytes = await file.read()
        print(f"  - Image bytes read: {len(image_bytes)} bytes")
        
        # Parse JSON strings
        azure_result_dict = json.loads(azure_result)
        print(f"  - Azure result parsed successfully")
        print(f"  - Azure items count: {len(azure_result_dict.get('fields', {}).get('Items', {}).get('value', []))}")
        
        options_dict = json.loads(options) if options else None
        print(f"  - Options: {options_dict}")
        
        # Enhance receipt
        print(f"  - Calling enhance_receipt_data...")
        result = await enhance_receipt_data(azure_result_dict, image_bytes, options_dict)
        
        print(f"  ✅ Enhancement complete")
        print(f"  - Result keys: {list(result.keys())}")
        if result.get('enhanced_result'):
            enhanced_items = result['enhanced_result'].get('fields', {}).get('Items', {}).get('value', [])
            print(f"  - Enhanced items count: {len(enhanced_items)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Enhancement error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "enhanced_result": {},
            "corrections": [],
            "overall_confidence": 0.0,
            "requires_review": True,
            "error": str(e)
        }

@app.post("/chat/ask")
async def api_chat_ask(body: dict):
    """
    Answer price comparison questions using GPT-4o-mini
    
    Request body:
    {
        "question": "Where's the cheapest milk?",
        "price_data": [
            {"item_name": "Dutch Lady Milk 1L", "store_name": "Mydin", "price": 5.90, "purchase_date": "2025-12-15"},
            {"item_name": "Dutch Lady Milk 1L", "store_name": "Tesco", "price": 6.50, "purchase_date": "2025-12-20"}
        ]
    }
    """
    question = body.get("question", "")
    price_data = body.get("price_data", [])
    
    answer = await answer_price_question(question, price_data)
    return {"answer": answer}

@app.post("/chat/extract_items")
async def api_extract_items(body: dict):
    """
    Extract item keywords from a natural language question
    
    Request body:
    {
        "question": "Where can I buy cheap milk and bread?"
    }
    
    Response:
    {
        "items": ["milk", "bread"]
    }
    """
    question = body.get("question", "")
    items = await extract_item_keywords(question)
    return {"items": items}

@app.post("/embeddings/generate")
async def api_generate_embedding(body: dict):
    """
    Generate embedding vector for a text query
    
    Request body:
    {
        "text": "nescafe gold refill pack"
    }
    
    Response:
    {
        "embedding": [0.123, -0.456, ...]  // OpenAI text-embedding-3-small (1536 dimensions)
    }
    """
    from openai import AsyncOpenAI
    from config import get_settings
    
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # Use OpenAI embeddings (same as canonicalizer)
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        dimensions=384  # Match database vector size
    )
    embedding = response.data[0].embedding
    
    return {"embedding": embedding}

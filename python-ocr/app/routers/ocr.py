from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.tesseract_ocr import TesseractOCRService
from ..utils.image_utils import download_image

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request model for receipt analysis."""
    image_url: HttpUrl
    extract_location: bool = True  # Flag to enable/disable location extraction


@router.post("/analyze")
async def analyze_receipt(
    request: AnalyzeRequest,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
    tesseract_service: TesseractOCRService = Depends(TesseractOCRService)
) -> Dict[str, Any]:
    """
    Analyze a receipt image from a URL and return structured data with store location.
    
    Uses:
    - Azure Document Intelligence for structured receipt data extraction
    - Tesseract OCR for store location/address extraction
    
    Args:
        request: Request containing the image URL and extraction options
        doc_service: Azure Document Intelligence service instance
        tesseract_service: Tesseract OCR service instance
        
    Returns:
        Dictionary containing:
        - success: bool
        - data: Raw Azure Document Intelligence analysis
        - location: Extracted store location information (if enabled)
        - validation: Validation results (is_valid_receipt, confidence, message)
    """
    try:
        print(f"Received analyze request. Image URL: {request.image_url}")
        
        # Step 1: Download image once
        print("Downloading image...")
        file_bytes = await download_image(str(request.image_url))
        print(f"Downloaded {len(file_bytes)} bytes")
        
        # Step 2: Extract store location using Tesseract (if requested)
        location_data = None
        if request.extract_location:
            print("Extracting store location with Tesseract OCR...")
            location_data = tesseract_service.extract_location_from_bytes(file_bytes)
            print(f"Location extraction complete. Success: {location_data}")
        
        # Step 3: Preprocess image for Azure
        print("Preprocessing image...")
        processed_bytes = doc_service.preprocessor.process(file_bytes)
        print(f"Image preprocessing complete. Output: {len(processed_bytes)} bytes")
        
        # Step 4: Send preprocessed image to Azure Document Intelligence
        print("Analyzing with Azure Document Intelligence...")
        receipt = await doc_service._analyze_document(processed_bytes)
        
        if not receipt:
            return {
                "success": False,
                "error": "No receipt data found",
                "location": location_data
            }
        
        # Convert to dict
        result = receipt.to_dict()
        
        # Step 5: Override Azure's merchant data with Tesseract's more accurate location data
        if location_data and location_data.get('success'):
            result = override_merchant_data_with_tesseract(result, location_data)
            print("✓ Overridden Azure merchant data with Tesseract location data")
        
        # Step 6: Validate if it's actually a receipt
        validation = validate_receipt_confidence(result)
        
        print(f"Analysis completed. Validation: {validation['is_valid_receipt']}, Confidence: {validation['confidence']}")
        
        response = {
            "success": True,
            "data": result,
            "validation": validation
        }
        
        # Add location data if extracted
        if location_data:
            response["location"] = location_data
        
        return response
        
    except Exception as e:
        print(f"Error in analyze_receipt: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


def validate_receipt_confidence(azure_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates if the analyzed document is a valid receipt based on Azure's confidence score.
    
    Args:
        azure_result: Raw Azure Document Intelligence result
        
    Returns:
        Dictionary with validation results:
        - is_valid_receipt: bool
        - confidence: float
        - message: str
        - doc_type: str
    """
    # Minimum confidence threshold for receipt validation
    MIN_CONFIDENCE = 0.7
    
    # Extract confidence and document type
    confidence = azure_result.get('confidence', 0.0)
    doc_type = azure_result.get('doc_type', 'unknown')
    
    # Check if it's identified as a receipt
    is_receipt_type = 'receipt' in doc_type.lower()
    
    # Validate confidence
    is_confident = confidence >= MIN_CONFIDENCE
    
    # Overall validation
    is_valid = is_receipt_type and is_confident
    
    # Generate message
    if not is_receipt_type:
        message = f"Document type '{doc_type}' is not a receipt"
    elif not is_confident:
        message = f"Low confidence ({confidence:.2%}). Document may not be a clear receipt image"
    else:
        message = f"Valid receipt detected with {confidence:.2%} confidence"
    
    return {
        "is_valid_receipt": is_valid,
        "confidence": confidence,
        "message": message,
        "doc_type": doc_type
    }


def override_merchant_data_with_tesseract(
    azure_result: Dict[str, Any],
    tesseract_location: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Override Azure Document Intelligence merchant/store fields with Tesseract OCR data.
    Tesseract's location extraction is often more accurate for store names and addresses.
    
    Args:
        azure_result: Azure Document Intelligence result dictionary
        tesseract_location: Tesseract location extraction result
        
    Returns:
        Modified azure_result with overridden merchant data
    """
    if not tesseract_location.get('success') or not tesseract_location.get('location'):
        return azure_result
    
    location = tesseract_location['location']
    
    # Azure receipt structure typically has 'fields' with merchant info
    if 'fields' not in azure_result:
        azure_result['fields'] = {}
    
    fields = azure_result['fields']
    
    # Override MerchantName with Tesseract's store_name
    if location.get('store_name'):
        fields['MerchantName'] = {
            'type': 'string',
            'value': location['store_name'],
            'content': location['store_name'],
            'confidence': location.get('confidence', 0.0),
            'source': 'tesseract'  # Mark source for debugging
        }
        print(f"  → Overriding MerchantName: {location['store_name']}")
    
    # Override MerchantAddress with Tesseract's address
    if location.get('address'):
        fields['MerchantAddress'] = {
            'type': 'string',
            'value': location['address'],
            'content': location['address'],
            'confidence': location.get('confidence', 0.0),
            'source': 'tesseract'
        }
        print(f"  → Overriding MerchantAddress: {location['address']}")
    
    # Add MerchantPhoneNumber if available and not already present
    if location.get('phone'):
        fields['MerchantPhoneNumber'] = {
            'type': 'phoneNumber',
            'value': location['phone'],
            'content': location['phone'],
            'confidence': location.get('confidence', 0.0),
            'source': 'tesseract'
        }
        print(f"  → Adding MerchantPhoneNumber: {location['phone']}")
    
    # Add additional location metadata
    if 'metadata' not in azure_result:
        azure_result['metadata'] = {}
    
    azure_result['metadata']['location_extraction'] = {
        'postal_code': location.get('postal_code'),
        'country': location.get('country'),
        'tesseract_confidence': location.get('confidence'),
        'extraction_strategy': tesseract_location.get('strategy_used')
    }
    
    return azure_result
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
from ..services.document_intelligence import DocumentIntelligenceService

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request model for receipt analysis."""
    image_url: HttpUrl


@router.post("/analyze")
async def analyze_receipt(
    request: AnalyzeRequest,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService)
) -> Dict[str, Any]:
    """
    Analyze a receipt image from a URL and return raw Azure Document Intelligence response
    with validation information.
    
    Args:
        request: Request containing the image URL
        doc_service: Azure Document Intelligence service instance
        
    Returns:
        Dictionary containing:
        - success: bool
        - data: Raw Azure Document Intelligence analysis
        - validation: Validation results (is_valid_receipt, confidence, message)
    """
    try:
        print(f"Received analyze request. Image URL: {request.image_url}")
        
        # Process the receipt from URL
        result = await doc_service.analyze_receipt_from_url(str(request.image_url))
        
        # Validate if it's actually a receipt
        validation = validate_receipt_confidence(result)
        
        print(f"Analysis completed. Validation: {validation['is_valid_receipt']}, Confidence: {validation['confidence']}")
        
        return {
            "success": True,
            "data": result,
            "validation": validation
        }
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
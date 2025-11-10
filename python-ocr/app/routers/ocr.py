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
    Analyze a receipt image from a URL and return raw Azure Document Intelligence response.
    
    Args:
        request: Request containing the image URL
        doc_service: Azure Document Intelligence service instance
        
    Returns:
        Dictionary containing raw Azure Document Intelligence analysis
    """
    try:
        print(f"Received analyze request. Image URL: {request.image_url}")
        
        # Process the receipt from URL
        result = await doc_service.analyze_receipt_from_url(str(request.image_url))
        
        print(f"Analysis completed successfully")
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        print(f"Error in analyze_receipt: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
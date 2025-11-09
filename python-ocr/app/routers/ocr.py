from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, Any
from ..services.azure_vision import AzureVisionService
import io

router = APIRouter()

@router.post("/analyze")
async def analyze_receipt(
    file: UploadFile = File(...),
    vision_service: AzureVisionService = Depends(AzureVisionService)
) -> Dict[str, Any]:
    """
    Analyze a receipt image and extract its information.
    
    Args:
        file: The receipt image file
        vision_service: Azure Vision service instance
        
    Returns:
        Dictionary containing extracted receipt information
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
        # Read file contents
        contents = await file.read()
        
        # Process the receipt
        result = await vision_service.analyze_receipt(contents)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
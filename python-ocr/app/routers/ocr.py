from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, Any
from ..services.document_intelligence import DocumentIntelligenceService
import io

router = APIRouter()

@router.post("/analyze")
async def analyze_receipt(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService)
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
        allowed_types = ['image/jpeg', 'image/png', 'image/tiff', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File must be one of the following types: {', '.join(allowed_types)}"
            )
        
        if file.size > 4 * 1024 * 1024:  # 4MB limit
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 4MB."
            )
        
        # Read file contents
        contents = await file.read()
        
        # Process the receipt
        result = await doc_service.analyze_receipt(
            file_bytes=contents  # Pass bytes directly
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
            
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error processing receipt: {str(e)}")  # Add logging for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Error processing receipt: {str(e)}"
        )
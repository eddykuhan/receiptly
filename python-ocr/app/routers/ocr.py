from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from typing import Dict, Any, Optional
from ..services.document_intelligence import DocumentIntelligenceService
import io

router = APIRouter()

@router.post("/analyze")
async def analyze_receipt(
    file: UploadFile = File(...),
    user_id: str = Header(..., description="User ID from authentication"),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService)
) -> Dict[str, Any]:
    """
    Analyze a receipt image and extract its information.
    
    Args:
        file: The receipt image file
        user_id: User identifier from authentication header
        doc_service: Azure Document Intelligence service instance
        
    Returns:
        Dictionary containing extracted receipt information and S3 references
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
            file_bytes=contents,
            user_id=user_id,
            filename=file.filename or "receipt.jpg",
            content_type=file.content_type
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/receipts")
async def list_user_receipts(
    user_id: str = Header(..., description="User ID from authentication"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService)
) -> Dict[str, Any]:
    """
    List all receipts for a user, optionally filtered by date range.
    
    Args:
        user_id: User identifier from authentication header
        start_date: Start date filter (YYYY-MM-DD) - optional
        end_date: End date filter (YYYY-MM-DD) - optional
        doc_service: Document Intelligence service instance
        
    Returns:
        List of receipt metadata
    """
    try:
        if not doc_service.s3_enabled:
            raise HTTPException(
                status_code=503,
                detail="S3 storage is not configured"
            )
        
        receipts = doc_service.s3_storage.list_user_receipts(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "count": len(receipts),
            "receipts": receipts
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
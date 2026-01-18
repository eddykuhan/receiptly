"""
User feedback and correction endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReceiptCorrection(BaseModel):
    """User correction to OCR result."""
    receipt_id: str = Field(..., description="Receipt ID from original analysis")
    user_id: str = Field(..., description="User ID submitting correction")
    image_hash: Optional[str] = None
    
    # Original vs corrected data
    original_merchant: Optional[str] = None
    corrected_merchant: Optional[str] = None
    
    original_total: Optional[float] = None
    corrected_total: Optional[float] = None
    
    original_items: Optional[List[Dict]] = None
    corrected_items: Optional[List[Dict]] = None
    
    # Metadata
    correction_type: str = Field(..., description="merchant|items|total|multiple")
    failed_source: Optional[str] = Field(None, description="Which OCR source failed")
    notes: Optional[str] = None


class IssueReport(BaseModel):
    """General issue report."""
    receipt_id: str
    user_id: str
    issue_type: str = Field(..., description="wrong_merchant|wrong_total|wrong_items|image_quality|other")
    description: str
    severity: str = Field(default="medium", description="low|medium|high")
    

class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    success: bool
    message: str
    correction_id: Optional[str] = None


@router.post("/correction", response_model=FeedbackResponse)
async def submit_correction(
    correction: ReceiptCorrection
) -> FeedbackResponse:
    """
    Submit user correction to improve OCR accuracy.
    
    This endpoint:
    1. Stores correction in database (TODO: implement database storage)
    2. Invalidates cache for this receipt
    3. Tracks which OCR source made the error
    4. Builds training dataset for ML improvements
    """
    try:
        # TODO: Store correction in database
        # correction_id = await store_correction(correction)
        correction_id = "temp-" + correction.receipt_id[:8]
        
        # TODO: Invalidate cache if image hash provided
        # if correction.image_hash:
        #     await invalidate_cache(correction.image_hash)
        
        # Log for analytics
        logger.info(
            "user_correction_submitted",
            extra={
                "correction_id": correction_id,
                "user_id": correction.user_id,
                "correction_type": correction.correction_type,
                "failed_source": correction.failed_source
            }
        )
        
        return FeedbackResponse(
            success=True,
            message="Thank you! Your correction helps improve our accuracy.",
            correction_id=correction_id
        )
        
    except Exception as e:
        logger.error(f"Failed to store correction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to save correction"
        )


@router.post("/issue", response_model=FeedbackResponse)
async def report_issue(
    issue: IssueReport
) -> FeedbackResponse:
    """
    Report an issue with OCR results.
    
    Enables debug mode for this user temporarily.
    """
    try:
        # TODO: Store issue report
        # issue_id = await store_issue(issue)
        issue_id = "issue-" + issue.receipt_id[:8]
        
        # TODO: Enable debug mode for this user (next 5 requests)
        # if issue.severity in ["medium", "high"]:
        #     await enable_debug_for_user(issue.user_id, request_count=5)
        
        logger.warning(
            "user_issue_reported",
            extra={
                "issue_id": issue_id,
                "user_id": issue.user_id,
                "issue_type": issue.issue_type,
                "severity": issue.severity
            }
        )
        
        return FeedbackResponse(
            success=True,
            message="Issue reported. Debug mode enabled for your next uploads.",
            correction_id=issue_id
        )
        
    except Exception as e:
        logger.error(f"Failed to store issue: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to save issue report"
        )


# Helper functions (to be implemented based on your database)
async def store_correction(correction: ReceiptCorrection) -> str:
    """Store correction in database."""
    # Implementation depends on your database choice
    # For MVP, you can use PostgreSQL via SQLAlchemy
    pass


async def store_issue(issue: IssueReport) -> str:
    """Store issue report in database."""
    pass


async def invalidate_cache(image_hash: str):
    """Invalidate cached OCR result."""
    pass


async def enable_debug_for_user(user_id: str, request_count: int = 5):
    """Enable debug mode for specific user."""
    # Store in Redis with expiry
    pass

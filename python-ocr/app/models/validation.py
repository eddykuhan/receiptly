"""
Validation models for receipt processing.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    HIGH = "high"           # >= 0.85
    MEDIUM = "medium"       # 0.70 - 0.84
    LOW = "low"            # 0.50 - 0.69
    VERY_LOW = "very_low"  # < 0.50


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    field: str
    issue_type: str  # "low_confidence", "missing", "suspicious"
    severity: str    # "warning", "error"
    message: str
    confidence: Optional[float] = None
    suggested_action: Optional[str] = None


class ReceiptValidation(BaseModel):
    """Enhanced receipt validation result."""
    is_valid_receipt: bool = Field(..., description="Overall receipt validity")
    confidence_level: ConfidenceLevel
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Field-level confidence
    merchant_confidence: float = Field(..., ge=0.0, le=1.0)
    items_confidence: float = Field(..., ge=0.0, le=1.0)
    total_confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Validation details
    issues: List[ValidationIssue] = []
    warnings: List[str] = []
    requires_manual_review: bool = False
    
    # Metadata
    doc_type: str
    processing_time_ms: int
    sources_used: List[str]  # ["azure", "llm_vision", "google_places"]
    
    # User guidance
    confidence_message: str
    next_steps: Optional[str] = None


class ProcessedReceipt(BaseModel):
    """Complete receipt processing result."""
    success: bool
    data: dict  # Raw Azure/LLM result
    validation: ReceiptValidation
    location: Optional[dict] = None
    debug_session_id: Optional[str] = None  # Only if debug enabled

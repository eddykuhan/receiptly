from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Literal, List
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.validation_service import EnhancedValidationService
from ..services.forgery_detection_service import ForgeryDetectionService
from ..services.pipeline_steps import (
    ImageDownloadStep,
    ReceiptCropStep,
    AzureAnalysisStep,
    LocationCandidatesStep,
    LLMEnhancementStep
)
from ..models.validation import ProcessedReceipt
from ..utils.debug import ImageDebugger
from ..core.config import get_settings
import time

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request model for receipt analysis."""
    image_url: HttpUrl
    extract_location: bool = True  # Flag to enable/disable location extraction
    auto_crop: bool = True  # Flag to enable/disable automatic receipt cropping
    crop_method: Literal["opencv", "azure_layout"] = "azure_layout"  # Cropping method
    enable_llm_enhancement: bool = False  # NEW: Enable LLM post-processing for better accuracy


@router.post("/analyze")
async def analyze_receipt(
    request: AnalyzeRequest,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService)
) -> ProcessedReceipt:
    """
    Analyze a receipt image from a URL and return structured data with enhanced validation.
    
    Pipeline Steps:
    1. Download image
    2. Auto-crop to receipt boundary (optional)
    3. Store original uncropped image for LLM
    4. Azure Document Intelligence analysis
    5. LLM Enhancement (optional - location, date, items)
    6. Enhanced validation with confidence scoring
    
    Args:
        request: Request containing image URL and extraction options
        doc_service: Azure Document Intelligence service instance
        
    Returns:
        ProcessedReceipt with success status, data, validation, and debug info
    """
    start_time = time.time()
    debugger = None
    
    try:
        # Initialize debugger if enabled
        settings = get_settings()
        if settings.DEBUG_IMAGE_PROCESSING:
            debugger = ImageDebugger(enabled=True)
            debugger.start_session()
            print(f"🐛 Debug mode enabled. Session: {debugger.session_id}")
        
        # ========== Step 1: Download Image ==========
        download_step = ImageDownloadStep()
        file_bytes = await download_step.execute(str(request.image_url), debugger)
        
        # Save original uncropped image for LLM Vision
        original_uncropped_bytes = file_bytes
        
        # ========== Step 1.5: Early Forgery Detection (Metadata) ==========
        print("Step 1.5: Metadata Forgery Detection...")
        forgery_service = ForgeryDetectionService()
        metadata_analysis = forgery_service.analyze_image(file_bytes)
        
        if debugger:
            debugger.save_json(metadata_analysis, "01a_metadata_analysis")
            
        # EARLY EXIT: If high risk (e.g. Photoshop detected), stop here to save costs
        if metadata_analysis.get('is_suspicious', False):
            print(f"🛑 Blocking suspicious upload based on metadata. Risk: {metadata_analysis.get('risk_score')}")
            
            # Create a "Failed/Rejected" validation object
            from ..services.validation_service import ValidationIssue, ConfidenceLevel, ReceiptValidation
            
            # Create validation issues from flags
            issues = []
            for flag in metadata_analysis.get('flags', []):
                issues.append(ValidationIssue(
                    field="image",
                    issue_type="suspicious",
                    severity="error",
                    message=f"Forgery Detected: {flag}",
                    confidence=metadata_analysis.get('risk_score', 1.0),
                    suggested_action="Upload an original, unmodified receipt photo."
                ))
            
            rejection_validation = ReceiptValidation(
                is_valid_receipt=False,
                confidence_level=ConfidenceLevel.VERY_LOW,
                overall_confidence=0.0,
                merchant_confidence=0.0,
                items_confidence=0.0,
                total_confidence=0.0,
                issues=issues,
                doc_type="suspicious_file",
                processing_time_ms=int((time.time() - start_time) * 1000),
                sources_used=["metadata_analysis"],
                confidence_message="❌ Upload rejected due to suspected manipulation",
                is_forged=True,
                forgery_confidence=metadata_analysis.get('risk_score', 1.0),
                forgery_reason=str(issues[0].message) if issues else "Suspicious metadata"
            )
            
            return ProcessedReceipt(
                success=False,
                data={"error": "Upload rejected by security filters"},
                validation=rejection_validation,
                location=None,
                debug_session_id=debugger.session_id if debugger else None
            )

        # ========== Step 2-3: Crop Receipt Boundary ==========
        crop_step = ReceiptCropStep()
        file_bytes, boundary_info = await crop_step.execute(
            file_bytes,
            request.auto_crop,
            request.crop_method,
            debugger
        )
        
        # ========== Step 5: Azure Analysis ==========
        azure_step = AzureAnalysisStep(doc_service)
        result = await azure_step.execute(file_bytes, debugger)
        
        if not result:
            return ProcessedReceipt(
                success=False,
                data=None,
                validation=None,
                location=None,
                debug_session_id=debugger.session_id if debugger else None
            )
        
        # ========== Step 7: LLM Enhancement (Optional) ==========
        if request.enable_llm_enhancement:
            llm_step = LLMEnhancementStep()
            result = await llm_step.execute(
                result,
                original_uncropped_bytes,
                request.extract_location,
                debugger
            )
        else:
            print("Step 7️⃣: LLM Enhancement disabled - using Azure-only results")
            if debugger:
                debugger.save_json({
                    "llm_enhancement": "disabled",
                    "using": "azure_only"
                }, "06_llm_enhancement_disabled")
        
        # Merge Metadata Analysis with LLM Analysis (if present)
        llm_analysis = result.get('forgery_analysis')
        
        if llm_analysis and llm_analysis.get('is_suspicious') is not None:
             # LLM Detection Run
             visual_risk = llm_analysis.get('risk_score', 0.0)
             metadata_risk = metadata_analysis.get('risk_score', 0.0)
             
             # Maximize risk
             combined_risk = max(visual_risk, metadata_risk)
             
             # Combine flags
             combined_flags = metadata_analysis.get('flags', [])
             if llm_analysis.get('reason'):
                 combined_flags.append(f"Visual Analysis: {llm_analysis['reason']}")
                 
             result['forgery_analysis'] = {
                 "is_suspicious": combined_risk > 0.6,
                 "risk_score": combined_risk,
                 "flags": combined_flags,
                 "details": {
                     "metadata": metadata_analysis,
                     "visual": llm_analysis
                 }
             }
        else:
            # Only Metadata Analysis available (LLM disabled or failed)
            result['forgery_analysis'] = {
                 "is_suspicious": False, # Passed early check
                 "risk_score": metadata_analysis.get('risk_score', 0.0),
                 "flags": metadata_analysis.get('flags', []),
                 "details": {
                     "metadata": metadata_analysis
                 }
            }
        
        # ========== Step 8: Enhanced Validation ==========
        print("Step 8️⃣: Enhanced validation...")
        validation_service = EnhancedValidationService()
        
        # Track which sources were used
        sources_used = ["azure"]
        if result.get('fields', {}).get('MerchantName', {}).get('source') == 'llm_vision':
            sources_used.append("llm_vision")
        if result.get('metadata', {}).get('google_places_match'):
            sources_used.append("google_places")
        if request.enable_llm_enhancement:
            sources_used.append("llm_enhancement")
        
        validation = validation_service.validate_receipt(
            azure_result=result,
            sources_used=sources_used,
            start_time=start_time
        )
        
        print(f"  ✓ Validation: {validation.is_valid_receipt}")
        print(f"  ✓ Confidence: {validation.overall_confidence:.2%}")
        
        if debugger:
            debugger.save_json(validation.dict(), "07_validation_result")
        
        # ========== Step 9: Return Response ==========
        debug_session_id = debugger.session_id if debugger and debugger.enabled else None
        if debugger:
            print(f"🐛 Debug files saved to: {debugger.output_dir}")
        
        return ProcessedReceipt(
            success=True,
            data=result,
            validation=validation,
            location=None,
            debug_session_id=debug_session_id
        )
        
    except Exception as e:
        print(f"❌ Error in analyze_receipt: {str(e)}")
        import traceback
        traceback.print_exc()
        if debugger:
            debugger.save_json({"error": str(e), "type": type(e).__name__}, "99_error")
        raise HTTPException(status_code=400, detail=str(e))
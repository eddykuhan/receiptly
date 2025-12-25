from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Literal, List
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.validation_service import EnhancedValidationService
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
        
        # ========== Step 6: Location Candidates (Optional - Currently Disabled) ==========
        # NOTE: This step is disabled by default as location extraction is now consolidated
        # into Step 7 (LLMEnhancementStep) for cost optimization. Uncomment below to enable
        # separate location candidate collection from multiple sources.
        #
        # location_step = LocationCandidatesStep()
        # candidates = await location_step.execute(
        #     result,
        #     original_uncropped_bytes,
        #     debugger
        # )
        # selected_candidate = location_step.select_best_candidate(candidates)
        # print(f"  ✓ Selected location: {selected_candidate.get('store_name')}")
        
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
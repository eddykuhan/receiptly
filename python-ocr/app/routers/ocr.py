from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Literal
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.easyocr_service import EasyOCRService
from ..services.receipt_detector import ReceiptDetector
from ..services.azure_receipt_detector import AzureReceiptDetector
from ..services.store_name_extractor import StoreNameExtractor
from ..utils.image_utils import download_image
from ..utils.debug import ImageDebugger, enable_debug, disable_debug
from ..core.config import get_settings

router = APIRouter()


def get_easyocr_service() -> EasyOCRService:
    """Factory function to create EasyOCRService with debug mode from settings."""
    settings = get_settings()
    return EasyOCRService(debug_mode=settings.DEBUG_TESSERACT)


class AnalyzeRequest(BaseModel):
    """Request model for receipt analysis."""
    image_url: HttpUrl
    extract_location: bool = True  # Flag to enable/disable location extraction
    auto_crop: bool = True  # Flag to enable/disable automatic receipt cropping
    crop_method: Literal["opencv", "azure_layout"] = "azure_layout"  # Cropping method


@router.post("/analyze")
async def analyze_receipt(
    request: AnalyzeRequest,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
    easyocr_service: EasyOCRService = Depends(get_easyocr_service)
) -> Dict[str, Any]:
    """
    Analyze a receipt image from a URL and return structured data with store location.
    
    Uses:
    - Azure Layout model OR OpenCV for receipt boundary detection (optional)
    - Azure Document Intelligence for structured receipt data extraction
    - EasyOCR for store location/address extraction (fallback if Azure fails)
    
    Args:
        request: Request containing the image URL and extraction options
        doc_service: Azure Document Intelligence service instance
        easyocr_service: EasyOCR service instance
        
    Returns:
        Dictionary containing:
        - success: bool
        - data: Raw Azure Document Intelligence analysis
        - location: Extracted store location information (if enabled)
        - validation: Validation results (is_valid_receipt, confidence, message)
    """
    try:
        print(f"Received analyze request. Image URL: {request.image_url}")
        print(f"Auto-crop: {request.auto_crop}, Method: {request.crop_method if request.auto_crop else 'N/A'}")
        
        # Initialize debugger if enabled
        settings = get_settings()
        debug_enabled = settings.DEBUG_IMAGE_PROCESSING
        debugger = ImageDebugger(enabled=debug_enabled) if debug_enabled else None
        
        if debugger:
            debugger.start_session()
            print(f"🐛 Debug mode enabled. Session: {debugger.session_id}")
        
        # Step 1: Download image once
        print("Downloading image...")
        file_bytes = await download_image(str(request.image_url))
        print(f"Downloaded {len(file_bytes)} bytes")
        print("Debugging output initialized.", debugger)
        if debugger:
            debugger.save_image(file_bytes, "01_original", {
                "url": str(request.image_url),
                "size_bytes": len(file_bytes)
            })
        
        # Step 2: Auto-crop to receipt boundary (if enabled)
        boundary_info = None
        if request.auto_crop:
            if request.crop_method == "azure_layout":
                print("Using Azure Document Intelligence Layout model for boundary detection...")
                try:
                    azure_detector = AzureReceiptDetector()
                    file_bytes, boundary_info = await azure_detector.detect_and_crop(file_bytes)
                    print(f"After Azure Layout cropping: {len(file_bytes)} bytes")
                    
                    if debugger:
                        debugger.save_image(file_bytes, "02_cropped_azure", {
                            "method": "azure_layout",
                            "size_bytes": len(file_bytes),
                            "boundary_info": boundary_info
                        })
                except Exception as e:
                    print(f"Azure Layout detection failed: {str(e)}")
                    print("Falling back to OpenCV detection...")
                    detector = ReceiptDetector()
                    file_bytes = detector.detect_and_crop(file_bytes)
                    print(f"After OpenCV cropping: {len(file_bytes)} bytes")
                    
                    if debugger:
                        debugger.save_image(file_bytes, "02_cropped_opencv_fallback", {
                            "method": "opencv_fallback",
                            "size_bytes": len(file_bytes),
                            "error": str(e)
                        })
            else:
                print("Using OpenCV for boundary detection...")
                detector = ReceiptDetector()
                file_bytes = detector.detect_and_crop(file_bytes)
                print(f"After cropping: {len(file_bytes)} bytes")

                if debugger:
                    debugger.save_image(file_bytes, "02_cropped_opencv", {
                        "method": "opencv",
                        "size_bytes": len(file_bytes)
                    })
        
        # Step 3: Store original bytes for potential EasyOCR fallback later
        # We don't run EasyOCR yet - only if Azure fails to extract merchant info
        location_data = None
        
        # Step 4: Preprocess image for Azure
        print("Preprocessing image...")
        processed_bytes = doc_service.preprocessor.process(file_bytes)
        print(f"Image preprocessing complete. Output: {len(processed_bytes)} bytes")

        if debugger:
            debugger.save_image(processed_bytes, "04_preprocessed_for_azure", {
                "size_bytes": len(processed_bytes),
                "preprocessor": doc_service.preprocessor.__class__.__name__
            })
        
        # Step 5: Send preprocessed image to Azure Document Intelligence
        print("Analyzing with Azure Document Intelligence...")
        receipt = await doc_service._analyze_document(processed_bytes)
        
        if not receipt:
            if debugger:
                debugger.save_json({"error": "No receipt data found"}, "05_azure_result")
            return {
                "success": False,
                "error": "No receipt data found",
                "location": location_data
            }
        
        # Convert to dict
        result = receipt.to_dict()
        
        if debugger:
            debugger.save_json(result, "05_azure_result", {
                "merchant_name": result.get("merchant_name"),
                "merchant_address": result.get("merchant_address")
            })
        
        # Step 6: Override Azure's merchant data with EasyOCR if Azure failed or has low confidence
        # Priority: Azure first, EasyOCR only as fallback
        if request.extract_location:
            result = override_merchant_data_with_easyocr(
                result, 
                easyocr_service, 
                file_bytes,
                debugger
            )
        else:
            # Even if extraction was disabled, try fallback if Azure has missing/low-confidence merchant data
            result = override_merchant_data_with_easyocr(
                result, 
                easyocr_service, 
                file_bytes,
                debugger
            )
        
        if debugger:
            debugger.save_json(result, "06_final_result_after_override", {
                "merchant_name": result.get("merchant_name"),
                "merchant_address": result.get("merchant_address"),
                "override_applied": location_data and location_data.get('success', False)
            })
        
        # Step 7: Validate if it's actually a receipt
        validation = validate_receipt_confidence(result)
        
        print(f"Analysis completed. Validation: {validation['is_valid_receipt']}, Confidence: {validation['confidence']}")
        
        if debugger:
            debugger.save_json(validation, "07_validation_result")
        
        response = {
            "success": True,
            "data": result,
            "validation": validation
        }
        
        # Add location data if extracted
        if location_data:
            response["location"] = location_data
        
        # Add debug session info
        if debugger:
            response["debug"] = {
                "session_id": debugger.session_id,
                "output_dir": debugger.output_dir
            }
            print(f"🐛 Debug files saved to: {debugger.output_dir}")
        
        return response
        
    except Exception as e:
        print(f"Error in analyze_receipt: {str(e)}")
        if debugger:
            debugger.save_json({"error": str(e), "type": type(e).__name__}, "99_error")
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


def override_merchant_data_with_easyocr(
    azure_result: Dict[str, Any],
    easyocr_service: 'EasyOCRService',
    image_bytes: bytes = None,
    debugger = None
) -> Dict[str, Any]:
    """
    Override Azure Document Intelligence merchant/store fields with EasyOCR data.
    
    **Priority Logic:**
    1. Azure results are preferred (highest priority)
    2. EasyOCR is only used as fallback if:
       - Azure MerchantName is empty/null OR confidence < 0.5
       - Azure MerchantAddress is empty/null OR confidence < 0.5
    
    This ensures we trust Azure's specialized receipt model first, 
    and only use EasyOCR when Azure fails or is uncertain.
    
    Args:
        azure_result: Azure Document Intelligence result dictionary
        easyocr_service: EasyOCR service instance
        image_bytes: Original image bytes for EasyOCR extraction
        debugger: Optional debugger instance
        
    Returns:
        Modified azure_result with merchant data (Azure preferred, EasyOCR as fallback)
    """
    # Azure receipt structure typically has 'fields' with merchant info
    if 'fields' not in azure_result:
        azure_result['fields'] = {}
    
    fields = azure_result['fields']
    
    # Helper function to check if Azure field is valid and confident
    def is_azure_field_valid(field_name: str, min_confidence: float = 0.5) -> bool:
        """Check if Azure extracted a valid field with sufficient confidence."""
        field = fields.get(field_name, {})
        
        if not isinstance(field, dict):
            return False
        
        value = field.get('value', '')
        confidence = field.get('confidence', 0.0)
        
        # Check if value exists and is not empty
        if not value or (isinstance(value, str) and len(value.strip()) < 2):
            return False
        
        # Check confidence threshold
        if confidence < min_confidence:
            return False
        
        return True
    
    # Check Azure's merchant name and address
    azure_merchant_valid = is_azure_field_valid('MerchantName')
    azure_address_valid = is_azure_field_valid('MerchantAddress')
    
    print(f"  Azure MerchantName valid: {azure_merchant_valid}")
    print(f"  Azure MerchantAddress valid: {azure_address_valid}")
    
    # Determine if we need EasyOCR fallback
    need_easyocr_merchant = not azure_merchant_valid
    need_easyocr_address = not azure_address_valid
    
    # Only run EasyOCR if needed
    easyocr_location = None
    if (need_easyocr_merchant or need_easyocr_address) and image_bytes:
        print("  → Running EasyOCR fallback extraction...")
        try:
            easyocr_result = easyocr_service.extract_location_from_bytes(image_bytes)
            
            if debugger:
                debugger.save_json(easyocr_result, "03_easyocr_extraction", {
                    "triggered_by": "azure_missing_or_low_confidence"
                })
            
            if easyocr_result and easyocr_result.get('success'):
                easyocr_location = easyocr_result.get('location', {})
                print(f"  ✓ EasyOCR extraction successful (confidence: {easyocr_location.get('confidence', 0):.2f})")
            else:
                print(f"  ⚠️ EasyOCR extraction failed: {easyocr_result.get('error', 'unknown error')}")
        except Exception as e:
            print(f"  ⚠️ EasyOCR extraction error: {str(e)}")
    
    # Helper function to validate text isn't gibberish
    def is_valid_text(text: str, max_length: int = 200) -> bool:
        """Check if text is valid (not gibberish or too long)."""
        if not text or not isinstance(text, str):
            return False
        
        # Length check
        if len(text) > max_length:
            return False
        
        # Check for reasonable letter ratio
        letter_count = sum(c.isalpha() for c in text)
        special_count = sum(not c.isalnum() and not c.isspace() for c in text)
        total = len(text)
        
        if total == 0:
            return False
        
        letter_ratio = letter_count / total
        special_ratio = special_count / total
        
        # Text should be at least 30% letters and less than 40% special chars
        if letter_ratio < 0.3 or special_ratio > 0.4:
            return False
        
        # Check for words (should have at least one word of 3+ letters)
        words = text.split()
        valid_words = [w for w in words if len(w) >= 3 and any(c.isalpha() for c in w)]
        if len(valid_words) == 0:
            return False
        
        return True
    
    # Initialize StoreNameExtractor for fuzzy matching
    extractor = StoreNameExtractor()
    
    # ========== Handle MerchantName ==========
    merchant_name_set = False
    
    # Priority 1: Keep Azure's result if valid
    if azure_merchant_valid:
        azure_merchant = fields.get('MerchantName', {})
        azure_value = azure_merchant.get('value', '')
        print(f"  ✓ Keeping Azure MerchantName: {azure_value}")
        merchant_name_set = True
    
    # Priority 2: Use EasyOCR if Azure failed
    if not merchant_name_set and easyocr_location and easyocr_location.get('store_name'):
        store_name = easyocr_location['store_name']
        if is_valid_text(store_name, max_length=100):
            fields['MerchantName'] = {
                'type': 'string',
                'value': store_name,
                'content': store_name,
                'confidence': easyocr_location.get('confidence', 0.0),
                'source': 'easyocr_fallback'
            }
            print(f"  → Overriding MerchantName with EasyOCR: {store_name}")
            merchant_name_set = True
        else:
            print(f"  ⚠️ Skipping EasyOCR MerchantName - invalid text detected")
    
    # Priority 3: Fallback Heuristics from StoreNameExtractor
    if not merchant_name_set and image_bytes:
        try:
            fallback_result = extractor.extract_from_full_image(image_bytes)
            if fallback_result and fallback_result.get('store_name'):
                fallback_name = fallback_result['store_name']
                fallback_confidence = fallback_result.get('confidence', 0.0)
                fallback_method = fallback_result.get('method', 'unknown')
                
                fields['MerchantName'] = {
                    'type': 'string',
                    'value': fallback_name,
                    'content': fallback_name,
                    'confidence': fallback_confidence,
                    'source': f'fallback_{fallback_method}'
                }
                print(f"  ✓ Fallback extraction successful: {fallback_name} (method: {fallback_method})")
                merchant_name_set = True
        except Exception as e:
            print(f"  ⚠️ Store name extraction failed: {str(e)}")
    
    # FINAL STEP: Fuzzy Match Correction
    # Regardless of source, try to match against known chains
    current_merchant = fields.get('MerchantName', {})
    current_value = current_merchant.get('value', '') if isinstance(current_merchant, dict) else str(current_merchant)
    
    if current_value and len(current_value.strip()) >= 2:
        print(f"  🔍 Checking '{current_value}' against known chains...")
        fuzzy_match = extractor.find_best_match(current_value)
        
        if fuzzy_match:
            canonical_name = fuzzy_match['store_name']
            confidence = fuzzy_match['confidence']
            print(f"  ✨ Fuzzy match found! Correcting '{current_value}' -> '{canonical_name}' (confidence: {confidence:.2f})")
            
            fields['MerchantName'] = {
                'type': 'string',
                'value': canonical_name,
                'content': canonical_name,
                'confidence': max(current_merchant.get('confidence', 0.0), confidence),
                'source': f"{current_merchant.get('source', 'unknown')}_fuzzy_corrected"
            }
            merchant_name_set = True
    
    # If still no merchant name, set placeholder
    if not merchant_name_set:
        fields['MerchantName'] = {
            'type': 'string',
            'value': 'Unknown Store',
            'content': 'Unknown Store',
            'confidence': 0.0,
            'source': 'placeholder',
            'requires_manual_review': True
        }
        print("  ⚠️ No store name detected - using 'Unknown Store' placeholder")
    
    # ========== Handle MerchantAddress ==========
    # Priority 1: Keep Azure's address if valid
    if azure_address_valid:
        azure_address = fields.get('MerchantAddress', {})
        azure_value = azure_address.get('value', '')
        print(f"  ✓ Keeping Azure MerchantAddress: {azure_value[:50]}...")
    
    # Priority 2: Use EasyOCR if Azure failed
    elif easyocr_location and easyocr_location.get('address'):
        address = easyocr_location['address'].upper()
        if is_valid_text(address, max_length=300):
            fields['MerchantAddress'] = {
                'type': 'string',
                'value': address,
                'content': address,
                'confidence': easyocr_location.get('confidence', 0.0),
                'source': 'easyocr_fallback'
            }
            print(f"  → Overriding MerchantAddress with EasyOCR: {address[:50]}...")
        else:
            print(f"  ⚠️ Skipping EasyOCR MerchantAddress - invalid text detected")
    
    # Add MerchantPhoneNumber if available from EasyOCR and not in Azure
    if easyocr_location and easyocr_location.get('phone'):
        phone = easyocr_location['phone']
        # Only add if Azure doesn't have it
        if not fields.get('MerchantPhoneNumber'):
            if phone and len(phone.replace('+', '').replace('-', '').replace(' ', '')) >= 7:
                fields['MerchantPhoneNumber'] = {
                    'type': 'phoneNumber',
                    'value': phone,
                    'content': phone,
                    'confidence': easyocr_location.get('confidence', 0.0),
                    'source': 'easyocr'
                }
                print(f"  → Adding MerchantPhoneNumber from EasyOCR: {phone}")
    
    # Handle TransactionDate fallback
    azure_date = fields.get('TransactionDate', {})
    azure_date_value = azure_date.get('value') if isinstance(azure_date, dict) else azure_date
    azure_date_confidence = azure_date.get('confidence', 0.0) if isinstance(azure_date, dict) else 0.0
    
    # Use EasyOCR date if Azure didn't find one or has very low confidence
    easyocr_date = easyocr_location.get('transaction_date') if easyocr_location else None
    
    if easyocr_date and (not azure_date_value or azure_date_confidence < 0.5):
        fields['TransactionDate'] = {
            'type': 'date',
            'value': easyocr_date['value'],
            'content': easyocr_date['content'],
            'confidence': easyocr_date['confidence'],
            'source': 'easyocr_fallback',
            'format_detected': easyocr_date.get('format_detected', 'unknown')
        }
        print(f"  → Adding TransactionDate from EasyOCR: {easyocr_date['value']}")
    elif azure_date_value:
        print(f"  ℹ️ Keeping Azure TransactionDate: {azure_date_value} (confidence: {azure_date_confidence:.2f})")
    else:
        print(f"  ⚠️ No transaction date detected by Azure or EasyOCR")
    
    # Add additional location metadata
    if 'metadata' not in azure_result:
        azure_result['metadata'] = {}
    
    if easyocr_location:
        azure_result['metadata']['location_extraction'] = {
            'postal_code': easyocr_location.get('postal_code'),
            'country': easyocr_location.get('country'),
            'easyocr_confidence': easyocr_location.get('confidence'),
            'extraction_strategy': 'easyocr_fallback',
            'date_extracted': easyocr_date is not None,
            'azure_merchant_valid': azure_merchant_valid,
            'azure_address_valid': azure_address_valid
        }
    
    return azure_result
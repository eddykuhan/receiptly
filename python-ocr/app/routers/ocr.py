from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Literal, List
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.easyocr_service import EasyOCRService
from ..services.receipt_detector import ReceiptDetector
from ..services.azure_receipt_detector import AzureReceiptDetector
from ..services.store_name_extractor import StoreNameExtractor
from ..services.store_location_service import StoreLocationService
from ..services.llm_client import LlmServiceClient
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
        
        # Step 6: Override Azure's merchant data with LLM-enhanced selection
        # Collects candidates from all strategies and uses LLM to select best
        if request.extract_location:
            result = await override_merchant_data_with_easyocr(
                result, 
                easyocr_service, 
                file_bytes,
                debugger
            )
        else:
            # Even if extraction was disabled, try fallback if Azure has missing/low-confidence merchant data
            result = await override_merchant_data_with_easyocr(
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


async def collect_location_candidates(
    azure_result: Dict[str, Any],
    easyocr_service: 'EasyOCRService',
    image_bytes: bytes,
    debugger = None
) -> List[Dict[str, Any]]:
    """
    Collect all possible location candidates from different OCR strategies.
    
    Returns a list of candidates with metadata for LLM selection.
    """
    candidates = []
    extractor = StoreNameExtractor()
    
    # Helper to extract field value safely
    def get_field_value(field_data, default=''):
        if isinstance(field_data, dict):
            return field_data.get('value', default)
        return str(field_data) if field_data else default
    
    fields = azure_result.get('fields', {})
    
    # Candidate 1: Azure Document Intelligence
    azure_merchant = fields.get('MerchantName', {})
    azure_address = fields.get('MerchantAddress', {})
    azure_phone = fields.get('MerchantPhoneNumber', {})
    
    azure_merchant_value = get_field_value(azure_merchant)
    azure_address_value = get_field_value(azure_address)
    azure_phone_value = get_field_value(azure_phone)
    azure_confidence = azure_merchant.get('confidence', 0.0) if isinstance(azure_merchant, dict) else 0.0
    
    if azure_merchant_value and len(azure_merchant_value.strip()) >= 2:
        candidates.append({
            "store_name": azure_merchant_value,
            "address": azure_address_value or None,
            "phone": azure_phone_value or None,
            "postal_code": None,
            "source": "azure",
            "confidence": azure_confidence,
            "metadata": {
                "method": "Azure Document Intelligence"
            }
        })
        print(f"  📋 Candidate {len(candidates)-1} (Azure): {azure_merchant_value}")
    
    # Candidate 2: EasyOCR extraction
    try:
        easyocr_result = easyocr_service.extract_location_from_bytes(image_bytes)
        if easyocr_result and easyocr_result.get('success'):
            easyocr_location = easyocr_result.get('location', {})
            easyocr_store = easyocr_location.get('store_name')
            
            if easyocr_store and len(easyocr_store.strip()) >= 2:
                candidates.append({
                    "store_name": easyocr_store,
                    "address": easyocr_location.get('address'),
                    "phone": easyocr_location.get('phone'),
                    "postal_code": easyocr_location.get('postal_code'),
                    "source": "easyocr",
                    "confidence": easyocr_location.get('confidence', 0.0),
                    "metadata": {
                        "method": "EasyOCR",
                        "country": easyocr_location.get('country')
                    }
                })
                print(f"  📋 Candidate {len(candidates)-1} (EasyOCR): {easyocr_store}")
    except Exception as e:
        print(f"  ⚠️ EasyOCR extraction failed: {str(e)}")
    
    # Candidate 3: Fallback heuristics
    try:
        fallback_result = extractor.extract_from_full_image(image_bytes)
        if fallback_result and fallback_result.get('store_name'):
            fallback_name = fallback_result['store_name']
            
            # Only add if different from existing candidates
            existing_names = [c['store_name'].lower() for c in candidates]
            if fallback_name.lower() not in existing_names:
                candidates.append({
                    "store_name": fallback_name,
                    "address": None,
                    "phone": None,
                    "postal_code": None,
                    "source": "fallback",
                    "confidence": fallback_result.get('confidence', 0.0),
                    "metadata": {
                        "method": f"Fallback {fallback_result.get('method', 'unknown')}"
                    }
                })
                print(f"  📋 Candidate {len(candidates)-1} (Fallback): {fallback_name}")
    except Exception as e:
        print(f"  ⚠️ Fallback extraction failed: {str(e)}")
    
    print(f"  ✅ Collected {len(candidates)} location candidates")
    return candidates


async def override_merchant_data_with_easyocr(
    azure_result: Dict[str, Any],
    easyocr_service: 'EasyOCRService',
    image_bytes: bytes = None,
    debugger = None
) -> Dict[str, Any]:
    """
    Override Azure Document Intelligence merchant/store fields using LLM-enhanced selection.
    
    **New Logic:**
    1. Collect location candidates from all strategies (Azure, EasyOCR, Fallback)
    2. Use LLM to select the best candidate
    3. Apply fuzzy matching correction
    4. Match against Google Places
    
    Args:
        azure_result: Azure Document Intelligence result dictionary
        easyocr_service: EasyOCR service instance
        image_bytes: Original image bytes for extraction
        debugger: Optional debugger instance
        
    Returns:
        Modified azure_result with best merchant data selected by LLM
    """
    # Azure receipt structure typically has 'fields' with merchant info
    if 'fields' not in azure_result:
        azure_result['fields'] = {}
    
    fields = azure_result['fields']
    
    # Step 1: Collect all location candidates
    print("  🔍 Collecting location candidates from all strategies...")
    candidates = await collect_location_candidates(
        azure_result,
        easyocr_service,
        image_bytes,
        debugger
    )
    
    if debugger:
        debugger.save_json(candidates, "03_location_candidates")
    
    # Step 2: Use LLM to select best candidate (if multiple)
    selected_candidate = None
    address_candidate = None
    llm_selection_result = None
    
    if len(candidates) > 1:
        print(f"  🤖 Using LLM to combine best parts from {len(candidates)} candidates...")
        try:
            llm_client = LlmServiceClient()
            llm_selection_result = await llm_client.select_best_location(candidates)
            
            if llm_selection_result:
                store_idx = llm_selection_result.get('best_store_name_index', 0)
                address_idx = llm_selection_result.get('best_address_index', store_idx)
                reasoning = llm_selection_result.get('reasoning', 'No reasoning provided')
                llm_confidence = llm_selection_result.get('confidence', 0.5)
                
                selected_candidate = candidates[store_idx]
                address_candidate = candidates[address_idx] if address_idx != store_idx else None
                
                print(f"  ✨ LLM combined data:")
                print(f"     Store Name from: Candidate {store_idx} ({candidates[store_idx]['source']})")
                if address_candidate:
                    print(f"     Address from: Candidate {address_idx} ({candidates[address_idx]['source']})")
                print(f"     Reasoning: {reasoning}")
                print(f"     LLM Confidence: {llm_confidence:.2f}")
                
                if debugger:
                    debugger.save_json(llm_selection_result, "04_llm_selection")
            else:
                # Fallback to highest confidence for store name
                store_idx = max(range(len(candidates)), key=lambda i: candidates[i].get("confidence", 0.0))
                selected_candidate = candidates[store_idx]
                address_candidate = None # No separate address candidate in fallback
                print(f"  ⚠️ LLM selection failed, using highest confidence candidate {store_idx} for all fields")
        except Exception as e:
            print(f"  ⚠️ LLM selection error: {str(e)}")
            # Fallback to highest confidence for store name
            store_idx = max(range(len(candidates)), key=lambda i: candidates[i].get("confidence", 0.0))
            selected_candidate = candidates[store_idx]
            address_candidate = None # No separate address candidate in fallback
            print(f"  ⚠️ Using fallback: highest confidence candidate {store_idx} for all fields")
    elif len(candidates) == 1:
        selected_candidate = candidates[0]
        print(f"  ℹ️ Only one candidate available, using: {selected_candidate['source']}")
    else:
        print("  ⚠️ No location candidates found")
    
    # Step 3: Apply combined data to fields
    merchant_name_set = False
    
    if selected_candidate:
        # Use LLM-parsed values if available, otherwise use candidate values
        if llm_selection_result:
            store_name = llm_selection_result.get('parsed_store_name') or selected_candidate.get('store_name')
            # If LLM provided parsed_location, use it; otherwise check address_candidate
            parsed_location = llm_selection_result.get('parsed_location')
            if parsed_location:
                address = parsed_location
            elif address_candidate:
                # Use address from different candidate
                address = address_candidate.get('address')
            else:
                address = selected_candidate.get('address')
        else:
            store_name = selected_candidate.get('store_name')
            address = selected_candidate.get('address')
        
        # Combine phone and postal from either candidate
        phone = selected_candidate.get('phone') or (address_candidate.get('phone') if address_candidate else None)
        postal_code = selected_candidate.get('postal_code') or (address_candidate.get('postal_code') if address_candidate else None)
        source = selected_candidate.get('source')
        confidence = selected_candidate.get('confidence', 0.0)
        
        # Set MerchantName
        if store_name:
            fields['MerchantName'] = {
                'type': 'string',
                'value': store_name,
                'content': store_name,
                'confidence': confidence,
                'source': f'{source}_llm_parsed' if llm_selection_result and llm_selection_result.get('parsed_store_name') else f'{source}_llm_selected' if llm_selection_result else source
            }
            merchant_name_set = True
            print(f"  ✓ Set MerchantName: {store_name}")
            if llm_selection_result and llm_selection_result.get('parsed_store_name'):
                print(f"     (LLM parsed from: {selected_candidate.get('store_name')})")
        
        # Set MerchantAddress if available
        if address:
            address_source = address_candidate.get('source') if address_candidate else source
            fields['MerchantAddress'] = {
                'type': 'string',
                'value': address,
                'content': address,
                'confidence': address_candidate.get('confidence', confidence) if address_candidate else confidence,
                'source': f'{address_source}_llm_parsed' if llm_selection_result and llm_selection_result.get('parsed_location') else f'{address_source}_llm_combined' if address_candidate else source
            }
            print(f"  ✓ Set MerchantAddress: {address[:50]}...")
            if llm_selection_result and llm_selection_result.get('parsed_location'):
                print(f"     (LLM extracted location from mixed data)")
            elif address_candidate:
                print(f"     (Combined from {address_source} candidate)")
        
        # Set MerchantPhoneNumber if available
        if phone and not fields.get('MerchantPhoneNumber'):
            fields['MerchantPhoneNumber'] = {
                'type': 'phoneNumber',
                'value': phone,
                'content': phone,
                'confidence': confidence,
                'source': f'{source}_llm_selected' if llm_selection_result else source
            }
            print(f"  ✓ Set MerchantPhoneNumber: {phone}")
    
    # Step 4: Fuzzy Match Correction
    # Initialize StoreNameExtractor for fuzzy matching
    extractor = StoreNameExtractor()
    
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
    
    # ========== Google Places Matching ==========
    # Try to match the extracted store name against Google Places database
    # This will replace OCR-extracted address with verified Google Places data
    google_places_match = None
    try:
        location_service = StoreLocationService()
        
        # Get current merchant name and address for matching
        current_merchant = fields.get('MerchantName', {})
        current_name = current_merchant.get('value', '') if isinstance(current_merchant, dict) else str(current_merchant)
        
        # Get OCR-extracted data for matching signals from selected candidate
        ocr_address = selected_candidate.get('address') if selected_candidate else None
        ocr_phone = selected_candidate.get('phone') if selected_candidate else None
        ocr_postal = selected_candidate.get('postal_code') if selected_candidate else None
        
        # Also check Azure's data (extract string value from dict)
        azure_address = fields.get('MerchantAddress', {})
        if isinstance(azure_address, dict) and azure_address.get('value'):
            addr_value = azure_address.get('value')
            if isinstance(addr_value, str):
                ocr_address = ocr_address or addr_value
        
        azure_phone = fields.get('MerchantPhoneNumber', {})
        if isinstance(azure_phone, dict) and azure_phone.get('value'):
            phone_value = azure_phone.get('value')
            if isinstance(phone_value, str):
                ocr_phone = ocr_phone or phone_value
        
        # Ensure all values are strings or None (not dicts or other types)
        ocr_address = str(ocr_address) if ocr_address and not isinstance(ocr_address, str) else ocr_address
        ocr_phone = str(ocr_phone) if ocr_phone and not isinstance(ocr_phone, str) else ocr_phone
        ocr_postal = str(ocr_postal) if ocr_postal and not isinstance(ocr_postal, str) else ocr_postal
        
        # Try to find best match
        if current_name and current_name != 'Unknown Store':
            print(f"  🗺️ Searching Google Places for: {current_name}")
            google_places_match = location_service.find_best_match(
                store_name=current_name,
                partial_address=ocr_address,
                phone=ocr_phone,
                postal_code=ocr_postal,
                min_confidence=0.70  # Only use matches with 70%+ confidence
            )
            
            if google_places_match:
                confidence = google_places_match['confidence']
                branch = google_places_match['branch_name']
                reason = google_places_match['match_reason']
                
                print(f"  ✅ Google Places match found!")
                print(f"     Branch: {branch}")
                print(f"     Confidence: {confidence:.2f}")
                print(f"     Reason: {reason}")
                
                # Replace address with Google Places data (if confidence is high enough)
                if confidence >= 0.80:
                    fields['MerchantAddress'] = {
                        'type': 'string',
                        'value': google_places_match['address'],
                        'content': google_places_match['address'],
                        'confidence': confidence,
                        'source': 'google_places'
                    }
                    print(f"  → Replaced address with Google Places data")
                    
                    # Add phone if not already present
                    if google_places_match.get('phone') and not fields.get('MerchantPhoneNumber'):
                        fields['MerchantPhoneNumber'] = {
                            'type': 'phoneNumber',
                            'value': google_places_match['phone'],
                            'content': google_places_match['phone'],
                            'confidence': confidence,
                            'source': 'google_places'
                        }
                        print(f"  → Added phone from Google Places: {google_places_match['phone']}")
                else:
                    print(f"  ℹ️ Google Places match confidence ({confidence:.2f}) below threshold (0.80)")
                    print(f"  ℹ️ Keeping OCR-extracted address")
            else:
                print(f"  ℹ️ No Google Places match found for '{current_name}'")
        
    except Exception as e:
        print(f"  ⚠️ Google Places matching error: {str(e)}")
        # Continue without Google Places data
    
    # Transaction date is handled by Azure - no additional processing needed for location selection
    azure_date = fields.get('TransactionDate', {})
    azure_date_value = azure_date.get('value') if isinstance(azure_date, dict) else azure_date
    if azure_date_value:
        print(f"  ℹ️ TransactionDate from Azure: {azure_date_value}")
    
    # Add additional location metadata
    if 'metadata' not in azure_result:
        azure_result['metadata'] = {}
    
    if selected_candidate:
        azure_result['metadata']['location_extraction'] = {
            'postal_code': selected_candidate.get('postal_code'),
            'selected_source': selected_candidate.get('source'),
            'selected_confidence': selected_candidate.get('confidence'),
            'extraction_strategy': 'llm_enhanced_selection',
            'llm_selection_used': llm_selection_result is not None
        }
        
        if llm_selection_result:
            azure_result['metadata']['llm_selection'] = {
                'reasoning': llm_selection_result.get('reasoning'),
                'confidence': llm_selection_result.get('confidence'),
                'num_candidates': len(candidates)
            }
    
    # Add Google Places metadata if match was found
    if google_places_match:
        azure_result['metadata']['google_places_match'] = True
        azure_result['metadata']['match_confidence'] = google_places_match['confidence']
        azure_result['metadata']['matched_branch'] = google_places_match['branch_name']
        azure_result['metadata']['match_reason'] = google_places_match['match_reason']
        azure_result['metadata']['latitude'] = google_places_match['latitude']
        azure_result['metadata']['longitude'] = google_places_match['longitude']
        
        # Add rating info if available
        if google_places_match.get('rating'):
            azure_result['metadata']['google_rating'] = google_places_match['rating']
            azure_result['metadata']['google_total_ratings'] = google_places_match.get('total_ratings', 0)
    else:
        azure_result['metadata']['google_places_match'] = False
    
    return azure_result
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Literal
from ..services.document_intelligence import DocumentIntelligenceService
from ..services.tesseract_ocr import TesseractOCRService
from ..services.receipt_detector import ReceiptDetector
from ..services.azure_receipt_detector import AzureReceiptDetector
from ..services.store_name_extractor import StoreNameExtractor
from ..utils.image_utils import download_image

router = APIRouter()


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
    tesseract_service: TesseractOCRService = Depends(TesseractOCRService)
) -> Dict[str, Any]:
    """
    Analyze a receipt image from a URL and return structured data with store location.
    
    Uses:
    - Azure Layout model OR OpenCV for receipt boundary detection (optional)
    - Azure Document Intelligence for structured receipt data extraction
    - Tesseract OCR for store location/address extraction
    
    Args:
        request: Request containing the image URL and extraction options
        doc_service: Azure Document Intelligence service instance
        tesseract_service: Tesseract OCR service instance
        
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
        
        # Step 1: Download image once
        print("Downloading image...")
        file_bytes = await download_image(str(request.image_url))
        print(f"Downloaded {len(file_bytes)} bytes")
        
        # Step 2: Auto-crop to receipt boundary (if enabled)
        boundary_info = None
        if request.auto_crop:
            if request.crop_method == "azure_layout":
                print("Using Azure Document Intelligence Layout model for boundary detection...")
                try:
                    azure_detector = AzureReceiptDetector()
                    file_bytes, boundary_info = await azure_detector.detect_and_crop(file_bytes)
                    print(f"After Azure Layout cropping: {len(file_bytes)} bytes")
                except Exception as e:
                    print(f"Azure Layout detection failed: {str(e)}")
                    print("Falling back to OpenCV detection...")
                    detector = ReceiptDetector()
                    file_bytes = detector.detect_and_crop(file_bytes)
                    print(f"After OpenCV cropping: {len(file_bytes)} bytes")
            else:
                print("Using OpenCV for boundary detection...")
                detector = ReceiptDetector()
                file_bytes = detector.detect_and_crop(file_bytes)
                print(f"After cropping: {len(file_bytes)} bytes")
        
        # Step 3: Extract store location using Tesseract (if requested)
        location_data = None
        if request.extract_location:
            print("Extracting store location with Tesseract OCR...")
            location_data = tesseract_service.extract_location_from_bytes(file_bytes)
            print(f"Location extraction complete. Success: {location_data}")
        
        # Step 4: Preprocess image for Azure
        print("Preprocessing image...")
        processed_bytes = doc_service.preprocessor.process(file_bytes)
        print(f"Image preprocessing complete. Output: {len(processed_bytes)} bytes")
        
        # Step 5: Send preprocessed image to Azure Document Intelligence
        print("Analyzing with Azure Document Intelligence...")
        receipt = await doc_service._analyze_document(processed_bytes)
        
        if not receipt:
            return {
                "success": False,
                "error": "No receipt data found",
                "location": location_data
            }
        
        # Convert to dict
        result = receipt.to_dict()
        
        # Step 6: Override Azure's merchant data with Tesseract's more accurate location data
        # Pass original image bytes for fallback extraction if needed
        if location_data and location_data.get('success'):
            result = override_merchant_data_with_tesseract(result, location_data, file_bytes)
            print("✓ Overridden Azure merchant data with Tesseract location data")
        else:
            # Even if Tesseract extraction was disabled/failed, try fallback if Azure has no merchant name
            result = override_merchant_data_with_tesseract(result, {'success': False}, file_bytes)
        
        # Step 7: Validate if it's actually a receipt
        validation = validate_receipt_confidence(result)
        
        print(f"Analysis completed. Validation: {validation['is_valid_receipt']}, Confidence: {validation['confidence']}")
        
        response = {
            "success": True,
            "data": result,
            "validation": validation
        }
        
        # Add location data if extracted
        if location_data:
            response["location"] = location_data
        
        return response
        
    except Exception as e:
        print(f"Error in analyze_receipt: {str(e)}")
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


def override_merchant_data_with_tesseract(
    azure_result: Dict[str, Any],
    tesseract_location: Dict[str, Any],
    image_bytes: bytes = None
) -> Dict[str, Any]:
    """
    Override Azure Document Intelligence merchant/store fields with Tesseract OCR data.
    Tesseract's location extraction is often more accurate for store names and addresses.
    Validates extracted text before overriding to prevent gibberish.
    Uses fallback extraction if both Azure and Tesseract fail.
    
    Args:
        azure_result: Azure Document Intelligence result dictionary
        tesseract_location: Tesseract location extraction result
        image_bytes: Original image bytes for fallback extraction
        
    Returns:
        Modified azure_result with overridden merchant data (only if valid)
    """
    if not tesseract_location.get('success') or not tesseract_location.get('location'):
        return azure_result
    
    location = tesseract_location['location']
    
    # Azure receipt structure typically has 'fields' with merchant info
    if 'fields' not in azure_result:
        azure_result['fields'] = {}
    
    fields = azure_result['fields']
    
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
    
    # Override MerchantName with Tesseract's store_name (only if valid)
    merchant_name_set = False
    
    if location.get('store_name'):
        store_name = location['store_name']
        if is_valid_text(store_name, max_length=100):
            fields['MerchantName'] = {
                'type': 'string',
                'value': store_name,
                'content': store_name,
                'confidence': location.get('confidence', 0.0),
                'source': 'tesseract'  # Mark source for debugging
            }
            print(f"  → Overriding MerchantName: {store_name}")
            merchant_name_set = True
        else:
            print(f"  ⚠️  Skipping MerchantName - invalid text detected (gibberish or too long)")
            # Keep Azure's merchant name if Tesseract returned gibberish
    
    # Fallback: If both Azure and Tesseract failed to get merchant name, try full-image extraction
    if not merchant_name_set and image_bytes:
        # Check if Azure also doesn't have a valid merchant name
        azure_merchant = fields.get('MerchantName', {})
        azure_value = azure_merchant.get('value', '') if isinstance(azure_merchant, dict) else str(azure_merchant)
        
        if not azure_value or len(azure_value.strip()) < 2:
            print("  ℹ️  Both Azure and Tesseract failed to detect store name, trying fallback extraction...")
            try:
                extractor = StoreNameExtractor()
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
                    print(f"  ✓ Fallback extraction successful: {fallback_name} (method: {fallback_method}, confidence: {fallback_confidence:.2f})")
                    merchant_name_set = True
                else:
                    print("  ⚠️  Fallback extraction did not find a valid store name")
            except Exception as e:
                print(f"  ⚠️  Fallback extraction failed: {str(e)}")
    
    # If still no merchant name, set a placeholder for manual review
    if not merchant_name_set:
        azure_merchant = fields.get('MerchantName', {})
        azure_value = azure_merchant.get('value', '') if isinstance(azure_merchant, dict) else str(azure_merchant)
        
        if not azure_value or len(azure_value.strip()) < 2:
            fields['MerchantName'] = {
                'type': 'string',
                'value': 'Unknown Store',
                'content': 'Unknown Store',
                'confidence': 0.0,
                'source': 'placeholder',
                'requires_manual_review': True
            }
            print("  ⚠️  No store name detected - using 'Unknown Store' placeholder")

    
    # Override MerchantAddress with Tesseract's address (only if valid)
    if location.get('address'):
        address = location['address']
        if is_valid_text(address, max_length=300):
            fields['MerchantAddress'] = {
                'type': 'string',
                'value': address,
                'content': address,
                'confidence': location.get('confidence', 0.0),
                'source': 'tesseract'
            }
            print(f"  → Overriding MerchantAddress: {address}")
        else:
            print(f"  ⚠️  Skipping MerchantAddress - invalid text detected (gibberish or too long)")
            # Keep Azure's address if Tesseract returned gibberish
    
    # Add MerchantPhoneNumber if available and not already present
    if location.get('phone'):
        phone = location['phone']
        # Phone validation - should be mostly digits
        if phone and len(phone.replace('+', '').replace('-', '').replace(' ', '')) >= 7:
            fields['MerchantPhoneNumber'] = {
                'type': 'phoneNumber',
                'value': phone,
                'content': phone,
                'confidence': location.get('confidence', 0.0),
                'source': 'tesseract'
            }
            print(f"  → Adding MerchantPhoneNumber: {phone}")
    
    # Add additional location metadata
    if 'metadata' not in azure_result:
        azure_result['metadata'] = {}
    
    azure_result['metadata']['location_extraction'] = {
        'postal_code': location.get('postal_code'),
        'country': location.get('country'),
        'tesseract_confidence': location.get('confidence'),
        'extraction_strategy': tesseract_location.get('strategy_used')
    }
    
    return azure_result
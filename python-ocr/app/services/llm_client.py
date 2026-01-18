import httpx
from typing import List, Dict, Any, Optional
from app.core.config import get_settings
import json
from datetime import datetime, date, time


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.isoformat()
        return super().default(obj)

class LlmServiceClient:
    """Client for calling the LLM microservice."""
    
    def __init__(self, base_url: str = None):
        settings = get_settings()
        self.base_url = base_url or settings.LLM_SERVICE_URL
        self.timeout = 30.0  # 30 second timeout for LLM calls
    
    async def select_best_location(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Call LLM service to select the best location from multiple candidates.
        
        Args:
            candidates: List of location candidate dictionaries
            
        Returns:
            {
                "selected_index": int,
                "reasoning": str,
                "confidence": float
            }
            or None if the call fails
        """
        if not candidates:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/select_best_location",
                    json={"candidates": candidates}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"⚠️ LLM service call failed: {str(e)}")
            return None

    async def extract_merchant_from_image(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Call LLM service to extract merchant info from receipt image using GPT-4 Vision.
        
        Args:
            image_bytes: Receipt image data in bytes
            
        Returns:
            {
                "merchant_name": str,
                "merchant_address": str,
                "success": bool,
                "error": str (optional)
            }
            or None if the call fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for vision API
                # Send as multipart form data
                files = {"file": ("receipt.jpg", image_bytes, "image/jpeg")}
                response = await client.post(
                    f"{self.base_url}/extract_merchant",
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"⚠️ LLM vision extraction failed: {str(e)}")
            return None

    async def enhance_receipt(
        self,
        azure_result: Dict[str, Any],
        image_bytes: bytes,
        options: Optional[Dict[str, bool]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM service to enhance Azure OCR results using GPT-4 Vision.
        
        This method sends both the Azure extraction results and the original image
        to the LLM service, which uses GPT-4 Vision to:
        - Complete truncated item names
        - Add missing items Azure didn't detect
        - Remove non-product items (baskets, bags with $0.00)
        - Validate and fix quantities/prices
        - Ensure total matches item sum
        
        Args:
            azure_result: Azure Document Intelligence extraction result
            image_bytes: Original receipt image data
            options: Optional dict to control which enhancements to apply:
                {
                    "expand_item_names": True,
                    "add_missing_items": True,
                    "remove_non_products": True,
                    "fix_quantities": True,
                    "validate_prices": True,
                    "validate_total": True
                }
                If None, all enhancements are enabled by default.
        
        Returns:
            {
                "enhanced_result": {...},  # Enhanced version of azure_result
                "corrections": [
                    {
                        "field": "items[0].name",
                        "original": "MILO ACT",
                        "corrected": "MILO Activ-Go 1kg",
                        "reason": "Expanded truncated name from image",
                        "confidence": 0.95
                    }
                ],
                "overall_confidence": 0.92,
                "requires_review": False,
                "stats": {
                    "items_added": 0,
                    "items_removed": 1,
                    "corrections_made": 3
                },
                "notes": "Enhancement summary"
            }
            or None if the call fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for vision API
                # Prepare form data
                files = {"file": ("receipt.jpg", image_bytes, "image/jpeg")}
                data = {
                    "azure_result": json.dumps(azure_result, cls=DateTimeEncoder),
                    "options": json.dumps(options, cls=DateTimeEncoder) if options else None
                }
                
                response = await client.post(
                    f"{self.base_url}/enhance_receipt",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"⚠️ LLM receipt enhancement failed: {str(e)}")
            return None

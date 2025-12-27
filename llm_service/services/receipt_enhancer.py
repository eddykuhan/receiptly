"""
Receipt Enhancement Service using GPT-4 Vision.

This service takes Azure Document Intelligence OCR results plus the original receipt image
and uses LLM to:
1. Complete truncated item names
2. Add missing items that Azure didn't detect
3. Remove non-product items (baskets, bags with $0.00)
4. Validate and fix quantity/price errors
5. Ensure total matches item sum
6. Provide confidence scores for corrections
"""

import base64
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from config import get_settings


class ReceiptEnhancer:
    """Enhance Azure OCR results using GPT-4 Vision intelligence."""
    
    def __init__(self):
        """Initialize the ReceiptEnhancer."""
        settings = get_settings()
        
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in environment."
            )
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4.1"  # GPT-4 Turbo with vision
    
    def _encode_image_bytes(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def enhance_receipt(
        self,
        azure_result: Dict[str, Any],
        image_bytes: bytes,
        enhancement_options: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Enhance Azure OCR result using image analysis.
        
        Args:
            azure_result: Azure Document Intelligence extraction result
            image_bytes: Original receipt image
            enhancement_options: Which enhancements to apply (default: all)
                {
                    "expand_item_names": True,
                    "add_missing_items": True,
                    "remove_non_products": True,
                    "fix_quantities": True,
                    "validate_prices": True,
                    "validate_total": True
                }
        
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
                "requires_review": False
            }
        """
        # Default options: enable all enhancements
        options = enhancement_options or {
            "expand_item_names": True,
            "add_missing_items": True,
            "remove_non_products": True,
            "fix_quantities": True,
            "validate_prices": True,
            "validate_total": True
        }
        
        # Encode image
        base64_image = self._encode_image_bytes(image_bytes)
        
        # Create enhancement prompt
        prompt = self._create_enhancement_prompt(azure_result, options)
        
        # Call GPT-4 Vision
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a receipt data enhancement expert. Your job is to improve OCR results by analyzing the receipt image alongside the extracted data."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"  # High detail for better OCR
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent, factual responses
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = self._parse_enhancement_result(content)
            
            return result
            
        except Exception as e:
            print(f"❌ LLM enhancement failed: {str(e)}")
            # Return original result with error
            return {
                "enhanced_result": azure_result,
                "corrections": [],
                "overall_confidence": 0.0,
                "requires_review": True,
                "error": str(e)
            }
    
    def _create_enhancement_prompt(
        self,
        azure_result: Dict[str, Any],
        options: Dict[str, bool]
    ) -> str:
        """Create the enhancement prompt for GPT-4 Vision."""
        
        # Extract key fields from Azure result
        fields = azure_result.get('fields', {})
        merchant = fields.get('MerchantName', {}).get('value', 'Unknown')
        address = fields.get('MerchantAddress', {}).get('value', '')
        phone = fields.get('MerchantPhoneNumber', {}).get('value', '')
        transaction_date = fields.get('TransactionDate', {}).get('value', '')
        
        # Extract items
        items = fields.get('Items', {}).get('value', [])
        items_text = "\n".join([
            f"  - {i.get('Description', {}).get('value', 'Unknown')} | "
            f"Qty: {i.get('Quantity', {}).get('value', 1)} | "
            f"Price: ${i.get('TotalPrice', {}).get('value', 0.0):.2f}"
            for i in items
        ])
        
        total = fields.get('Total', {}).get('value', 0.0)
        
        prompt = f"""You are analyzing a receipt from "{merchant}".

**AZURE OCR EXTRACTED:**
Store: {merchant}
Address: {address or "(not extracted)"}
Phone: {phone or "(not extracted)"}
Transaction Date: {transaction_date or "(not extracted)"}

Items:
{items_text or "  (no items detected)"}

Total: ${total:.2f}

**YOUR TASK:**
Compare the Azure extraction above with the actual receipt image and:

"""
        
        if options.get("extract_location"):
            prompt += """
0. **EXTRACT STORE LOCATION**
   - Find the FULL store name as written on the receipt (may differ from Azure)
   - Extract the complete store address including street, city, state
   - Extract phone number if visible
   - Look at the header/footer of receipt for complete location info
   - Be precise: Azure may have partial/incomplete location data
"""
        
        if options.get("extract_transaction_date"):
            prompt += """
0b. **EXTRACT TRANSACTION DATE & TIME**
   - Find the complete transaction date from the receipt
   - Include time if visible (HH:MM format)
   - Check bottom of receipt - dates are often printed there
   - Format: YYYY-MM-DD HH:MM:SS (or just date if time unavailable)
   - Azure may have missed this or have incomplete data
"""
        
        if options.get("expand_item_names"):
            prompt += """
1. **EXPAND TRUNCATED ITEM NAMES**
   - Look at the receipt image for full product names
   - Azure often truncates names (e.g., "MILO ACT" → "MILO Activ-Go 1kg")
   - Complete the names based on what you see in the image
"""
        
        if options.get("add_missing_items"):
            prompt += """
2. **ADD MISSING ITEMS**
   - Check if Azure missed any items by comparing with the image
   - Some receipts have items Azure completely misses
   - Add any missing items you see in the image
"""
        
        if options.get("remove_non_products"):
            prompt += """
3. **REMOVE NON-PRODUCT ITEMS**
   - Remove items like:
     * "BASKET" with price $0.00
     * "SHOPPING BAG" with price $0.00
     * "DEPOSIT" items
   - These are not actual purchases, just receipt artifacts
"""
        
        if options.get("fix_quantities"):
            prompt += """
4. **VALIDATE QUANTITIES**
   - Check if quantities match what's shown in the image
   - Azure sometimes confuses "1x" vs "2x"
   - Correct any quantity errors you see
"""
        
        if options.get("validate_prices"):
            prompt += """
5. **VALIDATE PRICES**
   - Check for decimal errors (19.99 vs 1.99, 199.9 vs 19.99)
   - Ensure unit prices and total prices are correct
   - Flag suspicious prices (too high/low)
"""
        
        if options.get("validate_total"):
            prompt += """
6. **VALIDATE TOTAL**
   - Ensure the sum of all item prices equals the total
   - Check if Azure captured the final total (not subtotal)
   - Account for taxes, discounts if visible
"""
        
        if options.get("detect_forgery", True):
            prompt += """
7. **DETECT FORGERY / AI GENERATION**
   - Look closely for signs that this image is Fake or AI-Generated
   - Signs of AI: 
     * Gibbons/nonsensical text in logos
     * "Wobbly" or inconsistent lines/tables
     * Perfect alignment that looks unnatural
     * Impossible lighting/shadows
     * Generic/Placeholder store names (e.g. "Restaurant Name", "123 Main St")
   - Signs of Photoshop:
     * mismatched fonts
     * floating text not following paper curve
"""

        prompt += """
 
**CRITICAL RULES:**
- Only make changes you can VERIFY from the image
- Do NOT hallucinate items or data
- If something is unclear in the image, keep Azure's version
- Provide confidence scores (0.0-1.0) for each correction
- Be conservative: when in doubt, don't change

**OUTPUT FORMAT (JSON ONLY):**
```json
{
  "merchant_name": "Full Store Name",
  "merchant_address": "Complete address with street, city, state",
  "merchant_phone": "Phone number if visible",
  "transaction_datetime": "YYYY-MM-DD HH:MM:SS",
  "forgery_analysis": {
      "is_suspicious": false,
      "risk_score": 0.1,
      "reason": "Natural lighting and consistent fonts observed"
  },
  "enhanced_items": [
    {
      "name": "MILO Activ-Go 1kg",
      "quantity": 1,
      "price": 19.99,
      "confidence": 0.95
    }
  ],
  "enhanced_total": 19.99,
  "corrections": [
    {
      "field": "items[0].name",
      "original": "MILO ACT",
      "corrected": "MILO Activ-Go 1kg",
      "reason": "Expanded truncated name visible in image",
      "confidence": 0.95
    }
  ],
  "items_added": 0,
  "items_removed": 1,
  "overall_confidence": 0.92,
  "requires_review": false,
  "notes": "Removed 'BASKET' $0.00 non-product item"
}
```

Return ONLY the JSON, no other text.
"""
        
        return prompt
    
    def _parse_enhancement_result(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM response into structured result."""
        try:
            print(f"🔍 Parsing LLM response (length: {len(llm_response)} chars)")
            print(f"🔍 First 500 chars: {llm_response[:500]}")
            
            # Try to extract JSON from response
            # Handle cases where LLM wraps JSON in markdown code blocks
            llm_response = llm_response.strip()
            
            if llm_response.startswith("```json"):
                llm_response = llm_response[7:]
            if llm_response.startswith("```"):
                llm_response = llm_response[3:]
            if llm_response.endswith("```"):
                llm_response = llm_response[:-3]
            
            llm_response = llm_response.strip()
            
            print(f"🔍 After cleanup, first 300 chars: {llm_response[:300]}")
            
            result = json.loads(llm_response)
            
            print(f"🔍 Parsed JSON keys: {list(result.keys())}")
            print(f"🔍 Enhanced items in response: {len(result.get('enhanced_items', []))}")
            
            # Extract location information from LLM
            location_info = {}
            if result.get('merchant_name'):
                location_info['merchant_name'] = result['merchant_name']
                print(f"🔍 Merchant name: {result['merchant_name']}")
            if result.get('merchant_address'):
                location_info['merchant_address'] = result['merchant_address']
                print(f"🔍 Merchant address: {result['merchant_address']}")
            if result.get('merchant_phone'):
                location_info['merchant_phone'] = result['merchant_phone']
                print(f"🔍 Merchant phone: {result['merchant_phone']}")
            if result.get('transaction_datetime'):
                location_info['transaction_datetime'] = result['transaction_datetime']
                print(f"🔍 Transaction datetime: {result['transaction_datetime']}")
            
            # Convert enhanced items back to Azure format
            enhanced_result = {
                "fields": {
                    "Items": {
                        "value": [
                            {
                                "Description": {"value": item["name"]},
                                "Quantity": {"value": item["quantity"]},
                                "TotalPrice": {"value": item["price"]},
                                "confidence": item.get("confidence", 0.9)
                            }
                            for item in result.get("enhanced_items", [])
                        ]
                    },
                    "Total": {
                        "value": result.get("enhanced_total", 0.0)
                    }
                }
            }
            
            print(f"🔍 Converted items to Azure format: {len(enhanced_result['fields']['Items']['value'])} items")
            
            return {
                "enhanced_result": enhanced_result,
                "location": location_info if location_info else None,
                "corrections": result.get("corrections", []),
                "overall_confidence": result.get("overall_confidence", 0.8),
                "requires_review": result.get("requires_review", False),
                "stats": {
                    "items_added": result.get("items_added", 0),
                    "items_removed": result.get("items_removed", 0),
                    "corrections_made": len(result.get("corrections", []))
                },
                "forgery_analysis": result.get("forgery_analysis"),
                "notes": result.get("notes", "")
            }
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response: {e}")
            print(f"Response was: {llm_response[:200]}...")
            return {
                "enhanced_result": {},
                "corrections": [],
                "overall_confidence": 0.0,
                "requires_review": True,
                "error": "Failed to parse LLM response"
            }


# Singleton instance
_enhancer = None

async def enhance_receipt_data(
    azure_result: Dict[str, Any],
    image_bytes: bytes,
    options: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """
    Convenience function to enhance receipt data.
    
    Args:
        azure_result: Azure Document Intelligence result
        image_bytes: Original receipt image
        options: Enhancement options (default: all enabled)
    
    Returns:
        Enhanced receipt data with corrections
    """
    global _enhancer
    if _enhancer is None:
        _enhancer = ReceiptEnhancer()
    
    return await _enhancer.enhance_receipt(azure_result, image_bytes, options)

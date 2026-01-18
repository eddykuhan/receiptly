"""
Receipt Merchant Information Extractor using GPT-4 Vision / LLM.
Extracts merchant name and address from receipt images.
Adapted from gpt4-vision-extractor for use as a microservice.
"""

import base64
import json
from typing import Dict, Optional
from openai import AsyncOpenAI
from config import get_settings


class ReceiptMerchantExtractor:
    """Extract merchant information from receipt images using GPT-4 Vision."""
    
    def __init__(self):
        """Initialize the ReceiptMerchantExtractor."""
        settings = get_settings()
        
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in environment."
            )
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4.1"  # GPT-4 with vision capabilities
    
    def _encode_image_bytes(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string.
        
        Args:
            image_bytes: Image data in bytes.
            
        Returns:
            Base64 encoded string of the image.
        """
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def extract_merchant_info(self, image_bytes: bytes) -> Dict[str, str]:
        """
        Extract merchant name and address from receipt image bytes.
        
        Args:
            image_bytes: Receipt image data in bytes.
            
        Returns:
            Dictionary containing merchant_name and merchant_address.
        """
        # Encode image
        base64_image = self._encode_image_bytes(image_bytes)
        
        # Create the prompt for GPT-4 Vision
        prompt = """
You are a Receipt Merchant Extraction Model.

Instructions:
1. Look at the printed header of the receipt for merchant information (not security stamps or red markings).
2. Identify the actual merchant name based on:
   - Known Malaysian merchant list (Mydin, Lotus's, 99 Speedmart, Jaya Grocer, Giant, Hero Market, NSK, Watsons, Guardian, etc.)
   - Partial text in the top header
3. Ignore company registration numbers, GST IDs, site codes, cashier IDs.
4. If the address is not explicitly printed, return only the location (e.g., "Bukit Mertajam, Malaysia").
5. If the merchant name is partially occluded or unclear, infer the nearest exact match from the known list.
6. NEVER return "Not found". Always infer the most likely merchant.

7. Extract the transaction date/time from the receipt:
   - **CRITICAL**: ALWAYS scan the ENTIRE receipt from TOP to BOTTOM
   - **START by checking the VERY TOP** of the receipt (first few lines after merchant name)
   - **THEN check the VERY BOTTOM** of the receipt (last few lines, footer area)
   - Many retailers print dates at DIFFERENT locations:
     * Top-date stores: 99 Speedmart, Mydin, Giant (date in header area)
     * Bottom-date stores: Watsons, Guardian, pharmacies (date in footer area)
     * Some receipts have BOTH print date (top) and transaction date (bottom) - choose transaction date
   - Look for date stamps in these formats:
     * DD/MM/YYYY, DD-MM-YYYY, MM/DD/YYYY
     * YYYY-MM-DD, YYYY/MM/DD
     * DD MMM YYYY (e.g., "07 Dec 2024")
   - Look for time stamps: HH:MM:SS, HH:MM
   - Common labels to look for:
     * "Date:", "Time:", "Date/Time:", "Transaction Date:"
     * "Date & Time:", "Txn Date:", "Purchase Date:"
     * Sometimes just a date/time without a label near the total or at the bottom
   - Prioritize the transaction date over print date or other dates
   - If multiple dates exist, choose the one that appears to be the transaction/purchase date
   - **DO NOT skip the bottom section** - this is where many stores print the date

8. Return the date in ISO 8601 format:
   - With time: YYYY-MM-DDTHH:MM:SS (e.g., "2024-12-07T14:30:00")
   - Without time: YYYY-MM-DD (e.g., "2024-12-07")

Return JSON only:

{
  "merchantName": "",
  "merchantAddress": "",
  "transactionDateTime": ""
}

Example responses:
{
  "merchantName": "Mydin",
  "merchantAddress": "Bukit Mertajam, Penang, Malaysia",
  "transactionDateTime": "2024-12-07T14:30:00"
}

{
  "merchantName": "Watsons",
  "merchantAddress": "Sunway Pyramid, Selangor",
  "transactionDateTime": "2024-12-07"
}

{
  "merchantName": "99 Speedmart",
  "merchantAddress": "Jalan Sultan Azlan Shah, Kuala Lumpur",
  "transactionDateTime": "2024-12-07T18:45:30"
}
"""

        
        try:
            # Call GPT-4 Vision API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
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
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.2  # Lower temperature for more consistent extraction
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            print(f"[ReceiptExtractor] Extracted: {result}")
            return {
                "merchant_name": result.get("merchantName", ""),
                "merchant_address": result.get("merchantAddress", ""),
                "transaction_datetime": result.get("transactionDateTime", ""),
                "raw_response": content,
                "success": True
            }
            
        except json.JSONDecodeError as e:
            print(f"[ReceiptExtractor] Error parsing JSON response: {e}")
            print(f"[ReceiptExtractor] Raw response: {content}")
            return {
                "merchant_name": "",
                "merchant_address": "",
                "raw_response": content if 'content' in dir() else "",
                "error": str(e),
                "success": False
            }
        except Exception as e:
            print(f"[ReceiptExtractor] Error calling GPT-4 Vision API: {e}")
            return {
                "merchant_name": "",
                "merchant_address": "",
                "error": str(e),
                "success": False
            }


# Module-level instance for easy access
_extractor: Optional[ReceiptMerchantExtractor] = None


def get_extractor() -> ReceiptMerchantExtractor:
    """Get or create the receipt extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ReceiptMerchantExtractor()
    return _extractor


async def extract_merchant_from_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Extract merchant information from receipt image bytes.
    
    Convenience function for use in API routes.
    
    Args:
        image_bytes: Receipt image data in bytes.
        
    Returns:
        Dictionary containing:
        - merchant_name: Extracted merchant/store name
        - merchant_address: Extracted address/location
        - success: Boolean indicating if extraction was successful
        - error: Error message if extraction failed (optional)
    """
    extractor = get_extractor()
    return await extractor.extract_merchant_info(image_bytes)

"""
Receipt Merchant Information Extractor using GPT-4 Vision
Extracts merchant name and address from receipt images.
"""

import os
import base64
import json
from pathlib import Path
from typing import Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv


class ReceiptExtractor:
    """Extract merchant information from receipt images using GPT-4 Vision."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ReceiptExtractor.
        
        Args:
            api_key: OpenAI API key. If not provided, will load from .env file.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in .env file "
                "or pass it to the constructor."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4.1"  # GPT-4 with vision capabilities
    
    def encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Base64 encoded string of the image.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_merchant_info(self, image_path: str) -> Dict[str, str]:
        """
        Extract merchant name and address from receipt image.
        
        Args:
            image_path: Path to the receipt image file.
            
        Returns:
            Dictionary containing merchant_name and merchant_address.
        """
        # Validate image path
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Encode image
        base64_image = self.encode_image(image_path)
        
        # Create the prompt for GPT-4 Vision
        prompt = """
      You are a Receipt Merchant Extraction Model.

            Instructions:
            1. Look only at the printed header of the receipt, not security stamps or red markings.
            2. Identify the actual merchant name based on:
            - Known Malaysian merchant list (Mydin, Lotus's, 99 Speedmart, Jaya Grocer, Giant, Hero Market, NSK, etc.)
            - Partial text in the top header
            3. Ignore company registration numbers, GST IDs, site codes, timestamps, cashier IDs.
            4. If the address is not explicitly printed, return only the location (e.g., "Bukit Mertajam, Malaysia").
            5. If the merchant name is partially occluded or unclear, infer the nearest exact match from the known list.
            6. NEVER return “Not found”. Always infer the most likely merchant.

            Return JSON only:

            {
            "merchantName": "",
            "merchantAddress": ""
            }
        """
        
        try:
            # Call GPT-4 Vision API
            response = self.client.chat.completions.create(
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
            print(result)
            return {
                "merchant_name": result.get("merchantName", "Not found"),
                "merchant_address": result.get("merchantAddress", "Not found"),
                "raw_response": content
            }
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {content}")
            return {
                "merchant_name": "Error parsing response",
                "merchant_address": "Error parsing response",
                "raw_response": content,
                "error": str(e)
            }
        except Exception as e:
            print(f"Error calling GPT-4 Vision API: {e}")
            return {
                "merchant_name": "Error",
                "merchant_address": "Error",
                "error": str(e)
            }
    
    def process_receipt(self, image_path: str, output_path: Optional[str] = None) -> Dict[str, str]:
        """
        Process a receipt image and optionally save results to a file.
        
        Args:
            image_path: Path to the receipt image.
            output_path: Optional path to save the JSON results.
            
        Returns:
            Dictionary containing extracted information.
        """
        print(f"Processing receipt: {image_path}")
        
        # Extract information
        result = self.extract_merchant_info(image_path)
        
        # Display results
        print("\n" + "="*50)
        print("EXTRACTION RESULTS")
        print("="*50)
        print(f"Merchant Name: {result['merchant_name']}")
        print(f"Merchant Address: {result['merchant_address']}")
        print("="*50 + "\n")
        
        # Save to file if output path is provided
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {output_path}\n")
        
        return result


def main():
    """Main function to demonstrate usage."""
    import sys
    
    # Check if image path is provided
    if len(sys.argv) < 2:
        print("Usage: python receipt_extractor.py <path_to_receipt_image> [output_json_path]")
        print("\nExample:")
        print("  python receipt_extractor.py receipts/receipt1.jpg")
        print("  python receipt_extractor.py receipts/receipt1.jpg output/result.json")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Initialize extractor
        extractor = ReceiptExtractor()
        
        # Process receipt
        extractor.process_receipt(image_path, output_path)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

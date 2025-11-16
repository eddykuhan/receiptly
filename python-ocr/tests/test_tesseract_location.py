#!/usr/bin/env python3
"""
Test script for Tesseract OCR location extraction.
Tests the new store location extraction feature.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.tesseract_ocr import TesseractOCRService


async def test_location_extraction():
    """Test location extraction with a sample receipt image."""
    print("=" * 60)
    print("Testing Tesseract OCR Location Extraction")
    print("=" * 60)
    
    # Initialize service
    tesseract_service = TesseractOCRService(debug_mode=True)
    print("✓ Tesseract OCR Service initialized\n")
    
    # Test with a URL (sample receipt image)
    test_image_url = "https://receiptly-staging-receipts.s3.ap-southeast-1.amazonaws.com/users/default-user/receipts/2025/11/16/2674f091-e50b-40e5-adce-e87f21256dac/receipt_1763255767554.jpg?X-Amz-Expires=3600&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA5ZJTSBRRPR56Z6XY%2F20251116%2Fap-southeast-1%2Fs3%2Faws4_request&X-Amz-Date=20251116T012320Z&X-Amz-SignedHeaders=host&X-Amz-Signature=00d4fefec53fe4543399f09baa1b72f7d8ac18a8b651c2ecb617e021468338b0"
    
    print(f"Test Image URL: {test_image_url}\n")
    
    try:
        # Download image
        import httpx
        async with httpx.AsyncClient() as client:
            print("Downloading test image...")
            response = await client.get(test_image_url)
            response.raise_for_status()
            image_bytes = response.content
            print(f"✓ Downloaded {len(image_bytes)} bytes\n")
        
        # Extract location
        print("Extracting location information...")
        result = tesseract_service.extract_location_from_bytes(image_bytes)
        
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        if result.get('success'):
            print("✓ Location extraction successful!\n")
            
            location = result.get('location', {})
            print(f"Store Name:    {location.get('store_name', 'N/A')}")
            print(f"Address:       {location.get('address', 'N/A')}")
            print(f"Phone:         {location.get('phone', 'N/A')}")
            print(f"Postal Code:   {location.get('postal_code', 'N/A')}")
            print(f"Country:       {location.get('country', 'N/A')}")
            print(f"Confidence:    {location.get('confidence', 0.0):.2%}\n")
            
            print("-" * 60)
            print("Full Location Text:")
            print("-" * 60)
            print(location.get('full_location_text', 'N/A'))
            print()
            
            print("-" * 60)
            print("Raw OCR Text (first 500 chars):")
            print("-" * 60)
            print(result.get('raw_text', 'N/A'))
        else:
            print("✗ Location extraction failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n")
    asyncio.run(test_location_extraction())
    print("\n")

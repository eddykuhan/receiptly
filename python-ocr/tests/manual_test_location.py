"""
Simple manual test for Tesseract location extraction.
Run this with a receipt image URL from your actual receipts.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import requests
from io import BytesIO
from app.services.tesseract_ocr import TesseractOCRService


def test_with_url(image_url: str):
    """Test location extraction with an image URL."""
    print("=" * 70)
    print("TESSERACT LOCATION EXTRACTION TEST")
    print("=" * 70)
    print(f"\nImage URL: {image_url}\n")
    
    try:
        # Download image
        print("📥 Downloading image...")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image_bytes = response.content
        print(f"✓ Downloaded {len(image_bytes):,} bytes\n")
        
        # Initialize service with debug mode
        service = TesseractOCRService(debug_mode=True)
        
        # Extract location
        print("🔍 Extracting location information...\n")
        result = service.extract_location_from_bytes(image_bytes)
        
        # Display results
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        if result.get('success'):
            print("✓ SUCCESS\n")
            
            location = result.get('location', {})
            
            print(f"📍 Store Name:     {location.get('store_name') or '(not detected)'}")
            print(f"📍 Address:        {location.get('address') or '(not detected)'}")
            print(f"📞 Phone:          {location.get('phone') or '(not detected)'}")
            print(f"📮 Postal Code:    {location.get('postal_code') or '(not detected)'}")
            print(f"🌍 Country:        {location.get('country') or '(not detected)'}")
            print(f"📊 Confidence:     {location.get('confidence', 0.0):.0%}")
            
            print("\n" + "-" * 70)
            print("FULL LOCATION TEXT")
            print("-" * 70)
            print(location.get('full_location_text', '(none)'))
            
            print("\n" + "-" * 70)
            print("RAW OCR TEXT (preview)")
            print("-" * 70)
            raw_text = result.get('raw_text', '')
            print(raw_text[:300] + "..." if len(raw_text) > 300 else raw_text)
            
        else:
            print("✗ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # You can provide URL as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test - use one of your actual receipt URLs from the .NET API
        print("\n💡 Usage: python manual_test_location.py <image_url>")
        print("\nExample:")
        print("  python manual_test_location.py https://example.com/receipt.jpg\n")
        sys.exit(1)
    
    test_with_url(url)

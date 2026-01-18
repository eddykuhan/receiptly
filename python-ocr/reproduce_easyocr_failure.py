import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, os.getcwd())

from app.services.easyocr_service import EasyOCRService

def test_easyocr():
    # Path to the debug image
    image_path = "debug_ocr/20251130_145747_193124/01_original.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    print(f"Testing EasyOCR with image: {image_path}")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Initialize service with debug mode
    service = EasyOCRService(debug_mode=True)
    
    # Extract location
    print("Running extraction...")
    result = service.extract_location_from_bytes(image_bytes)
    
    print("\n" + "="*50)
    print("RESULT")
    print("="*50)
    print(result)

    if result.get('error'):
        print("\nERROR DETAILS:")
        print(result.get('error'))

if __name__ == "__main__":
    test_easyocr()

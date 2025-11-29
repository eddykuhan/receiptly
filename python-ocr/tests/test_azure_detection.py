#!/usr/bin/env python3
"""
Test Azure Document Intelligence Layout model for receipt boundary detection.
Compares it with OpenCV-based detection.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.azure_receipt_detector import AzureReceiptDetector
from app.services.receipt_detector import ReceiptDetector


async def test_azure_detection(image_path: str, output_dir: str = "output"):
    """
    Test Azure Layout model receipt detection.
    
    Args:
        image_path: Path to the image file
        output_dir: Directory to save output files
    """
    print("=" * 80)
    print("AZURE LAYOUT MODEL - RECEIPT BOUNDARY DETECTION TEST")
    print("=" * 80)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read image file
    print(f"\n📂 Reading image: {image_path}")
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"   Original size: {len(image_bytes) / 1024:.1f} KB")
    
    input_filename = Path(image_path).stem
    
    # Test 1: Azure Layout Detection
    print(f"\n🔷 Method 1: Azure Document Intelligence Layout Model")
    print("-" * 80)
    
    try:
        azure_detector = AzureReceiptDetector()
        
        azure_vis_path = os.path.join(output_dir, f"{input_filename}_azure_detection.jpg")
        azure_cropped_path = os.path.join(output_dir, f"{input_filename}_azure_cropped.jpg")
        
        cropped_bytes, vis_file = await azure_detector.detect_with_visualization(
            image_bytes,
            output_path=azure_vis_path
        )
        
        # Save cropped image
        with open(azure_cropped_path, 'wb') as f:
            f.write(cropped_bytes)
        
        print(f"   Cropped size: {len(cropped_bytes) / 1024:.1f} KB")
        print(f"   📊 Detection visualization: {azure_vis_path}")
        print(f"   ✂️  Cropped receipt: {azure_cropped_path}")
        
        azure_reduction = (1 - len(cropped_bytes) / len(image_bytes)) * 100
        print(f"   📉 File size reduced by: {azure_reduction:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Azure detection failed: {str(e)}")
    
    # Test 2: OpenCV Detection (for comparison)
    print(f"\n🔶 Method 2: OpenCV Edge Detection (Comparison)")
    print("-" * 80)
    
    try:
        opencv_detector = ReceiptDetector()
        
        opencv_vis_path = os.path.join(output_dir, f"{input_filename}_opencv_detection.jpg")
        opencv_cropped_path = os.path.join(output_dir, f"{input_filename}_opencv_cropped.jpg")
        
        cropped_bytes_cv, vis_file_cv = opencv_detector.detect_with_visualization(
            image_bytes,
            output_path=opencv_vis_path
        )
        
        # Save cropped image
        with open(opencv_cropped_path, 'wb') as f:
            f.write(cropped_bytes_cv)
        
        print(f"   Cropped size: {len(cropped_bytes_cv) / 1024:.1f} KB")
        print(f"   📊 Detection visualization: {opencv_vis_path}")
        print(f"   ✂️  Cropped receipt: {opencv_cropped_path}")
        
        opencv_reduction = (1 - len(cropped_bytes_cv) / len(image_bytes)) * 100
        print(f"   📉 File size reduced by: {opencv_reduction:.1f}%")
        
    except Exception as e:
        print(f"   ❌ OpenCV detection failed: {str(e)}")
    
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\nOriginal size: {len(image_bytes) / 1024:.1f} KB")
    print(f"\nAzure Layout Model:")
    print(f"  - More accurate boundary detection")
    print(f"  - Uses AI to understand document structure")
    print(f"  - Better handling of complex backgrounds")
    print(f"\nOpenCV Edge Detection:")
    print(f"  - Faster processing")
    print(f"  - Works offline")
    print(f"  - Good for simple backgrounds")
    print("\n" + "=" * 80)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Azure Layout model for receipt boundary detection"
    )
    parser.add_argument(
        "image_path",
        help="Path to the receipt image file"
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory for results (default: output)"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.image_path):
        print(f"❌ Error: File not found: {args.image_path}")
        sys.exit(1)
    
    # Run test
    asyncio.run(test_azure_detection(args.image_path, args.output))


if __name__ == "__main__":
    main()

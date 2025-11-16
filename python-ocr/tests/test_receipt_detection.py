#!/usr/bin/env python3
"""
Test script for receipt boundary detection and cropping.
Demonstrates how the ReceiptDetector automatically crops images to just the receipt area.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.receipt_detector import ReceiptDetector


def test_receipt_detection(image_path: str, output_dir: str = "output"):
    """
    Test receipt detection on a local image file.
    
    Args:
        image_path: Path to the image file
        output_dir: Directory to save output files
    """
    print("=" * 80)
    print("RECEIPT BOUNDARY DETECTION TEST")
    print("=" * 80)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read image file
    print(f"\n📂 Reading image: {image_path}")
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"   Original size: {len(image_bytes) / 1024:.1f} KB")
    
    # Initialize detector
    detector = ReceiptDetector()
    
    # Detect and crop with visualization
    print(f"\n🔍 Detecting receipt boundary...")
    
    input_filename = Path(image_path).stem
    vis_path = os.path.join(output_dir, f"{input_filename}_detection.jpg")
    cropped_path = os.path.join(output_dir, f"{input_filename}_cropped.jpg")
    
    cropped_bytes, vis_file = detector.detect_with_visualization(
        image_bytes, 
        output_path=vis_path
    )
    
    # Save cropped image
    with open(cropped_path, 'wb') as f:
        f.write(cropped_bytes)
    
    print(f"   Cropped size: {len(cropped_bytes) / 1024:.1f} KB")
    
    print(f"\n✅ Results saved:")
    print(f"   📊 Detection visualization: {vis_path}")
    print(f"   ✂️  Cropped receipt: {cropped_path}")
    
    # Calculate savings
    reduction = (1 - len(cropped_bytes) / len(image_bytes)) * 100
    print(f"\n📉 File size reduced by: {reduction:.1f}%")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test receipt boundary detection and cropping"
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
    test_receipt_detection(args.image_path, args.output)


if __name__ == "__main__":
    main()

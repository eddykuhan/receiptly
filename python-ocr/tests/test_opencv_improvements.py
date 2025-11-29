#!/usr/bin/env python3
"""
Test script to verify OpenCV improvements for receipt boundary detection.
Tests various scenarios and edge cases.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.receipt_detector import ReceiptDetector


def test_receipt(image_path: str):
    """Test receipt detection on a single image."""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(image_path).name}")
    print(f"{'='*80}")
    
    # Read image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    original_size = len(image_bytes)
    print(f"📂 Original size: {original_size / 1024:.1f} KB")
    
    # Initialize detector
    detector = ReceiptDetector()
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "output" / "opencv_tests"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test detection with visualization
    filename = Path(image_path).stem
    vis_path = output_dir / f"{filename}_detection.jpg"
    
    cropped_bytes, _ = detector.detect_with_visualization(image_bytes, str(vis_path))
    
    cropped_size = len(cropped_bytes)
    reduction = ((original_size - cropped_size) / original_size) * 100
    
    print(f"✂️  Cropped size: {cropped_size / 1024:.1f} KB")
    print(f"📉 Size change: {reduction:+.1f}%")
    
    # Save cropped image
    cropped_path = output_dir / f"{filename}_cropped.jpg"
    with open(cropped_path, 'wb') as f:
        f.write(cropped_bytes)
    
    print(f"📊 Visualization: {vis_path}")
    print(f"💾 Cropped image: {cropped_path}")
    
    return {
        'filename': Path(image_path).name,
        'original_size': original_size,
        'cropped_size': cropped_size,
        'reduction_percent': reduction
    }


def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python test_opencv_improvements.py <image_path> [<image_path2> ...]")
        print("\nExample:")
        print("  python test_opencv_improvements.py receipt1.jpg receipt2.jpg")
        sys.exit(1)
    
    image_paths = sys.argv[1:]
    results = []
    
    print("\n" + "="*80)
    print("OPENCV RECEIPT DETECTION - IMPROVEMENT TEST")
    print("="*80)
    
    for image_path in image_paths:
        if not os.path.exists(image_path):
            print(f"\n❌ Error: File not found: {image_path}")
            continue
        
        try:
            result = test_receipt(image_path)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error processing {image_path}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Summary
    if results:
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        total_original = sum(r['original_size'] for r in results)
        total_cropped = sum(r['cropped_size'] for r in results)
        avg_reduction = sum(r['reduction_percent'] for r in results) / len(results)
        
        print(f"\n📊 Processed {len(results)} image(s)")
        print(f"📂 Total original size: {total_original / 1024:.1f} KB")
        print(f"✂️  Total cropped size: {total_cropped / 1024:.1f} KB")
        print(f"📉 Average reduction: {avg_reduction:+.1f}%")
        
        print("\nPer-image results:")
        for r in results:
            print(f"  • {r['filename']}: {r['reduction_percent']:+.1f}%")


if __name__ == "__main__":
    main()

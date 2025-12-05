"""
Batch processor for multiple receipt images.
"""

import os
import json
from pathlib import Path
from typing import List, Dict
from receipt_extractor import ReceiptExtractor


class BatchReceiptProcessor:
    """Process multiple receipt images in batch."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the batch processor.
        
        Args:
            api_key: OpenAI API key.
        """
        self.extractor = ReceiptExtractor(api_key)
    
    def process_directory(
        self, 
        input_dir: str, 
        output_dir: str = "output",
        extensions: List[str] = None
    ) -> List[Dict]:
        """
        Process all receipt images in a directory.
        
        Args:
            input_dir: Directory containing receipt images.
            output_dir: Directory to save extraction results.
            extensions: List of image file extensions to process.
            
        Returns:
            List of dictionaries containing results for each image.
        """
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Find all image files
        input_path = Path(input_dir)
        image_files = []
        for ext in extensions:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"No image files found in {input_dir}")
            return []
        
        print(f"Found {len(image_files)} image(s) to process\n")
        
        # Process each image
        results = []
        for idx, image_file in enumerate(image_files, 1):
            print(f"[{idx}/{len(image_files)}] Processing: {image_file.name}")
            
            # Create output filename
            output_filename = f"{image_file.stem}_result.json"
            output_path = os.path.join(output_dir, output_filename)
            
            # Process receipt
            result = self.extractor.process_receipt(str(image_file), output_path)
            result['image_filename'] = image_file.name
            results.append(result)
            
            print()  # Add spacing between results
        
        # Save summary
        summary_path = os.path.join(output_dir, "batch_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nBatch processing complete!")
        print(f"Processed {len(results)} receipt(s)")
        print(f"Summary saved to: {summary_path}")
        
        return results


def main():
    """Main function for batch processing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python batch_processor.py <input_directory> [output_directory]")
        print("\nExample:")
        print("  python batch_processor.py receipts/")
        print("  python batch_processor.py receipts/ output/")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
    
    try:
        processor = BatchReceiptProcessor()
        processor.process_directory(input_dir, output_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

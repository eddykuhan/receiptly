"""
Example usage of the Receipt Extractor.
This script demonstrates different ways to use the receipt extractor.
"""

from receipt_extractor import ReceiptExtractor
from batch_processor import BatchReceiptProcessor
import json


def example_single_receipt():
    """Example: Process a single receipt."""
    print("=" * 60)
    print("EXAMPLE 1: Single Receipt Processing")
    print("=" * 60)
    
    # Initialize the extractor
    extractor = ReceiptExtractor()
    
    # Process a receipt (replace with your actual image path)
    image_path = "receipts/sample_receipt.jpg"
    
    try:
        result = extractor.extract_merchant_info(image_path)
        
        print(f"\nMerchant Name: {result['merchant_name']}")
        print(f"Merchant Address: {result['merchant_address']}")
        
        # Save to file
        with open("output/single_result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print("\n✓ Results saved to output/single_result.json")
        
    except FileNotFoundError:
        print(f"\n⚠ Image file not found: {image_path}")
        print("Please add a receipt image to the 'receipts/' directory")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def example_batch_processing():
    """Example: Process multiple receipts in a directory."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Batch Processing")
    print("=" * 60)
    
    # Initialize the batch processor
    processor = BatchReceiptProcessor()
    
    # Process all receipts in a directory
    input_dir = "receipts"
    output_dir = "output/batch_results"
    
    try:
        results = processor.process_directory(input_dir, output_dir)
        
        print(f"\n✓ Processed {len(results)} receipt(s)")
        print(f"✓ Results saved to {output_dir}/")
        
        # Display summary
        print("\nSummary:")
        for idx, result in enumerate(results, 1):
            print(f"\n{idx}. {result.get('image_filename', 'Unknown')}")
            print(f"   Merchant: {result['merchant_name']}")
            print(f"   Address: {result['merchant_address']}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")


def example_custom_processing():
    """Example: Custom processing with error handling."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Custom Processing with Error Handling")
    print("=" * 60)
    
    extractor = ReceiptExtractor()
    
    # List of receipts to process
    receipts = [
        "receipts/receipt1.jpg",
        "receipts/receipt2.jpg",
        "receipts/receipt3.jpg"
    ]
    
    successful = 0
    failed = 0
    
    for receipt_path in receipts:
        try:
            print(f"\nProcessing: {receipt_path}")
            result = extractor.extract_merchant_info(receipt_path)
            
            # Check if extraction was successful
            if result['merchant_name'] != "Not found":
                print(f"✓ Success: {result['merchant_name']}")
                successful += 1
            else:
                print("⚠ Merchant name not found in receipt")
                failed += 1
                
        except FileNotFoundError:
            print(f"✗ File not found: {receipt_path}")
            failed += 1
        except Exception as e:
            print(f"✗ Error processing {receipt_path}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Processing Complete: {successful} successful, {failed} failed")
    print(f"{'=' * 60}")


def example_integration():
    """Example: Integration with a database or API."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Integration Example")
    print("=" * 60)
    
    extractor = ReceiptExtractor()
    
    # Simulate processing and storing in a database
    receipts_data = []
    
    receipt_files = ["receipts/receipt1.jpg"]  # Add your receipt paths
    
    for receipt_path in receipt_files:
        try:
            result = extractor.extract_merchant_info(receipt_path)
            
            # Create a record for database
            record = {
                "file_path": receipt_path,
                "merchant_name": result['merchant_name'],
                "merchant_address": result['merchant_address'],
                "status": "processed",
                "confidence": "high" if result['merchant_name'] != "Not found" else "low"
            }
            
            receipts_data.append(record)
            print(f"✓ Processed: {receipt_path}")
            
        except Exception as e:
            # Create error record
            record = {
                "file_path": receipt_path,
                "merchant_name": None,
                "merchant_address": None,
                "status": "error",
                "error_message": str(e)
            }
            receipts_data.append(record)
            print(f"✗ Error: {receipt_path}")
    
    # Save to JSON (simulating database storage)
    with open("output/database_records.json", "w") as f:
        json.dump(receipts_data, f, indent=2)
    
    print(f"\n✓ Saved {len(receipts_data)} record(s) to output/database_records.json")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("RECEIPT EXTRACTOR - USAGE EXAMPLES")
    print("=" * 60)
    print("\nThis script demonstrates various ways to use the receipt extractor.")
    print("Make sure you have:")
    print("  1. Set up your .env file with OPENAI_API_KEY")
    print("  2. Added some receipt images to the 'receipts/' directory")
    print("\n" + "=" * 60)
    
    # Run examples
    example_single_receipt()
    # example_batch_processing()  # Uncomment to run
    # example_custom_processing()  # Uncomment to run
    # example_integration()  # Uncomment to run
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

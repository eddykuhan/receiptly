"""
Test script for TransactionDate extraction from receipts.
Tests various date formats and validates the date extraction logic.
"""
from app.services.tesseract_ocr import TesseractOCRService

def test_date_extraction():
    """Test date extraction with various formats."""
    
    service = TesseractOCRService()
    
    # Test cases with different date formats
    test_cases = [
        {
            'name': 'DD/MM/YYYY format',
            'text': 'Store Name\n23/11/2025\nTotal: $50.00',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'MM/DD/YYYY format',
            'text': 'Receipt\n11/23/2025\nSubtotal: $25.00',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'DD MMM YYYY format',
            'text': 'Thank you\n23 Nov 2025\nTotal: $100',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'YYYY-MM-DD format',
            'text': 'Invoice\n2025-11-23\nAmount: $75',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'DD-MM-YY format (2-digit year)',
            'text': 'Receipt\n23-11-25\nTotal: $30',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'Date with OCR errors (O instead of 0)',
            'text': 'Store\n23/11/2O25\nTotal: $40',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'Date with slashes misread as l',
            'text': 'Receipt\n23l11l2025\nTotal: $60',
            'expected_date': '2025-11-23'
        },
        {
            'name': 'No date present',
            'text': 'Store Name\nAddress Line\nThank you!',
            'expected_date': None
        },
        {
            'name': 'Future date (should be rejected)',
            'text': 'Receipt\n23/11/2099\nTotal: $50',
            'expected_date': None
        }
    ]
    
    print("=" * 70)
    print("Testing Date Extraction")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Input text: {repr(test_case['text'][:50])}...")
        
        result = service.extract_date_from_text(test_case['text'])
        
        if result:
            extracted_date = result['value']
            confidence = result['confidence']
            format_detected = result.get('format_detected', 'unknown')
            content = result.get('content', '')
            
            print(f"✓ Extracted: {extracted_date}")
            print(f"  Confidence: {confidence:.2f}")
            print(f"  Format: {format_detected}")
            print(f"  Original text: '{content}'")
            
            if extracted_date == test_case['expected_date']:
                print("✓ PASS - Correct date extracted")
                passed += 1
            else:
                print(f"✗ FAIL - Expected {test_case['expected_date']}, got {extracted_date}")
                failed += 1
        else:
            print("✓ No date extracted")
            if test_case['expected_date'] is None:
                print("✓ PASS - Correctly rejected invalid/no date")
                passed += 1
            else:
                print(f"✗ FAIL - Expected {test_case['expected_date']}, but got None")
                failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = test_date_extraction()
    exit(0 if failed == 0 else 1)

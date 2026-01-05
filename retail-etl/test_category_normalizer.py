"""
Test script for CategoryNormalizer

Verifies that category normalization works correctly before running full ETL.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl_transformers.category_normalizer import normalize_category

# Test cases from actual data
test_cases = [
    # Case variations
    ("beverages", "Beverages"),
    ("Beverages", "Beverages"),
    ("BEVERAGES", "Beverages"),
    
    # Spelling variations
    ("yogurt", "Yogurt"),
    ("yoghurt", "Yogurt"),
    ("Yoghurt", "Yogurt"),
    
    # Whitespace
    ("UHT Milk ", "UHT Milk"),
    (" UHT Milk", "UHT Milk"),
    ("  Adult Milk  ", "Adult Milk"),
    
    # Case normalization
    ("chilled and frozen", "Chilled and Frozen"),
    ("food essentials", "Food Essentials"),
    ("fresh market", "Fresh Market"),
    
    # Unknown/empty
    ("", "Unknown"),
    (None, "Unknown"),
    ("uncategorized", "Unknown"),
    ("others", "Unknown"),
    
    # Title case for unknown categories
    ("organic juice", "Organic Juice"),
    ("instant noodles", "Instant Noodles"),
    
    # Preserve acronyms
    ("UHT Milk", "UHT Milk"),
    ("MSG and Salt", "MSG And Salt"),
]

def test_normalizer():
    """Run normalization tests."""
    print("Testing CategoryNormalizer...")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_cat, expected in test_cases:
        result = normalize_category(input_cat)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} Input: {repr(input_cat):30} → Expected: {expected:25} | Got: {result}")
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print(f"✗ {failed} tests failed")
        return False

if __name__ == "__main__":
    success = test_normalizer()
    sys.exit(0 if success else 1)

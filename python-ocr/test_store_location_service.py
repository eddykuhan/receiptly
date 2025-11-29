"""
Test script for StoreLocationService

Tests fuzzy matching capabilities with various scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.store_location_service import StoreLocationService


def print_match_result(result: dict, test_name: str):
    """Pretty print match result."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print('='*80)
    
    if result:
        print(f"✅ MATCH FOUND")
        print(f"   Store:      {result['store_name']}")
        print(f"   Branch:     {result['branch_name']}")
        print(f"   Address:    {result['address'][:70]}...")
        print(f"   Phone:      {result.get('phone', 'N/A')}")
        print(f"   Coordinates: ({result['latitude']}, {result['longitude']})")
        print(f"   Rating:     {result.get('rating', 'N/A')} ({result.get('total_ratings', 0)} reviews)")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason:     {result['match_reason']}")
    else:
        print(f"❌ NO MATCH FOUND")


def main():
    print("="*80)
    print("STORE LOCATION SERVICE - TEST SUITE")
    print("="*80)
    
    # Initialize service
    service = StoreLocationService()
    
    # Print stats
    stats = service.get_stats()
    print(f"\n📊 Database Statistics:")
    print(f"   Total locations: {stats['total_locations']}")
    print(f"   Total stores: {stats['total_stores']}")
    for store, count in stats['stores'].items():
        print(f"   - {store.title()}: {count} locations")
    
    # Test 1: Exact match with phone number
    print_match_result(
        service.find_best_match(
            store_name="Jaya Grocer",
            phone="04-291 9883"
        ),
        "Exact name + phone match"
    )
    
    # Test 2: Exact match with postal code
    print_match_result(
        service.find_best_match(
            store_name="Jaya Grocer",
            postal_code="10250"
        ),
        "Exact name + postal code match"
    )
    
    # Test 3: Exact match with city in address
    print_match_result(
        service.find_best_match(
            store_name="Jaya Grocer",
            partial_address="Gurney Paragon, Penang"
        ),
        "Exact name + city match"
    )
    
    # Test 4: Fuzzy match (OCR error)
    print_match_result(
        service.find_best_match(
            store_name="Jaya Groc",  # Missing letters
            partial_address="Penang"
        ),
        "Fuzzy name match with city"
    )
    
    # Test 5: Different store - Mydin
    print_match_result(
        service.find_best_match(
            store_name="Mydin",
            partial_address="Bukit Mertajam"
        ),
        "Mydin with city match"
    )
    
    # Test 6: Lotus's (with apostrophe)
    print_match_result(
        service.find_best_match(
            store_name="Lotus's",
            partial_address="Seberang Jaya"
        ),
        "Lotus's with city match"
    )
    
    # Test 7: AEON
    print_match_result(
        service.find_best_match(
            store_name="AEON",
            partial_address="Bukit Mertajam"
        ),
        "AEON with city match"
    )
    
    # Test 8: Village Grocer
    print_match_result(
        service.find_best_match(
            store_name="Village Grocer",
            partial_address="Penang"
        ),
        "Village Grocer with city match"
    )
    
    # Test 9: No match (unknown store)
    print_match_result(
        service.find_best_match(
            store_name="Unknown Kedai",
            partial_address="Somewhere"
        ),
        "Unknown store (should not match)"
    )
    
    # Test 10: Very fuzzy match (low confidence)
    print_match_result(
        service.find_best_match(
            store_name="JG",  # Very short abbreviation
            min_confidence=0.3  # Lower threshold
        ),
        "Very fuzzy match (abbreviation)"
    )
    
    # Test 11: OCR garbage (should not match)
    print_match_result(
        service.find_best_match(
            store_name="09556057664289 cP6_CoMMOR",  # Product code
            min_confidence=0.5
        ),
        "OCR garbage (should not match)"
    )
    
    # Test 12: Partial name with phone
    print_match_result(
        service.find_best_match(
            store_name="Jaya",  # Partial name
            phone="1-300-88-5427"  # Common Jaya Grocer number
        ),
        "Partial name + phone match"
    )
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

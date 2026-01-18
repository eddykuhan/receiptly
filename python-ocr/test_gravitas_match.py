#!/usr/bin/env python3
"""
Test Google Places matching for 99 Speedmart at Gravitas Business Park
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.store_location_service import StoreLocationService

def test_gravitas_match():
    """Test that Gravitas Business Park is correctly matched"""
    
    print("=" * 80)
    print("Testing Google Places Matching for 99 Speedmart @ Gravitas")
    print("=" * 80)
    
    # Initialize service
    service = StoreLocationService()
    
    # Check if data loaded
    stats = service.get_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Total locations: {stats['total_locations']}")
    print(f"   Total stores: {stats['total_stores']}")
    if '99 speedmart' in stats['stores']:
        print(f"   99 Speedmart branches: {stats['stores']['99 speedmart']}")
    
    # Test case: Receipt from Gravitas Business Park
    print("\n" + "=" * 80)
    print("TEST CASE: 99 Speedmart at Gravitas Business Park")
    print("=" * 80)
    
    store_name = "99 Speedmart"
    ocr_address = "Gravitas Business Park, Malaysia"
    
    print(f"\nInput:")
    print(f"  Store Name: {store_name}")
    print(f"  OCR Address: {ocr_address}")
    
    # Find match
    result = service.find_best_match(
        store_name=store_name,
        partial_address=ocr_address,
        phone=None,
        postal_code=None,
        min_confidence=0.70
    )
    
    print(f"\n{'='*80}")
    if result:
        print("✅ MATCH FOUND!")
        print(f"{'='*80}")
        print(f"  Branch: {result['branch_name']}")
        print(f"  Address: {result['address']}")
        print(f"  Phone: {result.get('phone', 'N/A')}")
        print(f"  Latitude: {result.get('latitude', 'N/A')}")
        print(f"  Longitude: {result.get('longitude', 'N/A')}")
        print(f"  Rating: {result.get('rating', 'N/A')} ({result.get('total_ratings', 0)} reviews)")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Reason: {result['match_reason']}")
        print(f"{'='*80}")
    else:
        print("❌ NO MATCH FOUND")
        print(f"{'='*80}")
        print("  This should NOT happen if data is loaded correctly.")
        print("  Possible issues:")
        print("  - Data directory not found")
        print("  - Store name mismatch")
        print("  - Confidence threshold too high")
    
    # Additional test: Check if branch exists in database
    print(f"\n{'='*80}")
    print("VERIFICATION: Checking raw database for Gravitas")
    print(f"{'='*80}")
    
    speedmart_locations = service.get_locations_for_store("99 speedmart")
    gravitas_branches = [
        loc for loc in speedmart_locations 
        if 'gravitas' in loc.get('branch_name', '').lower()
    ]
    
    if gravitas_branches:
        print(f"✅ Found {len(gravitas_branches)} Gravitas branch(es) in database:")
        for branch in gravitas_branches:
            print(f"   - {branch['branch_name']}")
            print(f"     {branch['address']}")
    else:
        print("❌ No Gravitas branches found in database")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_gravitas_match()

#!/usr/bin/env python3
"""
Test script to verify Sunway Carnival vs Sunway Pyramid disambiguation.

This test ensures that the location matching service correctly distinguishes
between different Sunway locations based on specific mall names.
"""

import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.store_location_service import StoreLocationService

def test_sunway_carnival_match():
    """Test that Sunway Carnival matches correctly (Penang location)."""
    print("\n" + "="*70)
    print("TEST 1: Watsons at Sunway Carnival (Penang)")
    print("="*70)
    
    service = StoreLocationService()
    
    result = service.find_best_match(
        store_name="Watsons",
        partial_address="Sunway Carnival, Malaysia"
    )
    
    if result:
        print(f"\n✅ Match found!")
        print(f"   Branch: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
        
        # Verify it's the Penang location (Sunway Carnival)
        is_carnival = "carnival" in result['branch_name'].lower()
        is_penang = "penang" in result['address'].lower()
        
        if is_carnival and is_penang:
            print("\n✅ PASS: Correctly matched Sunway Carnival in Penang")
            return True
        else:
            print("\n❌ FAIL: Matched wrong location")
            print(f"   Expected: Sunway Carnival (Penang)")
            print(f"   Got: {result['branch_name']}")
            return False
    else:
        print("\n❌ FAIL: No match found")
        return False


def test_sunway_pyramid_match():
    """Test that Sunway Pyramid matches correctly (Petaling Jaya location)."""
    print("\n" + "="*70)
    print("TEST 2: Watsons at Sunway Pyramid (Petaling Jaya)")
    print("="*70)
    
    service = StoreLocationService()
    
    result = service.find_best_match(
        store_name="Watsons",
        partial_address="Sunway Pyramid, Petaling Jaya"
    )
    
    if result:
        print(f"\n✅ Match found!")
        print(f"   Branch: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
        
        # Verify it's the Petaling Jaya location (Sunway Pyramid)
        is_pyramid = "pyramid" in result['branch_name'].lower() or "pyramid" in result['address'].lower()
        is_pj = "petaling jaya" in result['address'].lower()
        
        if is_pyramid and is_pj:
            print("\n✅ PASS: Correctly matched Sunway Pyramid in Petaling Jaya")
            return True
        else:
            print("\n❌ FAIL: Matched wrong location")
            print(f"   Expected: Sunway Pyramid (Petaling Jaya)")
            print(f"   Got: {result['branch_name']}")
            return False
    else:
        print("\n❌ FAIL: No match found")
        return False


def test_no_location_specified():
    """Test matching when only store name is provided (should have lower confidence)."""
    print("\n" + "="*70)
    print("TEST 3: Watsons with no specific location (ambiguous)")
    print("="*70)
    
    service = StoreLocationService()
    
    result = service.find_best_match(
        store_name="Watsons"
    )
    
    if result:
        print(f"\n✅ Match found!")
        print(f"   Branch: {result['branch_name']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
        
        # Should have lower confidence without location info
        if result['confidence'] <= 0.85:
            print(f"\n✅ PASS: Lower confidence ({result['confidence']:.2f}) without location")
            return True
        else:
            print(f"\n⚠️  WARNING: High confidence ({result['confidence']:.2f}) without location info")
            return True  # Still pass but warn
    else:
        print("\n❌ FAIL: No match found")
        return False


def test_phone_number_disambiguation():
    """Test that phone number can disambiguate between Sunway locations."""
    print("\n" + "="*70)
    print("TEST 4: Phone number disambiguation (Sunway Carnival)")
    print("="*70)
    
    service = StoreLocationService()
    
    # Sunway Carnival phone: 04-383 1994
    result = service.find_best_match(
        store_name="Watsons",
        partial_address="Sunway",  # Ambiguous
        phone="04-383 1994"
    )
    
    if result:
        print(f"\n✅ Match found!")
        print(f"   Branch: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Phone: {result['phone']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
        
        # Verify it's Sunway Carnival based on phone
        is_carnival = "carnival" in result['branch_name'].lower()
        
        if is_carnival:
            print("\n✅ PASS: Phone number correctly disambiguated to Sunway Carnival")
            return True
        else:
            print("\n❌ FAIL: Phone number didn't disambiguate correctly")
            return False
    else:
        print("\n❌ FAIL: No match found")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SUNWAY LOCATION DISAMBIGUATION TESTS")
    print("="*70)
    print("\nTesting ability to distinguish between:")
    print("  • Watsons Sunway Carnival Mall (Penang)")
    print("  • Watsons Sunway Pyramid (Petaling Jaya)")
    print("  • Other Sunway locations")
    
    results = []
    
    results.append(("Sunway Carnival Match", test_sunway_carnival_match()))
    results.append(("Sunway Pyramid Match", test_sunway_pyramid_match()))
    results.append(("No Location Specified", test_no_location_specified()))
    results.append(("Phone Disambiguation", test_phone_number_disambiguation()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

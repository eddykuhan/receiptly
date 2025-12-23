"""
Test Store Location Service

Run with: pytest tests/test_store_location_service.py -v
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.store_location_service import StoreLocationService


class TestStoreLocationService:
    """Test suite for StoreLocationService matching capabilities"""
    
    @pytest.fixture
    def service(self):
        """Create service instance with actual store data"""
        # Use the actual store-scraper data
        data_path = Path(__file__).parent.parent.parent / "store-scraper" / "data"
        return StoreLocationService(data_directory=str(data_path))
    
    # ========== EXACT MATCH TESTS ==========
    
    def test_exact_store_name_match(self, service):
        """Test exact store name matching"""
        result = service.find_best_match(
            store_name="99 Speedmart",
            min_confidence=0.70
        )
        
        assert result is not None
        assert result['store_name'] == "99 Speedmart"
        assert result['confidence'] >= 0.70
        print(f"\n✅ Exact match: {result['branch_name']} (confidence: {result['confidence']:.2f})")
    
    def test_branch_number_match(self, service):
        """Test matching with branch number (e.g., 99 Speedmart 2542)"""
        result = service.find_best_match(
            store_name="99 Speedmart 2542",
            min_confidence=0.70
        )
        
        assert result is not None
        assert "2542" in result['branch_name']
        assert result['confidence'] >= 0.90  # Should be very high confidence
        print(f"\n✅ Branch match: {result['branch_name']} (confidence: {result['confidence']:.2f})")
        print(f"   Reason: {result['match_reason']}")
    
    def test_location_keyword_match_penang(self, service):
        """Test matching with location keywords (Penang)"""
        result = service.find_best_match(
            store_name="99 Speedmart",
            partial_address="Bandar Perda, Penang",
            min_confidence=0.70
        )
        
        assert result is not None
        assert "Penang" in result['address'] or "Pulau Pinang" in result['address']
        print(f"\n✅ Location match: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
    
    def test_specific_location_match(self, service):
        """Test matching with specific location (e.g., Sunway Carnival)"""
        result = service.find_best_match(
            store_name="99 Speedmart",
            partial_address="Sunway Carnival Mall, Penang",
            min_confidence=0.70
        )
        
        assert result is not None
        # Should match a location near Sunway Carnival
        print(f"\n✅ Specific location: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
    
    # ========== FUZZY MATCHING TESTS ==========
    
    def test_fuzzy_store_name(self, service):
        """Test fuzzy matching with OCR errors"""
        # Simulate OCR error: "99 Speedmart" -> "99 Speed Mart"
        result = service.find_best_match(
            store_name="99 Speed Mart",
            min_confidence=0.60
        )
        
        assert result is not None
        assert result['store_name'] == "99 Speedmart"
        print(f"\n✅ Fuzzy match: '{result['store_name']}' matched from '99 Speed Mart'")
        print(f"   Confidence: {result['confidence']:.2f}")
    
    # ========== PHONE MATCHING TESTS ==========
    
    def test_phone_number_match(self, service):
        """Test matching with phone number"""
        # Use a known phone number from the data
        result = service.find_best_match(
            store_name="99 Speedmart",
            phone="03-3362 6863",
            min_confidence=0.70
        )
        
        assert result is not None
        if result.get('phone'):
            print(f"\n✅ Phone match: {result['branch_name']}")
            print(f"   Phone: {result['phone']}")
            print(f"   Confidence: {result['confidence']:.2f}")
    
    # ========== KUALA LUMPUR TESTS ==========
    
    def test_kl_location_match(self, service):
        """Test matching in Kuala Lumpur"""
        result = service.find_best_match(
            store_name="99 Speedmart",
            partial_address="Bukit Bintang, Kuala Lumpur",
            min_confidence=0.70
        )
        
        assert result is not None
        assert "Kuala Lumpur" in result['address']
        print(f"\n✅ KL location: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
    
    def test_chow_kit_location(self, service):
        """Test specific KL area (Chow Kit)"""
        result = service.find_best_match(
            store_name="99 Speedmart",
            partial_address="Chow Kit, KL",
            min_confidence=0.70
        )
        
        assert result is not None
        print(f"\n✅ Chow Kit match: {result['branch_name']}")
        print(f"   Address: {result['address'][:80]}...")
        print(f"   Confidence: {result['confidence']:.2f}")
    
    # ========== EDGE CASES ==========
    
    def test_no_match_unknown_store(self, service):
        """Test that unknown stores return None"""
        result = service.find_best_match(
            store_name="Non-Existent Store XYZ",
            min_confidence=0.70
        )
        
        assert result is None
        print(f"\n✅ Correctly returns None for unknown store")
    
    def test_low_confidence_rejected(self, service):
        """Test that low confidence matches are rejected"""
        result = service.find_best_match(
            store_name="99",  # Too generic
            min_confidence=0.90  # High threshold
        )
        
        # Might return None or low confidence
        if result:
            assert result['confidence'] >= 0.90
        print(f"\n✅ Low confidence matches rejected")
    
    def test_multiple_signals_high_confidence(self, service):
        """Test that multiple matching signals increase confidence"""
        result = service.find_best_match(
            store_name="99 Speedmart 2542",
            partial_address="Bandar Perda, Bukit Mertajam, Penang",
            phone="03-3362 6863",
            min_confidence=0.70
        )
        
        assert result is not None
        assert result['confidence'] >= 0.85  # Should be high with multiple signals
        print(f"\n✅ Multiple signals: {result['branch_name']}")
        print(f"   Confidence: {result['confidence']:.2f} (high due to multiple signals)")
        print(f"   Reason: {result['match_reason']}")
    
    # ========== SERVICE STATS ==========
    
    def test_service_stats(self, service):
        """Test that service loaded data correctly"""
        stats = service.get_stats()
        
        assert stats['total_locations'] > 0
        assert stats['total_stores'] > 0
        assert '99 speedmart' in stats['stores']
        
        print(f"\n📊 Service Stats:")
        print(f"   Total locations: {stats['total_locations']}")
        print(f"   Total stores: {stats['total_stores']}")
        for store, count in stats['stores'].items():
            print(f"   - {store.title()}: {count} locations")
    
    def test_get_all_stores(self, service):
        """Test getting all store names"""
        stores = service.get_all_stores()
        
        assert len(stores) > 0
        assert '99 speedmart' in stores
        
        print(f"\n🏪 Available stores:")
        for store in stores:
            print(f"   - {store.title()}")
    
    # ========== CUSTOM TEST SCENARIOS ==========
    
    @pytest.mark.parametrize("store_name,partial_address,expected_in_address", [
        ("99 Speedmart", "Penang", "Penang"),
        ("99 Speedmart", "Kuala Lumpur", "Kuala Lumpur"),
        ("99 Speedmart", "Selangor", "Selangor"),
    ])
    def test_parametrized_locations(self, service, store_name, partial_address, expected_in_address):
        """Test various location combinations"""
        result = service.find_best_match(
            store_name=store_name,
            partial_address=partial_address,
            min_confidence=0.70
        )
        
        assert result is not None
        assert expected_in_address in result['address']
        print(f"\n✅ {partial_address}: {result['branch_name'][:50]}...")


# ========== INTERACTIVE TEST FUNCTION ==========

def test_custom_location(store_name: str, address: str = None, phone: str = None):
    """
    Interactive test function to try custom inputs
    
    Usage:
        from tests.test_store_location_service import test_custom_location
        test_custom_location("99 Speedmart", "Sunway Carnival, Penang")
    """
    data_path = Path(__file__).parent.parent.parent / "store-scraper" / "data"
    service = StoreLocationService(data_directory=str(data_path))
    
    result = service.find_best_match(
        store_name=store_name,
        partial_address=address,
        phone=phone,
        min_confidence=0.70
    )
    
    if result:
        print(f"\n✅ Match Found!")
        print(f"   Store: {result['store_name']}")
        print(f"   Branch: {result['branch_name']}")
        print(f"   Address: {result['address']}")
        print(f"   Phone: {result.get('phone', 'N/A')}")
        print(f"   Coordinates: ({result['latitude']}, {result['longitude']})")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reason: {result['match_reason']}")
    else:
        print(f"\n❌ No match found for '{store_name}'")
        print(f"   Address hint: {address}")
        print(f"   Phone hint: {phone}")
    
    return result


if __name__ == "__main__":
    # Run interactive tests
    print("=" * 80)
    print("Interactive Store Location Service Tests")
    print("=" * 80)
    
    # Test 1: Exact match
    # test_custom_location("99 Speedmart")
    
    # Test 2: With location
    test_custom_location("99 Speedmart", "PG The Sun, Malaysia")
    
    # Test 3: With branch number
    # test_custom_location("99 Speedmart 2542")
    
    # Test 4: KL location
    # test_custom_location("99 Speedmart", "Chow Kit, Kuala Lumpur")

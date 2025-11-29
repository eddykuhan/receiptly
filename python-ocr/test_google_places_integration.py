"""
Integration test for Google Places matching in OCR pipeline

Tests the full flow: OCR extraction → Google Places matching → Enhanced response
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.routers.ocr import override_merchant_data_with_easyocr
from app.services.easyocr_service import EasyOCRService


async def test_google_places_integration():
    """Test Google Places integration with mock OCR data."""
    
    print("="*80)
    print("GOOGLE PLACES INTEGRATION TEST")
    print("="*80)
    
    # Initialize EasyOCR service
    easyocr_service = EasyOCRService(debug_mode=False)
    
    # Test Case 1: Azure has merchant name, should trigger Google Places match
    print("\n" + "="*80)
    print("TEST 1: Azure merchant name → Google Places match")
    print("="*80)
    
    azure_result_1 = {
        'fields': {
            'MerchantName': {
                'type': 'string',
                'value': 'Jaya Grocer',
                'confidence': 0.95,
                'source': 'azure'
            },
            'MerchantAddress': {
                'type': 'string',
                'value': 'Some incomplete address',
                'confidence': 0.60,
                'source': 'azure'
            },
            'MerchantPhoneNumber': {
                'type': 'phoneNumber',
                'value': '04-291 9883',
                'confidence': 0.90,
                'source': 'azure'
            }
        },
        'metadata': {}
    }
    
    result_1 = override_merchant_data_with_easyocr(
        azure_result_1,
        easyocr_service,
        image_bytes=None,  # Not needed for this test
        debugger=None
    )
    
    print("\n📊 RESULTS:")
    print(f"   Merchant Name: {result_1['fields']['MerchantName']['value']}")
    print(f"   Address: {result_1['fields']['MerchantAddress']['value'][:70]}...")
    print(f"   Address Source: {result_1['fields']['MerchantAddress'].get('source', 'N/A')}")
    print(f"   Phone: {result_1['fields'].get('MerchantPhoneNumber', {}).get('value', 'N/A')}")
    
    if result_1['metadata'].get('google_places_match'):
        print(f"\n✅ GOOGLE PLACES MATCH FOUND!")
        print(f"   Branch: {result_1['metadata']['matched_branch']}")
        print(f"   Confidence: {result_1['metadata']['match_confidence']:.2f}")
        print(f"   Reason: {result_1['metadata']['match_reason']}")
        print(f"   Coordinates: ({result_1['metadata']['latitude']}, {result_1['metadata']['longitude']})")
        if result_1['metadata'].get('google_rating'):
            print(f"   Rating: {result_1['metadata']['google_rating']} ({result_1['metadata']['google_total_ratings']} reviews)")
    else:
        print(f"\n❌ No Google Places match")
    
    # Test Case 2: Different store - Mydin
    print("\n" + "="*80)
    print("TEST 2: Mydin with partial address")
    print("="*80)
    
    azure_result_2 = {
        'fields': {
            'MerchantName': {
                'type': 'string',
                'value': 'Mydin',
                'confidence': 0.90,
                'source': 'azure'
            },
            'MerchantAddress': {
                'type': 'string',
                'value': 'Bukit Mertajam area',
                'confidence': 0.50,
                'source': 'azure'
            }
        },
        'metadata': {}
    }
    
    result_2 = override_merchant_data_with_easyocr(
        azure_result_2,
        easyocr_service,
        image_bytes=None,
        debugger=None
    )
    
    print("\n📊 RESULTS:")
    print(f"   Merchant Name: {result_2['fields']['MerchantName']['value']}")
    print(f"   Address: {result_2['fields']['MerchantAddress']['value'][:70]}...")
    print(f"   Address Source: {result_2['fields']['MerchantAddress'].get('source', 'N/A')}")
    
    if result_2['metadata'].get('google_places_match'):
        print(f"\n✅ GOOGLE PLACES MATCH FOUND!")
        print(f"   Branch: {result_2['metadata']['matched_branch']}")
        print(f"   Confidence: {result_2['metadata']['match_confidence']:.2f}")
        print(f"   Coordinates: ({result_2['metadata']['latitude']}, {result_2['metadata']['longitude']})")
    else:
        print(f"\n❌ No Google Places match")
    
    # Test Case 3: Unknown store (should not match)
    print("\n" + "="*80)
    print("TEST 3: Unknown store (should not match)")
    print("="*80)
    
    azure_result_3 = {
        'fields': {
            'MerchantName': {
                'type': 'string',
                'value': 'Random Kedai',
                'confidence': 0.85,
                'source': 'azure'
            }
        },
        'metadata': {}
    }
    
    result_3 = override_merchant_data_with_easyocr(
        azure_result_3,
        easyocr_service,
        image_bytes=None,
        debugger=None
    )
    
    print("\n📊 RESULTS:")
    print(f"   Merchant Name: {result_3['fields']['MerchantName']['value']}")
    
    if result_3['metadata'].get('google_places_match'):
        print(f"\n⚠️ UNEXPECTED: Google Places match found")
    else:
        print(f"\n✅ CORRECT: No Google Places match (as expected)")
    
    # Test Case 4: Fuzzy match (OCR error)
    print("\n" + "="*80)
    print("TEST 4: Fuzzy match - 'Jaya Groc' → 'Jaya Grocer'")
    print("="*80)
    
    azure_result_4 = {
        'fields': {
            'MerchantName': {
                'type': 'string',
                'value': 'Jaya Groc',  # OCR error
                'confidence': 0.70,
                'source': 'easyocr_fallback'
            },
            'MerchantAddress': {
                'type': 'string',
                'value': 'Penang',
                'confidence': 0.60,
                'source': 'easyocr_fallback'
            }
        },
        'metadata': {}
    }
    
    result_4 = override_merchant_data_with_easyocr(
        azure_result_4,
        easyocr_service,
        image_bytes=None,
        debugger=None
    )
    
    print("\n📊 RESULTS:")
    print(f"   Merchant Name: {result_4['fields']['MerchantName']['value']}")
    print(f"   Address: {result_4['fields']['MerchantAddress']['value'][:70]}...")
    
    if result_4['metadata'].get('google_places_match'):
        print(f"\n✅ GOOGLE PLACES MATCH FOUND (fuzzy matching worked)!")
        print(f"   Branch: {result_4['metadata']['matched_branch']}")
        print(f"   Confidence: {result_4['metadata']['match_confidence']:.2f}")
    else:
        print(f"\n❌ No Google Places match")
    
    print("\n" + "="*80)
    print("INTEGRATION TEST COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_google_places_integration())

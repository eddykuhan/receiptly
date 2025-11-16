#!/usr/bin/env python3
"""
Integration test to verify Tesseract location data overrides Azure Document Intelligence.
"""
import asyncio
import httpx
import json
import sys


async def test_integration():
    """Test the full integration with Tesseract override."""
    print("=" * 80)
    print("TESSERACT OVERRIDE INTEGRATION TEST")
    print("=" * 80)
    
    # Test receipt URL
    test_url = "https://receiptly-staging-receipts.s3.ap-southeast-1.amazonaws.com/users/default-user/receipts/2025/11/16/2674f091-e50b-40e5-adce-e87f21256dac/receipt_1763255767554.jpg?X-Amz-Expires=3600&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA5ZJTSBRRPR56Z6XY%2F20251116%2Fap-southeast-1%2Fs3%2Faws4_request&X-Amz-Date=20251116T012320Z&X-Amz-SignedHeaders=host&X-Amz-Signature=00d4fefec53fe4543399f09baa1b72f7d8ac18a8b651c2ecb617e021468338b0"
    
    print(f"\n📥 Test Image: {test_url[:80]}...")
    
    # Call the analyze endpoint
    api_url = "http://localhost:8000/api/v1/ocr/analyze"
    
    payload = {
        "image_url": test_url,
        "extract_location": True
    }
    
    print(f"\n🚀 Calling API: {api_url}")
    print(f"   With payload: extract_location=True\n")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
        
        print("=" * 80)
        print("✅ API RESPONSE RECEIVED")
        print("=" * 80)
        
        # Check if successful
        if not result.get('success'):
            print("❌ FAILED: API returned success=False")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return
        
        print("\n✅ Success: True")
        
        # Display Tesseract location data
        print("\n" + "─" * 80)
        print("📍 TESSERACT LOCATION DATA (Extracted)")
        print("─" * 80)
        
        location = result.get('location', {}).get('location', {})
        if location:
            print(f"Store Name:    {location.get('store_name', 'N/A')}")
            print(f"Address:       {location.get('address', 'N/A')}")
            print(f"Phone:         {location.get('phone', 'N/A')}")
            print(f"Postal Code:   {location.get('postal_code', 'N/A')}")
            print(f"Country:       {location.get('country', 'N/A')}")
            print(f"Confidence:    {location.get('confidence', 0) * 100:.0f}%")
            
            strategy = result.get('location', {}).get('strategy_used', 'N/A')
            print(f"Strategy Used: {strategy}")
        else:
            print("❌ No location data extracted")
        
        # Display Azure data with Tesseract overrides
        print("\n" + "─" * 80)
        print("📄 AZURE DOCUMENT INTELLIGENCE DATA (After Override)")
        print("─" * 80)
        
        azure_data = result.get('data', {})
        fields = azure_data.get('fields', {})
        
        # Check merchant fields
        merchant_name = fields.get('MerchantName', {})
        merchant_address = fields.get('MerchantAddress', {})
        merchant_phone = fields.get('MerchantPhoneNumber', {})
        
        print("\n🏪 Merchant Information:")
        if merchant_name:
            print(f"  Name:       {merchant_name.get('value', 'N/A')}")
            print(f"    Source:   {merchant_name.get('source', 'azure')}")
            print(f"    Confidence: {merchant_name.get('confidence', 0) * 100:.0f}%")
        else:
            print("  Name:       Not found")
        
        if merchant_address:
            print(f"  Address:    {merchant_address.get('value', 'N/A')}")
            print(f"    Source:   {merchant_address.get('source', 'azure')}")
            print(f"    Confidence: {merchant_address.get('confidence', 0) * 100:.0f}%")
        else:
            print("  Address:    Not found")
        
        if merchant_phone:
            print(f"  Phone:      {merchant_phone.get('value', 'N/A')}")
            print(f"    Source:   {merchant_phone.get('source', 'azure')}")
            print(f"    Confidence: {merchant_phone.get('confidence', 0) * 100:.0f}%")
        else:
            print("  Phone:      Not found")
        
        # Check metadata
        metadata = azure_data.get('metadata', {})
        loc_extraction = metadata.get('location_extraction', {})
        
        if loc_extraction:
            print("\n🔍 Location Extraction Metadata:")
            print(f"  Postal Code: {loc_extraction.get('postal_code', 'N/A')}")
            print(f"  Country:     {loc_extraction.get('country', 'N/A')}")
            print(f"  Tesseract Confidence: {loc_extraction.get('tesseract_confidence', 0) * 100:.0f}%")
            print(f"  Strategy:    {loc_extraction.get('extraction_strategy', 'N/A')}")
        
        # Validation info
        print("\n" + "─" * 80)
        print("✅ VALIDATION RESULTS")
        print("─" * 80)
        
        validation = result.get('validation', {})
        print(f"Is Valid Receipt: {validation.get('is_valid_receipt', False)}")
        print(f"Confidence:       {validation.get('confidence', 0) * 100:.0f}%")
        print(f"Document Type:    {validation.get('doc_type', 'N/A')}")
        print(f"Message:          {validation.get('message', 'N/A')}")
        
        # Verify override worked
        print("\n" + "=" * 80)
        print("🔍 VERIFICATION")
        print("=" * 80)
        
        overridden = False
        if merchant_name.get('source') == 'tesseract':
            print("✅ MerchantName successfully overridden with Tesseract data")
            overridden = True
        else:
            print("⚠️  MerchantName not overridden (using Azure data or not found)")
        
        if merchant_address.get('source') == 'tesseract':
            print("✅ MerchantAddress successfully overridden with Tesseract data")
            overridden = True
        else:
            print("⚠️  MerchantAddress not overridden (using Azure data or not found)")
        
        if merchant_phone.get('source') == 'tesseract':
            print("✅ MerchantPhoneNumber successfully added from Tesseract data")
            overridden = True
        else:
            print("⚠️  MerchantPhoneNumber not added from Tesseract")
        
        if overridden:
            print("\n🎉 SUCCESS: Tesseract data is overriding Azure fields!")
        else:
            print("\n⚠️  WARNING: No Tesseract overrides detected")
        
        # Optional: Save full response for debugging
        print("\n" + "─" * 80)
        print("💾 Full Response (saved to test_output.json)")
        print("─" * 80)
        
        with open('test_output.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("✅ Saved to: test_output.json")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED")
        print("=" * 80)
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_integration())

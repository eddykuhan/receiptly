"""
Test LLM Enhancement Feature

This script demonstrates the LLM enhancement capability that improves
Azure Document Intelligence OCR results using GPT-4 Vision.
"""

import asyncio
import httpx
import json
from pathlib import Path


async def test_llm_enhancement():
    """
    Test the LLM enhancement feature with a real receipt.
    
    This example shows how LLM can:
    1. Expand truncated item names
    2. Remove non-product items (baskets, bags)
    3. Add missing items
    4. Fix prices and quantities
    """
    
    # Test receipt URL (replace with your test image)
    test_receipt_url = "https://example.com/receipt.jpg"
    
    print("=" * 60)
    print("LLM ENHANCEMENT TEST")
    print("=" * 60)
    
    # Test 1: WITHOUT LLM Enhancement (Azure only)
    print("\n📊 Test 1: Azure OCR Only (No LLM)")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/analyze",
            json={
                "image_url": test_receipt_url,
                "extract_location": True,
                "auto_crop": True,
                "enable_llm_enhancement": False  # Disabled
            }
        )
        
        azure_only = response.json()
        
        # Display results
        items = azure_only['data']['fields'].get('Items', {}).get('value', [])
        total = azure_only['data']['fields'].get('Total', {}).get('value', 0.0)
        confidence = azure_only['validation']['overall_confidence']
        
        print(f"Merchant: {azure_only['data'].get('merchant_name', 'Unknown')}")
        print(f"Items detected: {len(items)}")
        print(f"Total: ${total:.2f}")
        print(f"Confidence: {confidence:.2%}\n")
        
        print("Items:")
        for i, item in enumerate(items, 1):
            name = item.get('Description', {}).get('value', 'Unknown')
            price = item.get('TotalPrice', {}).get('value', 0.0)
            qty = item.get('Quantity', {}).get('value', 1)
            print(f"  {i}. {name} (x{qty}) - ${price:.2f}")
    
    # Test 2: WITH LLM Enhancement
    print("\n\n🤖 Test 2: Azure OCR + LLM Enhancement")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://localhost:8000/analyze",
            json={
                "image_url": test_receipt_url,
                "extract_location": True,
                "auto_crop": True,
                "enable_llm_enhancement": True  # ENABLED
            }
        )
        
        enhanced = response.json()
        
        # Display results
        items = enhanced['data']['fields'].get('Items', {}).get('value', [])
        total = enhanced['data']['fields'].get('Total', {}).get('value', 0.0)
        confidence = enhanced['validation']['overall_confidence']
        sources = enhanced['validation']['sources_used']
        
        print(f"Merchant: {enhanced['data'].get('merchant_name', 'Unknown')}")
        print(f"Items detected: {len(items)}")
        print(f"Total: ${total:.2f}")
        print(f"Confidence: {confidence:.2%}")
        print(f"Sources: {', '.join(sources)}\n")
        
        print("Items:")
        for i, item in enumerate(items, 1):
            name = item.get('Description', {}).get('value', 'Unknown')
            price = item.get('TotalPrice', {}).get('value', 0.0)
            qty = item.get('Quantity', {}).get('value', 1)
            print(f"  {i}. {name} (x{qty}) - ${price:.2f}")
        
        # Show LLM corrections
        if 'llm_corrections' in enhanced and enhanced['llm_corrections']:
            print("\n✨ LLM Corrections Made:")
            for correction in enhanced['llm_corrections']:
                field = correction['field']
                original = correction['original']
                corrected = correction['corrected']
                reason = correction['reason']
                conf = correction['confidence']
                
                print(f"\n  Field: {field}")
                print(f"  Original: {original}")
                print(f"  Corrected: {corrected}")
                print(f"  Reason: {reason}")
                print(f"  Confidence: {conf:.2%}")
        
        # Show stats
        if 'stats' in enhanced:
            stats = enhanced['stats']
            print("\n📈 Enhancement Statistics:")
            print(f"  Items added: {stats.get('items_added', 0)}")
            print(f"  Items removed: {stats.get('items_removed', 0)}")
            print(f"  Total corrections: {stats.get('corrections_made', 0)}")
    
    # Comparison
    print("\n\n📊 COMPARISON SUMMARY")
    print("=" * 60)
    
    azure_items = len(azure_only['data']['fields'].get('Items', {}).get('value', []))
    enhanced_items = len(enhanced['data']['fields'].get('Items', {}).get('value', []))
    azure_conf = azure_only['validation']['overall_confidence']
    enhanced_conf = enhanced['validation']['overall_confidence']
    
    print(f"Items count:")
    print(f"  Azure only: {azure_items}")
    print(f"  With LLM: {enhanced_items}")
    print(f"  Difference: {enhanced_items - azure_items:+d}")
    
    print(f"\nConfidence:")
    print(f"  Azure only: {azure_conf:.2%}")
    print(f"  With LLM: {enhanced_conf:.2%}")
    print(f"  Improvement: {(enhanced_conf - azure_conf):.2%}")
    
    print("\n" + "=" * 60)


async def test_direct_llm_service():
    """
    Test calling the LLM service directly (for debugging).
    """
    print("\n\n🔧 Direct LLM Service Test")
    print("=" * 60)
    
    # Mock Azure result
    azure_result = {
        "fields": {
            "MerchantName": {"value": "MYDIN", "confidence": 0.95},
            "Items": {
                "value": [
                    {
                        "Description": {"value": "MILO ACT"},
                        "Quantity": {"value": 1},
                        "TotalPrice": {"value": 19.99}
                    },
                    {
                        "Description": {"value": "BASKET"},
                        "Quantity": {"value": 1},
                        "TotalPrice": {"value": 0.00}
                    }
                ]
            },
            "Total": {"value": 19.99}
        }
    }
    
    # Read test image
    test_image_path = Path("receipts/test_receipt.jpg")
    if not test_image_path.exists():
        print(f"❌ Test image not found: {test_image_path}")
        print("   Please place a test receipt image at receipts/test_receipt.jpg")
        return
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    
    print("Calling LLM service...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {"file": ("receipt.jpg", image_bytes, "image/jpeg")}
        data = {
            "body": json.dumps({
                "azure_result": azure_result,
                "options": None  # Use defaults
            })
        }
        
        response = await client.post(
            "http://localhost:8001/enhance_receipt",
            files=files,
            data=data
        )
        
        result = response.json()
        
        print("\n✅ LLM Enhancement Result:")
        print(json.dumps(result, indent=2))


async def main():
    """Run all tests."""
    try:
        # Test 1: Full integration test
        await test_llm_enhancement()
        
        # Test 2: Direct LLM service test
        # await test_direct_llm_service()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║      LLM Receipt Enhancement Test Suite               ║
    ║                                                        ║
    ║  This demonstrates how LLM can improve Azure OCR:     ║
    ║  • Expand truncated item names                        ║
    ║  • Remove non-product items (baskets, bags)          ║
    ║  • Add missing items                                  ║
    ║  • Fix price/quantity errors                         ║
    ║  • Validate totals                                    ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())

"""Step 7: LLM Enhancement (Location, Date, Items)"""

from typing import Optional, Dict, Any
from ...services.llm_client import LlmServiceClient
from ...services.store_location_service import StoreLocationService
from ...utils.debug import ImageDebugger


class LLMEnhancementStep:
    """Step 7: LLM Enhancement (Location, Date, Items)"""
    
    def __init__(self):
        self.llm_client = LlmServiceClient()
        self.location_service = StoreLocationService()
    
    async def execute(
        self,
        result: Dict[str, Any],
        original_image_bytes: bytes,
        extract_location: bool = True,
        debugger: Optional[ImageDebugger] = None
    ) -> Dict[str, Any]:
        """
        Single LLM call for location extraction, date extraction, and item enhancement.
        
        Args:
            result: Azure analysis result
            original_image_bytes: Original uncropped image
            extract_location: Whether to extract location
            debugger: Optional debugger instance
            
        Returns:
            Enhanced result with location, date, and items
        """
        print("Step 7️⃣: LLM Enhancement...")
        
        try:
            print("  🔍 Requesting LLM for location, date, and item enhancement...")
            enhancement = await self.llm_client.enhance_receipt(
                azure_result=result,
                image_bytes=original_image_bytes,
                options={
                    "extract_location": extract_location,
                    "extract_transaction_date": True,
                    "expand_item_names": True,
                    "add_missing_items": True,
                    "remove_non_products": True,
                    "fix_quantities": True,
                    "validate_prices": True,
                    "validate_total": True
                }
            )
            
            if not enhancement:
                print("  ⚠️ No enhancement response")
                return result
            
            # Step 7a: Process location extraction
            result = await self._process_location(
                result, 
                enhancement, 
                debugger
            )
            
            # Step 7b: Process item enhancement
            result = await self._process_items(
                result, 
                enhancement, 
                debugger
            )
            
            # Step 7c: Propagate forgery analysis
            if 'forgery_analysis' in enhancement:
                result['forgery_analysis'] = enhancement['forgery_analysis']
            
            return result
            
        except Exception as e:
            print(f"  ❌ LLM Enhancement failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return result
    
    async def _process_location(
        self,
        result: Dict[str, Any],
        enhancement: Dict[str, Any],
        debugger: Optional[ImageDebugger] = None
    ) -> Dict[str, Any]:
        """Process location extraction from LLM response"""
        
        if not enhancement.get('location'):
            return result
        
        location_info = enhancement['location']
        print(f"  🗺️ Location extracted:")
        print(f"     Store: {location_info.get('merchant_name')}")
        print(f"     Address: {location_info.get('merchant_address', '')[:50]}")
        print(f"     Date: {location_info.get('transaction_datetime')}")
        
        # Apply location data to result fields
        if location_info.get('merchant_name'):
            result['fields']['MerchantName'] = {
                'type': 'string',
                'value': location_info['merchant_name'],
                'content': location_info['merchant_name'],
                'confidence': location_info.get('confidence', 0.9),
                'source': 'llm_vision'
            }
        
        if location_info.get('merchant_address'):
            result['fields']['MerchantAddress'] = {
                'type': 'string',
                'value': location_info['merchant_address'],
                'content': location_info['merchant_address'],
                'confidence': location_info.get('confidence', 0.9),
                'source': 'llm_vision'
            }
        
        if location_info.get('merchant_phone'):
            result['fields']['MerchantPhoneNumber'] = {
                'type': 'phoneNumber',
                'value': location_info['merchant_phone'],
                'content': location_info['merchant_phone'],
                'confidence': location_info.get('confidence', 0.9),
                'source': 'llm_vision'
            }
        
        if location_info.get('transaction_datetime'):
            result['fields']['TransactionDate'] = {
                'type': 'date',
                'value': location_info['transaction_datetime'],
                'content': location_info['transaction_datetime'],
                'confidence': 0.90,
                'source': 'llm_vision'
            }
        
        # Run Google Places verification
        if location_info.get('merchant_name'):
            result = await self._verify_with_google_places(
                result,
                location_info,
                debugger
            )
        
        if debugger:
            debugger.save_json(location_info, "06_location_from_llm")
        
        return result
    
    async def _verify_with_google_places(
        self,
        result: Dict[str, Any],
        location_info: Dict[str, Any],
        debugger: Optional[ImageDebugger] = None
    ) -> Dict[str, Any]:
        """Verify location with Google Places"""
        
        merchant_name = location_info.get('merchant_name', '')
        merchant_address = location_info.get('merchant_address', '')
        merchant_phone = location_info.get('merchant_phone')
        
        print(f"  🔍 Verifying with Google Places...")
        print(f"     Store: {merchant_name}")
        print(f"     Address: {merchant_address}")
        print(f"     Phone: {merchant_phone or 'N/A'}")
        
        try:
            google_match = self.location_service.find_best_match(
                store_name=merchant_name,
                partial_address=merchant_address,
                phone=merchant_phone,
                min_confidence=0.70
            )
            
            if google_match:
                print(f"  ✅ Match found: {google_match['branch_name']} (confidence: {google_match['confidence']:.2f})")
                
                if google_match['confidence'] >= 0.80:
                    print(f"  ✅ Google Places verified: {google_match['branch_name']}")
                    result['fields']['MerchantAddress'] = {
                        'type': 'string',
                        'value': google_match['address'],
                        'content': google_match['address'],
                        'confidence': google_match['confidence'],
                        'source': 'google_places'
                    }
                    
                    # Add metadata
                    if 'metadata' not in result:
                        result['metadata'] = {}
                    result['metadata']['google_places_match'] = True
                    result['metadata']['match_confidence'] = google_match['confidence']
                    result['metadata']['matched_branch'] = google_match['branch_name']
                    result['metadata']['latitude'] = google_match['latitude']
                    result['metadata']['longitude'] = google_match['longitude']
                else:
                    print(f"  ⚠️ Match confidence {google_match['confidence']:.2f} below threshold 0.80")
                    print(f"     Match: {google_match['branch_name']}")
            else:
                print(f"  ⚠️ No matching store found in database for '{merchant_name}'")
                
        except Exception as e:
            print(f"  ⚠️ Google Places verification failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result
    
    async def _process_items(
        self,
        result: Dict[str, Any],
        enhancement: Dict[str, Any],
        debugger: Optional[ImageDebugger] = None
    ) -> Dict[str, Any]:
        """Process item enhancement from LLM response"""
        
        if not enhancement.get('enhanced_result'):
            return result
        
        enhanced_fields = enhancement['enhanced_result'].get('fields', {})
        
        if not enhanced_fields.get('Items'):
            return result
        
        enhanced_items = enhanced_fields['Items'].get('value', [])
        
        if not enhanced_items:
            print("  ⚠️ No enhanced items")
            return result
        
        # Merge enhanced items with Azure structure
        azure_items = result['fields'].get('Items', {}).get('value', [])
        merged_items = []
        
        for i, enhanced_item in enumerate(enhanced_items):
            if i < len(azure_items):
                # Update existing item
                azure_item = azure_items[i]
                if azure_item.get('value_type') == 'dictionary' and azure_item.get('value'):
                    item_data = azure_item['value']
                else:
                    item_data = {}
                
                # Update with enhanced values
                if 'Description' in enhanced_item:
                    if 'Description' not in item_data:
                        item_data['Description'] = {}
                    item_data['Description']['value'] = enhanced_item['Description']['value']
                
                if 'Quantity' in enhanced_item:
                    if 'Quantity' not in item_data:
                        item_data['Quantity'] = {}
                    item_data['Quantity']['value'] = enhanced_item['Quantity']['value']
                
                if 'TotalPrice' in enhanced_item:
                    if 'TotalPrice' not in item_data:
                        item_data['TotalPrice'] = {}
                    item_data['TotalPrice']['value'] = enhanced_item['TotalPrice']['value']
                
                azure_item['value'] = item_data
                merged_items.append(azure_item)
            else:
                # New item added by LLM
                merged_items.append({
                    "value_type": "dictionary",
                    "value": {
                        "Description": {
                            "value_type": "string",
                            "value": enhanced_item['Description']['value'],
                            "confidence": enhanced_item.get('confidence', 0.9)
                        },
                        "Quantity": {
                            "value_type": "float",
                            "value": enhanced_item['Quantity']['value'],
                            "confidence": enhanced_item.get('confidence', 0.9)
                        },
                        "TotalPrice": {
                            "value_type": "float",
                            "value": enhanced_item['TotalPrice']['value'],
                            "confidence": enhanced_item.get('confidence', 0.9)
                        }
                    },
                    "confidence": enhanced_item.get('confidence', 0.9)
                })
        
        result['fields']['Items']['value'] = merged_items
        
        corrections = enhancement.get('corrections', [])
        print(f"  ✨ Enhanced items: {len(merged_items)}")
        print(f"     Corrections: {len(corrections)}")
        print(f"     Added: {enhancement.get('stats', {}).get('items_added', 0)}")
        print(f"     Removed: {enhancement.get('stats', {}).get('items_removed', 0)}")
        
        if debugger:
            debugger.save_json(enhancement, "06b_llm_enhancement")
        
        return result

"""Step 6: Location Candidates Collection"""

from typing import Optional, Dict, Any, List
from ...services.llm_client import LlmServiceClient
from ...utils.debug import ImageDebugger


class LocationCandidatesStep:
    """Step 6: Collect location candidates from multiple sources"""
    
    def __init__(self):
        self.llm_client = LlmServiceClient()
    
    async def execute(
        self,
        azure_result: Dict[str, Any],
        image_bytes: bytes,
        debugger: Optional[ImageDebugger] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect location candidates from Azure and LLM Vision.
        
        Args:
            azure_result: Azure analysis result
            image_bytes: Original uncropped image bytes
            debugger: Optional debugger instance
            
        Returns:
            List of location candidates with metadata
        """
        print("Step 6️⃣: Collecting location candidates...")
        
        candidates = []
        
        # Candidate 1: Azure Document Intelligence
        candidates.extend(self._get_azure_candidates(azure_result))
        
        # Candidate 2: LLM Vision extraction
        candidates = await self._add_llm_candidates(
            candidates,
            azure_result,
            image_bytes,
            debugger
        )
        
        print(f"  ✅ Collected {len(candidates)} location candidates")
        
        if debugger:
            debugger.save_json(candidates, "06_location_candidates")
        
        return candidates
    
    def _get_azure_candidates(
        self,
        azure_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract location candidates from Azure result"""
        
        candidates = []
        fields = azure_result.get('fields', {})
        
        # Extract field values safely
        def get_field_value(field_data, default=''):
            if isinstance(field_data, dict):
                return field_data.get('value', default)
            return str(field_data) if field_data else default
        
        azure_merchant = fields.get('MerchantName', {})
        azure_address = fields.get('MerchantAddress', {})
        azure_phone = fields.get('MerchantPhoneNumber', {})
        
        merchant_value = get_field_value(azure_merchant)
        address_value = get_field_value(azure_address)
        phone_value = get_field_value(azure_phone)
        confidence = azure_merchant.get('confidence', 0.0) if isinstance(azure_merchant, dict) else 0.0
        
        if merchant_value and len(merchant_value.strip()) >= 2:
            candidates.append({
                "store_name": merchant_value,
                "address": address_value or None,
                "phone": phone_value or None,
                "postal_code": None,
                "source": "azure",
                "confidence": confidence,
                "metadata": {"method": "Azure Document Intelligence"}
            })
            print(f"  📋 Candidate {len(candidates)-1} (Azure): {merchant_value}")
        
        return candidates
    
    async def _add_llm_candidates(
        self,
        candidates: List[Dict[str, Any]],
        azure_result: Dict[str, Any],
        image_bytes: bytes,
        debugger: Optional[ImageDebugger] = None
    ) -> List[Dict[str, Any]]:
        """Extract and add LLM Vision candidates"""
        
        try:
            llm_result = await self.llm_client.extract_merchant_from_image(image_bytes)
            
            if not llm_result or not llm_result.get('success'):
                return candidates
            
            llm_store = llm_result.get('merchant_name', '').strip()
            llm_address = llm_result.get('merchant_address', '').strip()
            llm_datetime = llm_result.get('transaction_datetime', '').strip()
            
            if llm_store and len(llm_store) >= 2:
                # Check if store name is different from Azure (avoid duplicates)
                existing_names = [c['store_name'].lower() for c in candidates]
                
                if llm_store.lower() not in existing_names:
                    # Add as new candidate
                    candidates.append({
                        "store_name": llm_store,
                        "address": llm_address if llm_address else None,
                        "phone": None,
                        "postal_code": None,
                        "transaction_datetime": llm_datetime if llm_datetime else None,
                        "source": "llm_vision",
                        "confidence": 0.9,
                        "metadata": {"method": "GPT-4 Vision"}
                    })
                    print(f"  📋 Candidate {len(candidates)-1} (LLM Vision): {llm_store}")
                    if llm_datetime:
                        print(f"     Transaction DateTime: {llm_datetime}")
                else:
                    # Enhance existing Azure candidate with LLM data
                    for c in candidates:
                        if c['store_name'].lower() == llm_store.lower():
                            if llm_address and (not c.get('address') or len(llm_address) > len(c.get('address', ''))):
                                c['address'] = llm_address
                                print(f"  📝 Enhanced with LLM address: {llm_address[:50]}...")
                            if llm_datetime and not c.get('transaction_datetime'):
                                c['transaction_datetime'] = llm_datetime
                                print(f"  📝 Enhanced with LLM datetime: {llm_datetime}")
                            break
        except Exception as e:
            print(f"  ⚠️ LLM Vision extraction failed: {str(e)}")
        
        return candidates
    
    def select_best_candidate(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Select best candidate based on confidence and source priority"""
        
        if not candidates:
            return None
        
        # Sort by source priority (LLM > Azure) then confidence
        def candidate_priority(c):
            source_priority = 1 if c.get('source') == 'llm_vision' else 0
            return (source_priority, c.get('confidence', 0.0))
        
        sorted_candidates = sorted(candidates, key=candidate_priority, reverse=True)
        selected = sorted_candidates[0]
        
        print(f"  ✨ Selected: {selected['source']} (confidence: {selected.get('confidence', 0.0):.2f})")
        
        return selected

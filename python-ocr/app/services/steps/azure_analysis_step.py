"""Step 5: Azure Document Intelligence Analysis"""

from typing import Optional, Dict, Any
from ...services.document_intelligence import DocumentIntelligenceService
from ...utils.debug import ImageDebugger


class AzureAnalysisStep:
    """Step 5: Azure Document Intelligence Analysis"""
    
    def __init__(self, doc_service: DocumentIntelligenceService):
        self.doc_service = doc_service
    
    async def execute(
        self,
        file_bytes: bytes,
        debugger: Optional[ImageDebugger] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send cropped image to Azure Document Intelligence.
        
        Args:
            file_bytes: Image bytes
            debugger: Optional debugger instance
            
        Returns:
            Azure analysis result as dict
        """
        print("Step 5️⃣: Azure Document Intelligence Analysis...")
        
        receipt = await self.doc_service._analyze_document(file_bytes)
        
        if not receipt:
            print("  ❌ No receipt data found")
            if debugger:
                debugger.save_json({"error": "No receipt data found"}, "05_azure_result")
            return None
        
        result = receipt.to_dict()
        print(f"  ✓ Extracted data")
        print(f"    - Store: {result.get('fields', {}).get('MerchantName', {}).get('value', 'N/A')}")
        print(f"    - Items: {len(result.get('fields', {}).get('Items', {}).get('value', []))}")
        
        if debugger:
            debugger.save_json(result, "05_azure_result", {
                "merchant_name": result.get("merchant_name"),
                "merchant_address": result.get("merchant_address")
            })
        
        return result

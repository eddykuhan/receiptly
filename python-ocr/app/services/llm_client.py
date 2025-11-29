import httpx
from typing import List, Dict, Any, Optional

class LlmServiceClient:
    """Client for calling the LLM microservice."""
    
    def __init__(self, base_url: str = "http://localhost:8500"):
        self.base_url = base_url
        self.timeout = 30.0  # 30 second timeout for LLM calls
    
    async def select_best_location(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Call LLM service to select the best location from multiple candidates.
        
        Args:
            candidates: List of location candidate dictionaries
            
        Returns:
            {
                "selected_index": int,
                "reasoning": str,
                "confidence": float
            }
            or None if the call fails
        """
        if not candidates:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/select_best_location",
                    json={"candidates": candidates}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"⚠️ LLM service call failed: {str(e)}")
            return None

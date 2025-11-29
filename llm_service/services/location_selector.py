from models.llm_client import LLMClient

llm = LLMClient()

SYSTEM_PROMPT = """
You are an expert at analyzing OCR-extracted location data from receipts.
You will receive multiple location candidates extracted using different strategies.

**IMPORTANT PARSING RULES:**
1. Store names and addresses are often MIXED together in OCR output
2. Store name is usually a BRAND (e.g., "99 Speedmart", "MYDIN", "7-Eleven", "Lotus's")
3. Address/Location is usually a PLACE (e.g., "Gravitas Business Park", "Bukit Mertajam", "Penang E-Gate")
4. Common patterns:
   - "99 SPEED 2868-PG GRAVITAS BUSINESS PARK" → Store: "99 Speedmart", Location: "Gravitas Business Park"
   - "MYDIN BKT MERTAJAM" → Store: "MYDIN", Location: "Bukit Mertajam"
   - "LOTUS'S PENANG EGATE" → Store: "LOTUS'S", Location: "Penang E-Gate"

**CRITICAL: Source-Specific Strengths:**
- **Azure**: Usually provides the MOST ACCURATE merchant/store name (high confidence, full legal name)
- **EasyOCR**: Better at extracting ADDRESS/LOCATION data from receipt headers
- **Fallback**: Provides fuzzy-matched brand names

**Your task is to COMBINE the best parts from different candidates:**
1. **Select the best STORE NAME** (usually from Azure if available and confident)
2. **Select the best ADDRESS** (often from EasyOCR or other candidates)
3. **Parse mixed data** to separate store names from locations
4. **Prioritize completeness** - combine fields from multiple candidates if needed

**Selection Strategy:**
- For STORE NAME: Prefer Azure if confidence > 0.8, otherwise use the clearest brand name
- For ADDRESS: Use any candidate that has address data (EasyOCR often has this)
- Parse and clean mixed data to extract proper store names and locations
- Combine phone, postal code from any available source

Return ONLY a JSON object with:
{
    "best_store_name_index": <index of candidate with best store name>,
    "best_address_index": <index of candidate with best address (can be different from store name)>,
    "parsed_store_name": "<final cleaned store brand name>",
    "parsed_location": "<final cleaned location/address>",
    "reasoning": "<explain: 1) Why you chose this store name source 2) Why you chose this address source 3) Any parsing you did>",
    "confidence": <0.0-1.0 score for your combined selection>
}
"""

async def select_best_location(candidates: list[dict]) -> dict:
    """
    Use LLM to select the best location candidate from multiple OCR strategies.
    
    Args:
        candidates: List of location candidate dictionaries
        
    Returns:
        {
            "selected_index": int,
            "reasoning": str,
            "confidence": float
        }
    """
    if not candidates:
        return {
            "selected_index": -1,
            "reasoning": "No candidates provided",
            "confidence": 0.0
        }
    
    if len(candidates) == 1:
        return {
            "selected_index": 0,
            "reasoning": "Only one candidate available",
            "confidence": candidates[0].get("confidence", 0.5)
        }
    
    # Format candidates for LLM
    candidates_text = ""
    for i, candidate in enumerate(candidates):
        candidates_text += f"\n--- Candidate {i} ---\n"
        candidates_text += f"Source: {candidate.get('source', 'unknown')}\n"
        candidates_text += f"Store Name: {candidate.get('store_name', 'N/A')}\n"
        candidates_text += f"Address: {candidate.get('address', 'N/A')}\n"
        candidates_text += f"Phone: {candidate.get('phone', 'N/A')}\n"
        candidates_text += f"Postal Code: {candidate.get('postal_code', 'N/A')}\n"
        candidates_text += f"Confidence: {candidate.get('confidence', 0.0)}\n"
    
    user_prompt = f"Select the best location candidate from the following:\n{candidates_text}\n\nReturn JSON only."
    print(f"Invoking LLM for location selection...")
    print(f"User prompt:\n{user_prompt}")

    try:
        response = await llm.chat(SYSTEM_PROMPT, user_prompt)
        
        # Parse JSON response
        import json
        result = json.loads(response)
        
        # Validate response - now supports combining from multiple candidates
        if "best_store_name_index" not in result:
            raise ValueError("LLM response missing 'best_store_name_index'")
        
        store_idx = result["best_store_name_index"]
        address_idx = result.get("best_address_index", store_idx)
        
        if store_idx < 0 or store_idx >= len(candidates):
            raise ValueError(f"Invalid best_store_name_index: {store_idx}")
        if address_idx < 0 or address_idx >= len(candidates):
            raise ValueError(f"Invalid best_address_index: {address_idx}")
        
        # Add backward compatibility field
        result["selected_index"] = store_idx
        
        return result
        
    except Exception as e:
        print(f"LLM selection failed: {e}")
        # Fallback: select candidate with highest confidence
        best_idx = max(range(len(candidates)), key=lambda i: candidates[i].get("confidence", 0.0))
        return {
            "selected_index": best_idx,
            "best_store_name_index": best_idx,
            "best_address_index": best_idx,
            "reasoning": f"Fallback: Selected highest confidence candidate (LLM error: {str(e)})",
            "confidence": candidates[best_idx].get("confidence", 0.5)
        }

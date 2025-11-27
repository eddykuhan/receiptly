# 📍 Store Address Matching Strategy

## Problem Statement

Currently, the receipt OCR extracts `StoreAddress` from receipt images, but this data can be:
- **Inaccurate** - OCR misreads text (e.g., "09556057664289 cP6_CoMMOR" instead of actual address)
- **Incomplete** - Missing postal codes, city names, or full street addresses
- **Inconsistent** - Different formatting across receipts from the same store
- **Low confidence** - EasyOCR/Tesseract may have low confidence scores

**Now that we have accurate Google Places API data**, we can significantly improve address accuracy by matching OCR-extracted store names to our location database.

---

## Solution Overview

### 🎯 Strategy: Fuzzy Matching + Geocoding

1. **Extract store name from receipt** (already working via Azure + EasyOCR)
2. **Fuzzy match** the store name against our Google Places database
3. **If multiple matches**, use additional signals:
   - Partial address match (city, postal code)
   - Phone number match
   - GPS coordinates (if available from user's device)
4. **Replace OCR address** with the matched Google Places address
5. **Store coordinates** for map visualization

---

## Implementation Plan

### Phase 1: Create Store Location Database Service

**File**: `python-ocr/app/services/store_location_service.py`

This service will:
- Load all store location JSON files
- Provide fuzzy matching capabilities
- Return best match with confidence score
- Handle multiple stores (Jaya Grocer, Mydin, Lotus's, AEON, Village Grocer)

```python
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz
import json
import os

class StoreLocationService:
    def __init__(self, data_directory: str = "data"):
        self.locations = self._load_all_locations(data_directory)
    
    def find_best_match(
        self,
        store_name: str,
        partial_address: Optional[str] = None,
        phone: Optional[str] = None,
        postal_code: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Find the best matching store location.
        
        Returns:
            {
                'store_name': 'Jaya Grocer',
                'branch_name': 'Jaya Grocer @ Gurney Paragon',
                'address': 'Full Google Places address',
                'latitude': 5.4356179,
                'longitude': 100.31110749999999,
                'phone': '04-291 9883',
                'confidence': 0.95,
                'match_reason': 'Exact store name + phone match'
            }
        """
        pass
```

### Phase 2: Integrate into OCR Pipeline

**File**: `python-ocr/app/services/receipt_processor.py`

Modify the receipt processing workflow:

```python
# Current flow:
1. Azure extracts MerchantName + MerchantAddress
2. EasyOCR fallback if confidence low
3. Return extracted data

# New flow:
1. Azure extracts MerchantName + MerchantAddress
2. EasyOCR fallback if confidence low
3. **NEW: Fuzzy match store name against Google Places DB**
4. **NEW: If match found (confidence > 0.8), replace address with Google data**
5. Return enhanced data with coordinates
```

### Phase 3: Update .NET API to Store Coordinates

**File**: `dotnet-api/src/Receiptly.Infrastructure/Services/ReceiptProcessingService.cs`

Extract and store latitude/longitude from OCR metadata:

```csharp
// Extract coordinates (from Google Places match)
if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("latitude", out var lat))
{
    if (double.TryParse(lat?.ToString(), out var latitude))
    {
        receipt.Latitude = latitude;
    }
}

if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("longitude", out var lng))
{
    if (double.TryParse(lng?.ToString(), out var longitude))
    {
        receipt.Longitude = longitude;
    }
}
```

---

## Matching Algorithm

### Confidence Scoring System

| Match Type | Confidence | Example |
|------------|-----------|---------|
| **Exact name + phone** | 0.95 | "Jaya Grocer" + "04-291 9883" |
| **Exact name + postal code** | 0.90 | "Mydin" + "13700" |
| **Fuzzy name (>90%) + city** | 0.85 | "Lotus's" + "Penang" |
| **Fuzzy name (>80%)** | 0.70 | "Jaya Groc" → "Jaya Grocer" |
| **Fuzzy name (<80%)** | 0.50 | "JG" → "Jaya Grocer" |
| **No match** | 0.0 | Keep OCR address |

### Fuzzy Matching Logic

```python
def calculate_match_confidence(
    ocr_store_name: str,
    db_store_name: str,
    ocr_phone: Optional[str],
    db_phone: str,
    ocr_address: Optional[str],
    db_address: str
) -> Tuple[float, str]:
    """
    Calculate confidence score for a potential match.
    
    Returns: (confidence_score, match_reason)
    """
    
    # 1. Store name similarity
    name_ratio = fuzz.ratio(ocr_store_name.lower(), db_store_name.lower())
    
    # 2. Phone number match (if available)
    phone_match = False
    if ocr_phone and db_phone:
        # Normalize phone numbers (remove spaces, dashes, country codes)
        ocr_phone_clean = ''.join(filter(str.isdigit, ocr_phone))
        db_phone_clean = ''.join(filter(str.isdigit, db_phone))
        phone_match = ocr_phone_clean[-7:] == db_phone_clean[-7:]  # Last 7 digits
    
    # 3. Address partial match (city, postal code)
    address_match = False
    if ocr_address and db_address:
        # Check for city names, postal codes
        address_match = any(
            city in ocr_address.lower() 
            for city in extract_cities(db_address)
        )
    
    # Calculate final confidence
    if name_ratio >= 90 and phone_match:
        return (0.95, "Exact name + phone match")
    elif name_ratio >= 90 and address_match:
        return (0.90, "Exact name + address match")
    elif name_ratio >= 80:
        return (0.85, f"Strong name match ({name_ratio}%)")
    elif name_ratio >= 70:
        return (0.70, f"Moderate name match ({name_ratio}%)")
    else:
        return (0.50, f"Weak name match ({name_ratio}%)")
```

---

## Data Flow Diagram

```
┌─────────────────────┐
│  Receipt Image      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Azure OCR          │
│  + EasyOCR Fallback │
└──────────┬──────────┘
           │
           ├─ Store Name: "Jaya Grocer"
           ├─ Address: "Gurney Paragon..." (may be inaccurate)
           ├─ Phone: "04-291 9883"
           └─ Postal Code: "10250"
           │
           ▼
┌─────────────────────────────────┐
│  Store Location Service         │
│  (Fuzzy Match)                  │
└──────────┬──────────────────────┘
           │
           ├─ Load Google Places DB
           ├─ Match "Jaya Grocer" → 20 results
           ├─ Filter by phone "04-291 9883"
           └─ Best match: Gurney Paragon (confidence: 0.95)
           │
           ▼
┌─────────────────────────────────┐
│  Enhanced Receipt Data          │
└──────────┬──────────────────────┘
           │
           ├─ Store Name: "Jaya Grocer"
           ├─ Branch: "Jaya Grocer @ Gurney Paragon"
           ├─ Address: "Lot LG 26, 26A, 27, Gurney Paragon Mall..." ✅ (from Google)
           ├─ Latitude: 5.4356179 ✅ (NEW)
           ├─ Longitude: 100.31110749999999 ✅ (NEW)
           ├─ Phone: "04-291 9883"
           └─ Match Confidence: 0.95 ✅ (NEW)
           │
           ▼
┌─────────────────────────────────┐
│  PostgreSQL Database            │
│  (Receipt table)                │
└─────────────────────────────────┘
```

---

## Benefits

### ✅ Improved Accuracy
- Replace OCR errors with verified Google Places addresses
- Consistent formatting across all receipts

### ✅ Geocoding Support
- Store latitude/longitude for map visualization
- Enable location-based features (nearby stores, spending by location)

### ✅ Better User Experience
- Show correct store branch names
- Display receipts on a map
- Suggest stores based on user's location

### ✅ Analytics Capabilities
- Track spending by store location
- Identify most visited branches
- Regional spending patterns

---

## Edge Cases & Handling

| Scenario | Handling Strategy |
|----------|------------------|
| **No match found** | Keep original OCR address, set confidence = OCR confidence |
| **Multiple matches (same confidence)** | Return first match, log warning for manual review |
| **Store not in database** | Keep OCR address, flag for database update |
| **OCR completely wrong** | Low fuzzy match score → keep OCR but mark low confidence |
| **New store branch** | No match → suggest adding to Google Places DB |

---

## Database Schema Updates

### Current Schema
```csharp
public class Receipt
{
    public string StoreAddress { get; set; } = string.Empty;
    public double? LocationConfidence { get; set; }
    // Missing: Latitude, Longitude already exist ✅
}
```

### Metadata to Add
```csharp
// In OcrResponse.Metadata (from Python OCR)
{
    "google_places_match": true,
    "match_confidence": 0.95,
    "matched_branch": "Jaya Grocer @ Gurney Paragon",
    "latitude": 5.4356179,
    "longitude": 100.31110749999999
}
```

---

## Testing Strategy

### Test Cases

1. **Exact Match**
   - OCR: "Jaya Grocer", Phone: "04-291 9883"
   - Expected: Gurney Paragon branch (confidence: 0.95)

2. **Fuzzy Match**
   - OCR: "Jaya Groc", Address contains "Penang"
   - Expected: Best Penang branch (confidence: 0.85)

3. **No Match**
   - OCR: "Unknown Kedai", No phone
   - Expected: Keep OCR address (confidence: OCR confidence)

4. **Multiple Branches**
   - OCR: "Mydin", No additional info
   - Expected: Return closest match or first result (confidence: 0.70)

5. **Wrong OCR**
   - OCR: "09556057664289 cP6_CoMMOR" (garbage)
   - Expected: No match, keep original, low confidence

---

## Next Steps

1. **Install dependencies**
   ```bash
   pip install fuzzywuzzy python-Levenshtein
   ```

2. **Create StoreLocationService**
   - Implement fuzzy matching
   - Add confidence scoring
   - Handle edge cases

3. **Integrate into OCR pipeline**
   - Call service after OCR extraction
   - Enhance response with Google Places data
   - Add metadata for .NET API

4. **Update .NET API**
   - Extract lat/lng from metadata
   - Store in database
   - Return in API responses

5. **Frontend updates** (future)
   - Display receipts on map
   - Show store branch names
   - Filter by location

---

## Example API Response (After Implementation)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "storeName": "Jaya Grocer",
  "storeAddress": "Lot LG 26, 26A, 27, Gurney Paragon Mall, 163-D, Persiaran Gurney, 10250 George Town, Pulau Pinang, Malaysia",
  "storePhoneNumber": "04-291 9883",
  "postalCode": "10250",
  "country": "Malaysia",
  "latitude": 5.4356179,
  "longitude": 100.31110749999999,
  "locationConfidence": 0.95,
  "totalAmount": 123.45,
  "purchaseDate": "2025-11-27T09:00:00Z",
  "ocrMetadata": {
    "googlePlacesMatch": true,
    "matchedBranch": "Jaya Grocer @ Gurney Paragon",
    "matchConfidence": 0.95,
    "matchReason": "Exact name + phone match"
  }
}
```

---

## Performance Considerations

- **Database size**: ~100 locations (5 stores × 20 locations each) = Fast in-memory lookup
- **Fuzzy matching**: O(n) where n = number of locations per store (~20) = Very fast
- **Caching**: Load JSON files once at startup, keep in memory
- **Scalability**: If database grows to 1000+ locations, consider:
  - PostgreSQL full-text search
  - Elasticsearch for fuzzy matching
  - Pre-computed similarity matrices

---

## Conclusion

By leveraging the Google Places API data you've extracted, we can:
1. **Dramatically improve** address accuracy
2. **Add geocoding** capabilities for map features
3. **Provide better UX** with correct branch names
4. **Enable analytics** based on store locations

The fuzzy matching approach is robust, handles OCR errors gracefully, and provides confidence scores for transparency.

**Ready to implement?** Let me know and I'll start with Phase 1! 🚀

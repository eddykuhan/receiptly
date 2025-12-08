# Transaction Date Extraction Enhancement

## Overview
Enhanced the OCR pipeline to ensure **transaction date/timestamp** is always extracted, even when Azure Document Intelligence fails. This is critical for the application's success as the date is essential for:
- Price tracking over time
- Receipt history organization
- Analytics and insights
- Duplicate detection

## Problem Statement
Azure Document Intelligence sometimes fails to extract the `TransactionDate` field from receipts, leaving this critical data missing. Without a reliable timestamp, receipts cannot be properly organized or analyzed.

## Solution Implemented

### 1. Enhanced LLM Extractor (`llm_service/services/receipt_extractor.py`)

**Changes**:
- ✅ Updated GPT-4 Vision prompt to extract transaction date/time
- ✅ **Scans BOTH top (header) AND bottom (footer)** of receipt for dates
- ✅ Handles retailers like **Watsons, Guardian** that print dates at the bottom
- ✅ Added support for multiple date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD MMM YYYY)
- ✅ Added support for time extraction (HH:MM:SS, HH:MM)
- ✅ Returns date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) when possible
- ✅ Falls back to date-only format (YYYY-MM-DD) if time is unavailable
- ✅ Prioritizes transaction date over print date when multiple dates exist

**New Prompt Instructions**:
```
7. Extract the transaction date/time from the receipt:
   - IMPORTANT: Check BOTH the top (header) AND bottom (footer) of the receipt
   - Some retailers (e.g., Watsons, Guardian, pharmacies) print the date at the BOTTOM
   - Look for date stamps in these formats:
     * DD/MM/YYYY, DD-MM-YYYY, MM/DD/YYYY
     * YYYY-MM-DD, YYYY/MM/DD
     * DD MMM YYYY (e.g., "07 Dec 2024")
   - Look for time stamps: HH:MM:SS, HH:MM
   - Common labels to look for:
     * "Date:", "Time:", "Date/Time:", "Transaction Date:"
     * "Date & Time:", "Txn Date:", "Purchase Date:"
     * Sometimes just a date/time without a label
   - Prioritize the transaction date over print date or other dates
   - If multiple dates exist, choose the one that appears to be the transaction/purchase date
```

**Response Format**:
```json
{
  "merchantName": "Mydin",
  "merchantAddress": "Bukit Mertajam, Penang, Malaysia",
  "transactionDateTime": "2024-12-07T14:30:00"
}
```

**Example: Watsons (date at bottom)**:
```json
{
  "merchantName": "Watsons",
  "merchantAddress": "Sunway Pyramid, Selangor",
  "transactionDateTime": "2024-12-07"
}
```

### 2. Updated OCR Router (`python-ocr/app/routers/ocr.py`)

**Changes**:
- ✅ Modified `collect_location_candidates()` to capture `transaction_datetime` from LLM
- ✅ Added fallback logic in `override_merchant_data_with_llm()`
- ✅ Checks Azure first, then falls back to LLM if missing
- ✅ Adds metadata flags when date is missing from all sources

**Fallback Logic Flow**:
```python
1. Check Azure Document Intelligence for TransactionDate
   ├─ If found → Use Azure date
   └─ If missing → Check LLM fallback
       ├─ If LLM extracted date → Use LLM date (confidence: 0.85)
       └─ If no date from any source → Set metadata flag for manual review
```

## Data Flow

```
Receipt Image
    ↓
Azure Document Intelligence
    ├─ Extracts: MerchantName, Address, Items, Total, TransactionDate
    ↓
Check TransactionDate
    ├─ Present? → Use Azure date ✅
    └─ Missing? → Continue to LLM fallback
        ↓
    LLM Vision (GPT-4)
        ├─ Extracts: merchantName, merchantAddress, transactionDateTime
        ↓
    Use LLM transactionDateTime as fallback
        ├─ Present? → Use LLM date ✅ (confidence: 0.85)
        └─ Missing? → Flag for manual review ⚠️
```

## Benefits

1. **Improved Data Completeness** - Significantly reduces missing transaction dates
2. **Better User Experience** - Receipts always have timestamps for proper organization
3. **Reduced Manual Intervention** - Fewer receipts requiring manual date entry
4. **Maintained Data Quality** - Source tracking allows for quality auditing

## Critical Data Checklist

For application success, ensure these fields are always extracted:

- ✅ **MerchantName** - Primary: LLM, Fallback: Azure
- ✅ **MerchantAddress** - Primary: Google Places, Fallback: LLM/Azure
- ✅ **Latitude/Longitude** - Primary: Google Places
- ✅ **TransactionDate** - Primary: Azure, Fallback: LLM ← **NEW**
- ✅ **Items & Prices** - Primary: Azure
- ✅ **Total Amount** - Primary: Azure

## Related Files Modified

1. `/llm_service/services/receipt_extractor.py` - Enhanced prompt and response
2. `/python-ocr/app/routers/ocr.py` - Added fallback logic

# OCR Accuracy Improvements

## Overview
This document outlines the improvements made to Tesseract OCR location extraction to fix common accuracy issues with store names, postal codes, and country detection.

## Issues Fixed

### 1. Country Detection Accuracy
**Problem**: System incorrectly detected "USA" for Malaysian receipts based on 5-digit postal code pattern.

**Solution**: Multi-tier country detection with priority ordering:
1. **Explicit mentions** (highest priority): "Malaysia", "Kuala Lumpur", "Selangor"
2. **Phone patterns** (high priority): `03-XXXXXXX` = Malaysia, `+65` = Singapore
3. **Postal patterns** (lower priority): Only used if no phone number found
4. **Context validation**: US ZIP codes only match with US state names

**Example**:
```
Phone: 03-2283111 → Malaysia ✓
Postal: 59200     → Validates Malaysia
Result: Malaysia (not USA)
```

### 2. Postal Code Extraction
**Problem**: Extracted invoice numbers or company registration numbers instead of actual postal codes.

**Solution**: Enhanced extraction with context awareness:
- **Address context matching**: Look for postal codes before city names
  - Pattern: `59200 KUALA LUMPUR` → Extract `59200`
- **Exclusion filters**: Skip numbers near:
  - Invoice/receipt/transaction keywords
  - Company registration (e.g., "Sdn Bhd (44047-1)")
  - VAT numbers
  - Dates
- **OCR error correction**: `$9200` → `59200`
- **Validation**: Malaysia postal codes must be 50000-99999

**Example**:
```
Text:
  Sdn Bhd ($44047-1)         ← Excluded (company reg)
  $9200 KUALA LUMPUR         ← Cleaned to 59200 ✓
  Invoice No: 200686         ← Excluded (invoice)
  
Result: 59200
```

### 3. OCR Character Misreading
**Problem**: Common OCR errors in addresses:
- `$` misread as `5` in numbers
- `O` misread as `0` in numeric contexts
- `?` misread as `7` in phone numbers
- `I` vs `1`, `|` vs `I`

**Solution**: Context-aware character correction:

#### Address Cleaning
```python
"$9200 KUALA LUMPUR"  → "59200 KUALA LUMPUR"
"16-229 , LG FLO0R"   → "16-229 , LG FLOOR"
```

#### Phone Cleaning
```python
"03-2283111?"  → "0322831117"
"O3-228311O"   → "0322831110"
```

#### Store Name Cleaning
```python
"JAYA GR|OCER"  → "JAYA GROCER"
"C1TY MART"     → "CITY MART"
```

## Implementation Details

### Enhanced Functions

#### 1. `_extract_postal_code()`
```python
# Priority 1: Labeled postal codes
r'(?:postal|post\s*code|zip)[:\s]+([A-Z0-9\s-]{4,10})'

# Priority 2: Address context (Malaysia)
r'[$5-9]?\d{4,5}\s+(?:kuala\s+lumpur|kl|selangor|penang)'

# Priority 3: Pattern matching with exclusions
- Exclude: invoice, VAT, company reg, dates
- Clean: $ → 5, O → 0
- Validate: 50000-99999 range for Malaysia
```

#### 2. `_detect_country()`
```python
# Priority 1: Explicit country/city mentions
['malaysia', 'kuala lumpur', 'singapore', ...]

# Priority 2: Phone patterns
{
  'malaysia': r'\+60|^60[-\s]|03[-\s]\d{4}',
  'singapore': r'\+65|^65[-\s]',
  'usa': r'\+1[-\s]\d{3}',
}

# Priority 3: Postal patterns (with context)
- Malaysia: 5-digit + city name
- Singapore: S prefix + 6 digits
- US: Only if state names present
```

#### 3. `_clean_address_ocr()`
```python
# Number corrections
r'\$(\d)' → r'5\1'        # $5 → 55
r'(\d)\$' → r'\g<1>5'     # 5$ → 55
r'\$' → '5'               # Standalone $ → 5

# Letter/number in numeric context
r'(?<=\d)[Oo](?=\d)' → '0'  # O between digits
r'(?<=\d)[Oo](?=\s|$)' → '0' # O after digits
```

#### 4. `_extract_phone()`
```python
# OCR corrections
line = re.sub(r'[Oo]', '0', line)  # O → 0
line = re.sub(r'\?', '7', line)    # ? → 7

# Pattern matching
- International: +XX-XXXX-XXXX
- Malaysia: 03-XXXXXXX
- General: (XXX) XXX-XXXX
- Minimum: 7 digits
```

## Test Results

### Before Improvements
```
Store Name:   cp HRYR GROCERS
Address:      $9200 KUALA LUMPUR
Phone:        0322831117
Postal Code:  200686 (invoice number)
Country:      USA
Confidence:   55%
```

### After Improvements
```
Store Name:   JAYA GROCER ✓
Address:      59200 KUALA LUMPUR ✓
Phone:        0322831117 ✓
Postal Code:  59200 ✓
Country:      Malaysia ✓
Confidence:   100% ✓
```

## Multi-Strategy Preprocessing

The system uses 3 preprocessing strategies for best accuracy:

1. **Enhanced**: CLAHE + bilateral filter + adaptive thresholding
   - Best for: Normal receipts with varying lighting
   
2. **Simple**: Grayscale + upscale
   - Best for: Clear, high-quality receipts ✓ (Used in test)
   
3. **High Contrast**: Otsu's thresholding
   - Best for: Faded or low-contrast receipts

System automatically scores all strategies and returns the best result.

## Configuration

### Tesseract Config
- OEM Mode: 3 (LSTM neural net)
- PSM Modes: 6 (uniform block) and 3 (auto) - tries both
- Preprocessing: Top 25% of receipt (where store info is located)
- Upscaling: Minimum 1000-1500px width for better OCR

### Debug Mode
Enable to save preprocessed images and see scoring:
```python
service = TesseractOCRService(debug_mode=True)
```

Debug output:
```
[DEBUG] Saved enhanced image to: debug_ocr/enhanced_123.png
[DEBUG] Strategy 'enhanced' score: 0.75
[DEBUG] Store name: cgaeend 7 UGQ20°
[DEBUG] Saved simple image to: debug_ocr/simple_123.png
[DEBUG] Strategy 'simple' score: 1.20
[DEBUG] Store name: JAYA GROCER ✓
```

## Best Practices

### For Receipt Scanning
1. **Image Quality**: Higher resolution = better OCR
2. **Lighting**: Avoid shadows on top portion of receipt
3. **Orientation**: Ensure receipt is upright
4. **Format**: JPEG or PNG with good compression

### For Store Location Formatting
1. **Store Name**: Should be in first 10 lines
2. **Address**: Include keywords (Floor, Level, Road, Street)
3. **Phone**: Include area code for better country detection
4. **Postal Code**: Near city name for best extraction

## Future Improvements

1. **Language Support**: Add Chinese, Malay, Tamil character recognition
2. **Store Name Database**: Validate against known store chains
3. **Geolocation**: Validate postal codes against maps API
4. **Confidence Thresholds**: Auto-flag low confidence extractions for review
5. **Learning**: Track which preprocessing works best per store/country

## Related Documentation
- [Location Extraction Guide](LOCATION_EXTRACTION.md)
- [Workflow Optimization](WORKFLOW_OPTIMIZATION.md)
- [API Reference](API_REFERENCE.md)

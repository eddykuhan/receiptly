# Python OCR Service - API Reference

## Overview

Stateless OCR service that provides:
1. **Azure Document Intelligence** - Structured receipt data extraction (items, totals, merchant info)
2. **Tesseract OCR** - Store location and address extraction from receipt images

Downloads images from S3, preprocesses them, and returns comprehensive analysis.

## Base URL

- Development: `http://localhost:8000`
- Production: Configure in .NET API `appsettings.json`

## Endpoints

### Analyze Receipt

Analyze a receipt image from a URL with optional location extraction.

**Endpoint:** `POST /api/v1/ocr/analyze`

**Request:**
```json
{
  "image_url": "https://s3.amazonaws.com/presigned-url...",
  "extract_location": true
}
```

**Parameters:**
- `image_url` (required): Presigned S3 URL or any accessible image URL
- `extract_location` (optional, default: true): Enable Tesseract OCR for location extraction

**Response:**
```json
{
  "success": true,
  "data": {
    "doc_type": "receipt.retail",
    "fields": {
      "MerchantName": {
        "value": "Target",
        "value_type": "string",
        "confidence": 0.99
      },
      "MerchantAddress": {
        "value": "123 Main St, City, State 12345",
        "value_type": "string",
        "confidence": 0.95
      },
      "MerchantPhoneNumber": {
        "value": "+1234567890",
        "value_type": "phoneNumber",
        "confidence": 0.92
      },
      "TransactionDate": {
        "value": "2025-11-10",
        "value_type": "date",
        "confidence": 0.98
      },
      "TransactionTime": {
        "value": "14:30:00",
        "value_type": "time",
        "confidence": 0.96
      },
      "Total": {
        "value": 45.67,
        "value_type": "number",
        "confidence": 0.99
      },
      "Subtotal": {
        "value": 42.46,
        "value_type": "number",
        "confidence": 0.98
      },
      "TotalTax": {
        "value": 3.21,
        "value_type": "number",
        "confidence": 0.97
      },
      "Items": {
        "value_type": "array",
        "value_array": [
          {
            "value_type": "object",
            "value_object": {
              "Description": {
                "value": "Product Name",
                "value_type": "string",
                "confidence": 0.95
              },
              "Quantity": {
                "value": 2,
                "value_type": "number",
                "confidence": 0.94
              },
              "Price": {
                "value": 12.99,
                "value_type": "number",
                "confidence": 0.96
              },
              "TotalPrice": {
                "value": 25.98,
                "value_type": "number",
                "confidence": 0.97
              }
            }
          }
        ]
      }
    },
    "confidence": 0.96
  },
  "location": {
    "success": true,
    "location": {
      "store_name": "Target Store #1234",
      "address": "123 Main Street, Building A Level 2",
      "phone": "+12345678901",
      "postal_code": "12345",
      "country": "Usa",
      "confidence": 0.90,
      "full_location_text": "Target Store #1234\n123 Main Street\nBuilding A Level 2\nCity, State 12345\nTel: (123) 456-7890"
    },
    "raw_text": "Target Store #1234...",
    "confidence": 0.90
  },
  "validation": {
    "is_valid_receipt": true,
    "confidence": 0.96,
    "message": "Valid receipt detected with 96.00% confidence",
    "doc_type": "receipt.retail"
  }
}
```

**Response Fields:**

- `success`: Boolean indicating if the analysis was successful
- `data`: Raw Azure Document Intelligence response with structured receipt fields
- `location`: Store location information extracted by Tesseract OCR
  - `success`: Whether location extraction succeeded
  - `location.store_name`: Extracted store/merchant name
  - `location.address`: Full address with street, building, floor info
  - `location.phone`: Phone number in cleaned format
  - `location.postal_code`: Postal/ZIP code
  - `location.country`: Detected country
  - `location.confidence`: Confidence score (0.0-1.0) based on fields found
  - `location.full_location_text`: Complete location text from top of receipt
  - `raw_text`: First 500 characters of OCR text for debugging
- `validation`: Receipt validation results
  - `is_valid_receipt`: Whether document is a valid receipt
  - `confidence`: Azure's confidence in receipt detection
  - `message`: Human-readable validation message
  - `doc_type`: Document type identified by Azure

**Error Response:**
```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (invalid URL, download failed, etc.)
- `500` - Server error

### Health Check

Check service health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy"
}
```

## Image Preprocessing

The service uses an optimized workflow for maximum efficiency:

### Processing Pipeline

1. **Download Once** - Image downloaded from S3/URL only once
2. **Location Extraction** (Tesseract OCR):
   - Focus on top 30% of image (where store info typically appears)
   - Adaptive thresholding for better text recognition
   - Denoising for clarity
   - OCR extraction and parsing
3. **Azure Preprocessing**:
   - RGB Conversion - Ensures consistent color space
   - Resize - Minimum 800px on shortest side
   - Contrast Enhancement - 1.3x increase
   - Sharpening - Enhances text edges
4. **Azure Analysis** - Structured receipt data extraction
5. **Combine Results** - Location + Azure data returned together

**Advantages:**
- Single image download (bandwidth efficient)
- Parallel-ready design (location extraction independent)
- Optimized preprocessing for each use case
- Better performance and error handling
4. **Sharpness Enhancement** - 1.5x increase
5. **Bilateral Denoising** - Reduces noise while preserving edges
6. **Deskew** - Corrects rotation using Hough line detection
7. **Adaptive Binarization** - Optional (disabled by default to preserve address text)

## Azure Document Intelligence Fields

The service returns fields detected by Azure Document Intelligence prebuilt-receipt model:

### Common Fields

- `MerchantName` - Store/business name
- `MerchantAddress` - Full address
- `MerchantPhoneNumber` - Contact number
- `TransactionDate` - Purchase date
- `TransactionTime` - Purchase time
- `Total` - Total amount
- `Subtotal` - Subtotal before tax
- `TotalTax` - Tax amount
- `Tip` - Tip amount (if applicable)

### Item Fields

Each item in the `Items` array contains:
- `Description` - Item name/description
- `Quantity` - Number of items
- `Price` - Unit price
- `TotalPrice` - Line total

### Field Structure

All fields follow this structure:
```json
{
  "value": <actual value>,
  "value_type": "string|number|date|time|phoneNumber|array|object",
  "confidence": 0.0-1.0
}
```

## Configuration

Set these environment variables in `.env`:

```env
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key
API_PREFIX=/api/v1
CORS_ORIGINS=["*"]
```

## Dependencies

- FastAPI - Web framework
- Azure AI Form Recognizer - Document analysis
- Pillow - Image manipulation
- OpenCV - Image preprocessing
- NumPy - Numerical operations
- httpx - HTTP client for image downloads

## Error Handling

The service handles various error scenarios:

- **Image download failure** - Returns 400 with error details
- **Preprocessing failure** - Falls back to original image
- **Azure API failure** - Returns 400 with Azure error message
- **No receipt detected** - Returns success with empty fields

## Performance Considerations

- Image download timeout: 30 seconds
- Preprocessing is synchronous (adds 1-3 seconds)
- Azure analysis time: 2-5 seconds typical
- Total processing time: 3-10 seconds per receipt

## Testing

### Using cURL

```bash
curl -X POST http://localhost:8000/api/v1/ocr/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://your-s3-url..."}'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/ocr/analyze",
    json={"image_url": "https://your-s3-url..."}
)

print(response.json())
```

## Limitations

- Maximum image size: Limited by available memory
- Supported formats: JPEG, PNG, TIFF, PDF
- S3 presigned URL expiry: Ensure URLs are valid for at least 60 seconds
- Azure API rate limits apply
- Preprocessing may not work for all receipt types

## Troubleshooting

### Image download fails
- Check S3 presigned URL is valid
- Verify URL is accessible from service
- Check network connectivity

### Low confidence scores
- Image quality may be poor
- Try higher resolution images
- Ensure receipt is well-lit and flat

### Missing fields
- Some receipts don't have all fields
- Azure confidence thresholds may filter low-confidence data
- Check raw Azure response for additional fields

### Preprocessing errors
- Service falls back to original image
- Check logs for specific error
- Some image formats may not support all preprocessing steps

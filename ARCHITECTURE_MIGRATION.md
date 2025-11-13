# Architecture Migration: S3 Storage & Data Extraction to .NET API

## Overview

The receipt processing architecture has been refactored to move S3 storage and data extraction responsibilities from the Python OCR service to the .NET API Gateway.

## New Architecture Flow

```
[Frontend] 
    ↓ (uploads image)
[.NET API Gateway]
    ↓ 1. Upload image to S3 → Get presigned URL
    ↓ 2. Call Python OCR with URL
[Python OCR Service] 
    ↓ 3. Download image → Preprocess → Azure Document Intelligence → Return raw JSON
[.NET API Gateway]
    ↓ 4. Save raw response to S3
    ↓ 5. Extract structured data
    ↓ 6. Save extracted data to S3
    ↓ 7. Save to SQL database
    ↓ 8. Return receipt to frontend
[Frontend]
```

## Changes Made

### Python OCR Service (Simplified)

**Removed:**
- S3 storage service (`s3_storage.py`)
- AWS dependencies (boto3, AWS credentials)
- User-based file organization
- Multi-user support logic
- Data extraction methods
- `/receipts` list endpoint

**Updated:**
- `DocumentIntelligenceService.analyze_receipt_from_url()` - Now accepts image URL instead of bytes
- Returns raw Azure Document Intelligence response (no extraction)
- `/analyze` endpoint - Accepts `{"image_url": "..."}` instead of file upload

**Dependencies Removed:**
- boto3
- azure-storage-blob
- python-jose

**Dependencies Added:**
- httpx (for downloading images from S3 presigned URLs)

### .NET API Gateway (Enhanced)

**New Services:**

1. **S3StorageService** (`Receiptly.Infrastructure/Services/S3StorageService.cs`)
   - Upload receipt images to S3
   - Generate presigned URLs for Python OCR access
   - Save raw Azure responses to S3
   - Save extracted data to S3
   - Organized folder structure: `users/{userId}/receipts/{YYYY}/{MM}/{DD}/{receiptId}/`

2. **PythonOcrClient** (`Receiptly.Infrastructure/Services/PythonOcrClient.cs`)
   - HTTP client for calling Python OCR service
   - Sends image URL for analysis
   - Receives raw Azure Document Intelligence response

3. **ReceiptProcessingService** (`Receiptly.Infrastructure/Services/ReceiptProcessingService.cs`)
   - Orchestrates complete workflow
   - Extracts structured data from raw Azure response
   - Handles merchant name, address, date, items, totals, tax

**Updated:**
- `ReceiptsController` - New `/upload` endpoint for receipt processing
- `Program.cs` - Dependency injection configuration
- `appsettings.json` - AWS and Python OCR configuration

**Required NuGet Packages:**
```bash
cd dotnet-api/src/Receiptly.Infrastructure
dotnet add package AWSSDK.S3
dotnet add package AWSSDK.Extensions.NETCore.Setup
```

## Configuration

### .NET API (`appsettings.json`)

```json
{
  "AWS": {
    "AccessKeyId": "your-aws-access-key",
    "SecretAccessKey": "your-aws-secret-key",
    "S3BucketName": "receiptly-receipts-prod",
    "Region": "us-east-1"
  },
  "PythonOcr": {
    "ServiceUrl": "http://localhost:8000"
  }
}
```

### Python OCR (`.env`)

```env
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key
```

## API Changes

### .NET API

**New Endpoint:**
```
POST /api/receipts/upload
Content-Type: multipart/form-data

Body: 
- file: receipt image (JPEG, PNG, TIFF, PDF)

Response:
{
  "id": "guid",
  "storeName": "string",
  "storeAddress": "string",
  "purchaseDate": "datetime",
  "totalAmount": decimal,
  "taxAmount": "string",
  "items": [
    {
      "id": "guid",
      "name": "string",
      "price": decimal,
      "quantity": int
    }
  ],
  "createdAt": "datetime"
}
```

### Python OCR Service

**Updated Endpoint:**
```
POST /api/v1/ocr/analyze
Content-Type: application/json

Body:
{
  "image_url": "https://s3-presigned-url..."
}

Response:
{
  "success": true,
  "data": {
    "doc_type": "receipt.retail",
    "fields": {
      "MerchantName": { "value": "...", "confidence": 0.99 },
      "MerchantAddress": { "value": "...", "confidence": 0.95 },
      "TransactionDate": { "value": "2025-11-10", "confidence": 0.98 },
      "Items": { 
        "value_array": [...],
        "confidence": 0.92
      },
      ...
    }
  }
}
```

**Removed Endpoint:**
- `GET /api/v1/ocr/receipts` (user receipts listing)

## S3 Folder Structure

```
s3://receiptly-receipts-prod/
  users/
    {userId}/
      receipts/
        2025/
          11/
            10/
              {receiptId}/
                original_image.jpg
                raw_response.json
                extracted_data.json
```

## Migration Benefits

1. **Single Responsibility**: Python service focuses solely on OCR, .NET handles business logic
2. **Stateless Python Service**: Easier to scale horizontally
3. **Consistent Data Layer**: All S3 and database operations in one place (.NET)
4. **Better Security**: AWS credentials only in .NET API
5. **Easier Testing**: Clear separation of concerns
6. **Multi-user Support**: User context managed by .NET with Azure AD B2C

## Installation & Setup

### Python OCR Service

```bash
cd python-ocr
pip install -r requirements.txt

# Update .env with Azure credentials only
cp .env.example .env

# Run service
uvicorn app.main:app --reload
```

### .NET API

```bash
cd dotnet-api/src/Receiptly.Infrastructure
dotnet add package AWSSDK.S3
dotnet add package AWSSDK.Extensions.NETCore.Setup

cd ../Receiptly.API
# Update appsettings.json with AWS and Python OCR URL
dotnet run
```

## Testing the New Flow

1. Start Python OCR service:
   ```bash
   cd python-ocr
   uvicorn app.main:app --reload
   ```

2. Start .NET API:
   ```bash
   cd dotnet-api/src/Receiptly.API
   dotnet run
   ```

3. Upload receipt via .NET API:
   ```bash
   curl -X POST https://localhost:5001/api/receipts/upload \
     -H "Authorization: Bearer {token}" \
     -F "file=@receipt.jpg"
   ```

## Troubleshooting

### Python OCR Service

- Ensure Azure Document Intelligence credentials are valid
- Check that image preprocessing completes successfully
- Verify httpx can download from S3 presigned URLs

### .NET API

- Verify AWS credentials have S3 PutObject and GetObject permissions
- Ensure S3 bucket exists and is accessible
- Check Python OCR service URL is reachable
- Confirm Azure AD B2C authentication is configured

## Next Steps

1. Add retry logic for Python OCR calls
2. Implement webhook/callback for async processing of large receipts
3. Add receipt validation and duplicate detection
4. Implement batch processing for multiple receipts
5. Add comprehensive logging and monitoring

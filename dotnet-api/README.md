# Receiptly .NET API - Setup Instructions

## Prerequisites

- .NET 8.0 SDK or later
- SQL Server (LocalDB, SQL Server, or Azure SQL)
- AWS Account with S3 access
- Azure AD B2C tenant (for authentication)

## Installation

### 1. Install Required NuGet Packages

```bash
cd dotnet-api/src/Receiptly.Infrastructure
dotnet add package AWSSDK.S3
dotnet add package AWSSDK.Extensions.NETCore.Setup

cd ../Receiptly.Core
# Core layer has no new dependencies

cd ../Receiptly.API
# API layer uses existing Microsoft packages
```

### 2. Configure AWS S3

Update `appsettings.json` or use User Secrets:

```bash
cd src/Receiptly.API
dotnet user-secrets init
dotnet user-secrets set "AWS:AccessKeyId" "your-access-key"
dotnet user-secrets set "AWS:SecretAccessKey" "your-secret-key"
dotnet user-secrets set "AWS:S3BucketName" "receiptly-receipts-prod"
dotnet user-secrets set "AWS:Region" "us-east-1"
```

### 3. Configure Python OCR Service URL

```bash
dotnet user-secrets set "PythonOcr:ServiceUrl" "http://localhost:8000"
```

For production:
```bash
dotnet user-secrets set "PythonOcr:ServiceUrl" "https://your-ocr-service.com"
```

### 4. Configure Azure AD B2C

```bash
dotnet user-secrets set "AzureAd:Instance" "https://login.microsoftonline.com/"
dotnet user-secrets set "AzureAd:Domain" "your-tenant.onmicrosoft.com"
dotnet user-secrets set "AzureAd:TenantId" "your-tenant-id"
dotnet user-secrets set "AzureAd:ClientId" "your-client-id"
```

### 5. Setup Database

```bash
cd src/Receiptly.API
dotnet ef database update
```

## Project Structure

```
dotnet-api/
├── src/
│   ├── Receiptly.API/              # Web API & Controllers
│   │   ├── Controllers/
│   │   │   └── ReceiptsController.cs
│   │   ├── Program.cs
│   │   └── appsettings.json
│   │
│   ├── Receiptly.Core/             # Business Logic
│   │   ├── Interfaces/
│   │   │   └── IReceiptProcessingService.cs
│   │   └── Services/               # (Business logic goes here)
│   │
│   ├── Receiptly.Infrastructure/   # External Services & Data
│   │   ├── Data/
│   │   │   └── ApplicationDbContext.cs
│   │   └── Services/
│   │       ├── S3StorageService.cs
│   │       ├── PythonOcrClient.cs
│   │       └── ReceiptProcessingService.cs
│   │
│   └── Receiptly.Domain/           # Domain Models
│       └── Models/
│           ├── Receipt.cs
│           └── Item.cs
└── Receiptly.sln
```

## Key Services

### S3StorageService

Handles all S3 operations:
- Upload receipt images
- Generate presigned URLs for Python OCR
- Save raw Azure responses
- Save extracted data

**Methods:**
- `UploadReceiptImageAsync()` - Upload image and return presigned URL
- `SaveRawResponseAsync()` - Save OCR raw response
- `SaveExtractedDataAsync()` - Save structured data
- `GetPresignedUrl()` - Generate presigned URLs

### PythonOcrClient

HTTP client for Python OCR service:
- Sends image URL to Python service
- Receives raw Azure Document Intelligence response

**Methods:**
- `AnalyzeReceiptAsync(string imageUrl)` - Analyze receipt via URL

### ReceiptProcessingService

Orchestrates the complete receipt processing workflow:

1. Upload image to S3 → Get presigned URL
2. Call Python OCR with URL
3. Save raw response to S3
4. Extract structured data from raw response
5. Save extracted data to S3
6. Return `Receipt` entity for database storage

**Methods:**
- `ProcessReceiptAsync()` - Main orchestration method
- `ExtractReceiptData()` - Parse Azure response
- `ExtractItems()` - Parse receipt line items

## API Endpoints

### Upload Receipt

```http
POST /api/receipts/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

Body:
- file: receipt image (JPEG, PNG, TIFF, PDF)
```

**Response:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "storeName": "Target",
  "storeAddress": "123 Main St, City, State",
  "purchaseDate": "2025-11-10T14:30:00Z",
  "totalAmount": 45.67,
  "taxAmount": "3.21",
  "items": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "name": "Product Name",
      "price": 12.99,
      "quantity": 2
    }
  ],
  "imageUrl": null,
  "createdAt": "2025-11-10T15:00:00Z"
}
```

### List Receipts

```http
GET /api/receipts
Authorization: Bearer {token}
```

### Get Receipt by ID

```http
GET /api/receipts/{id}
Authorization: Bearer {token}
```

## AWS IAM Permissions

Your AWS credentials need the following S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::receiptly-receipts-prod",
        "arn:aws:s3:::receiptly-receipts-prod/*"
      ]
    }
  ]
}
```

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

## Running the Application

### Development

```bash
cd dotnet-api/src/Receiptly.API
dotnet run
```

API available at: `https://localhost:5001`

### Production

```bash
dotnet publish -c Release -o ./publish
cd publish
dotnet Receiptly.API.dll
```

## Testing

### Test Receipt Upload

```bash
# Get authentication token first (Azure AD B2C)
TOKEN="your-bearer-token"

# Upload receipt
curl -X POST https://localhost:5001/api/receipts/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/receipt.jpg"
```

## Troubleshooting

### AWS S3 Connection Issues

- Verify AWS credentials are correct
- Check S3 bucket exists and region is correct
- Ensure IAM permissions are properly configured
- Test with AWS CLI: `aws s3 ls s3://receiptly-receipts-prod/`

### Python OCR Service Connection

- Verify Python service is running: `curl http://localhost:8000/health`
- Check `PythonOcr:ServiceUrl` configuration
- Review logs for HTTP client errors

### Database Issues

- Run migrations: `dotnet ef database update`
- Check connection string in `appsettings.json`
- Verify SQL Server is running

### Authentication Issues

- Verify Azure AD B2C configuration
- Check token claims contain user ID (`sub` or `nameidentifier`)
- Review Azure AD B2C app registration settings

## Environment Variables

For production deployment, set these environment variables:

```bash
AWS__AccessKeyId=your-access-key
AWS__SecretAccessKey=your-secret-key
AWS__S3BucketName=receiptly-receipts-prod
AWS__Region=us-east-1
PythonOcr__ServiceUrl=https://your-ocr-service.com
AzureAd__TenantId=your-tenant-id
AzureAd__ClientId=your-client-id
ConnectionStrings__DefaultConnection=your-sql-connection-string
```

## Next Steps

1. Implement error handling and retry logic
2. Add request/response logging
3. Implement caching for frequently accessed receipts
4. Add background job processing for large batches
5. Setup Application Insights for monitoring
6. Configure auto-scaling based on load

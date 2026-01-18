# Receiptly AI Agent Instructions

## Project Overview

Receiptly is a receipt scanning and price comparison application using a microservices architecture. The system extracts data from receipts using OCR and provides price comparisons across locations.

## Key Components

```
[Frontend (TBD)] → [.NET API Gateway] → [Python OCR Service]
```

### Core Services

1. **.NET API Gateway** (`/dotnet-api/`)
   - Clean Architecture with 4 layers:
     - `Receiptly.API`: Controllers, DTOs, and endpoints
     - `Receiptly.Core`: Business logic, interfaces
     - `Receiptly.Infrastructure`: Data access, external services, repositories
     - `Receiptly.Domain`: Domain models, enums
   - Uses Entity Framework Core with PostgreSQL
   - AutoMapper for DTO mapping
   - Repository pattern for data access
   - CancellationToken support for async operations

2. **Python OCR Service** (`/python-ocr/`)
   - FastAPI-based microservice
   - Azure Computer Vision integration
   - Stateless receipt processing
   - Multi-source location extraction with LLM enhancement
   - See [OCR Processing Pipeline](#ocr-processing-pipeline) for detailed flow

## Key Patterns and Conventions

### .NET Patterns

#### Domain Models
```csharp
// Domain models use nullable reference types
public class Receipt
{
    public Guid Id { get; set; }
    public string StoreName { get; set; } = string.Empty;  // Note default initialization
    public List<Item> Items { get; set; } = new();
    public DateTime? UpdatedAt { get; set; }  // Optional fields are nullable
}
```

#### DTOs (Data Transfer Objects)
```csharp
// DTOs exclude internal fields and prevent circular references
public class ReceiptDto
{
    public Guid Id { get; set; }
    public string StoreName { get; set; } = string.Empty;
    public List<ItemDto> Items { get; set; } = new();  // ItemDto excludes Receipt reference
    // Excludes: S3Key, internal database fields
}
```

#### Repository Pattern
```csharp
// All repository methods accept CancellationToken
public interface IReceiptRepository
{
    Task<Receipt> CreateAsync(Receipt receipt, CancellationToken cancellationToken = default);
    Task<Receipt?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<List<Receipt>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default);
}
```

#### AutoMapper Usage
```csharp
// Controllers use AutoMapper to convert domain models to DTOs
public class ReceiptsController : ControllerBase
{
    private readonly IMapper _mapper;
    
    public async Task<ActionResult<ReceiptDto>> GetReceipt(Guid id, CancellationToken cancellationToken)
    {
        var receipt = await _receiptRepository.GetByIdAsync(id, cancellationToken);
        var receiptDto = _mapper.Map<ReceiptDto>(receipt);
        return Ok(receiptDto);
    }
}
```

#### CancellationToken Pattern
```csharp
// Always accept CancellationToken in async methods
// Check cancellation at strategic points in long-running operations
public async Task<Receipt> ProcessReceiptAsync(
    string userId, 
    Stream imageStream, 
    CancellationToken cancellationToken = default)
{
    await UploadToS3Async(...);
    cancellationToken.ThrowIfCancellationRequested();
    
    var ocrResult = await CallOcrAsync(...);
    cancellationToken.ThrowIfCancellationRequested();
    
    await SaveToDbAsync(..., cancellationToken);
    return receipt;
}

// Handle OperationCanceledException in controllers
catch (OperationCanceledException)
{
    _logger.LogWarning("Request cancelled");
    return StatusCode(499, new { error = "Request cancelled" });
}
```

### Python Patterns
```python
# FastAPI services use dependency injection
@router.post("/analyze")
async def analyze_receipt(
    file: UploadFile = File(...),
    vision_service: AzureVisionService = Depends(AzureVisionService)
)
```

## OCR Processing Pipeline

The `/python-ocr/app/routers/ocr.py` endpoint implements a **9-step receipt analysis pipeline** that combines Azure Document Intelligence, LLM Vision (GPT-4), and Google Places verification.

### Pipeline Steps

**Step 1: Request Validation & Setup**
- Parse `AnalyzeRequest` parameters (image_url, extract_location, auto_crop, enable_llm_enhancement)
- Initialize `ImageDebugger` if debug mode enabled
- Record start_time for performance metrics

**Step 2: Image Download**
- Download image from provided URL
- Store original uncropped bytes (preserves transaction dates at image edges)
- Debug: Save as "01_original"

**Step 3: Receipt Boundary Detection (Optional)**
- If `auto_crop=true`:
  - Primary: Try Azure Document Intelligence Layout model for boundary detection
  - Fallback: OpenCV-based detection if Azure fails
- Result: Cropped image focused on receipt content
- Debug: Save as "02_cropped_*"

**Step 4: [Skipped] Image Preprocessing**
- Currently commented out in production
- Would normalize image for Azure processing (brightness, contrast, rotation)

**Step 5: Azure Document Intelligence Analysis**
- Send cropped image to Azure Document Intelligence service
- Extract structured receipt data:
  - MerchantName, MerchantAddress, MerchantPhoneNumber
  - Items (Description, Quantity, TotalPrice per item)
  - TransactionDate
  - Total Amount
  - Document confidence score
- Debug: Save as "05_azure_result"

**Step 6: [Commented Out] Merchant Data Override**

**Previously:** This step called LLM Vision separately to extract merchant data.  
**Now:** Moved into Step 7 to consolidate LLM calls and reduce costs.  
**Reason:** Calling LLM twice (once for location, once for items) was redundant and expensive.

- Debug: Step skipped

**Step 7: LLM Enhancement (Optional - Fully Consolidated)**

Controlled by `enable_llm_enhancement` flag. When enabled, performs **location extraction, transaction date extraction, AND item enhancement in a SINGLE LLM call** for maximum efficiency.

**Single LLM Request extracts:**
1. **Merchant Location:**
   - Store name (prioritized over Azure)
   - Full address
   - Phone number
   
2. **Transaction Date:**
   - More reliable than Azure (uses full uncropped image context)
   
3. **Item Enhancement:**
   - Expand abbreviated item names
   - Add missing items detected in image
   - Remove non-product entries (subtotals, taxes, discounts)
   - Fix quantities and validate prices
   - Validate total against item sum

**Post-LLM Processing:**
- Apply extracted location/date to result fields
- Run Google Places verification on LLM-extracted store name
- If Google match confidence ≥ 80%, replace with verified address + coordinates
- Merge enhanced items back into Azure structure

**Cost Optimization Evolution:**
- **Original:** 2 separate LLM calls (location + items) = ~$0.05/receipt
- **Previous:** Consolidated into 1 call = ~$0.03/receipt  
- **Current:** Single unified LLM request = ~$0.025/receipt
- **Total Savings:** 50% reduction from original implementation

- Debug: Save as "06_location_from_llm" and "06b_llm_enhancement"

**Step 8: Enhanced Validation**

Run `EnhancedValidationService`:
- Validate receipt structure completeness
- Calculate overall confidence score
- Track which sources were used (azure, llm_vision, google_places, llm_enhancement)
- Detect and flag issues/warnings
- Measure total processing duration

- Debug: Save as "07_validation_result"

**Step 9: Return Response**

Build `ProcessedReceipt` object containing:
- `success`: bool (success/failure status)
- `data`: Azure result with all overrides applied
- `validation`: Confidence scores, issue flags, processing duration
- `location`: Store location data with verification status
- `debug_session_id`: Debug directory reference (if debug enabled)

### Data Source Priority Hierarchy

| Field | Source Priority | Fallback Strategy | Condition |
|-------|-----------------|-------------------|-----------|
| **Store Name** | LLM Vision > Azure | Google Places verification applied | Only if `enable_llm_enhancement=true` |
| **Address** | Google Places verified > LLM Vision > Azure | Merged from best available source | Only if `enable_llm_enhancement=true` |
| **Phone** | Google Places > LLM Vision > Azure | Skip if all unavailable | Only if `enable_llm_enhancement=true` |
| **Transaction Date** | LLM Vision > Azure | Flag for manual review if missing | Only if `enable_llm_enhancement=true` |
| **Items** | LLM Enhanced > Azure | Use Azure if enhancement disabled/fails | Only if `enable_llm_enhancement=true` |

**Note:** When `enable_llm_enhancement=false`, the system uses **Azure-only** results for all fields.

### Request Configuration Flags

```python
class AnalyzeRequest(BaseModel):
    image_url: HttpUrl                          # Receipt image URL
    extract_location: bool = True               # Enable store location extraction
    auto_crop: bool = True                      # Enable receipt boundary detection
    crop_method: Literal["opencv", "azure_layout"] = "azure_layout"  # Cropping method
    enable_llm_enhancement: bool = False        # Enable LLM post-processing
```

### Error Handling & Fallback Strategy

- **Azure Layout detection fails**: Fall back to OpenCV boundary detection
- **LLM Vision extraction unavailable**: Continue with Azure-only data
- **Google Places match fails**: Continue with OCR-extracted address
- **LLM enhancement fails**: Keep Azure results unchanged
- **Any step exception**: Capture in debug session, return HTTPException 400

### Key Implementation Details

1. **Original Image Preservation**: Always keeps uncropped image bytes for LLM Vision processing to preserve transaction dates printed at image edges
2. **Confidence-Based Selection**: Candidates sorted by confidence; LLM Vision prioritized due to better full-image context
3. **Google Places Integration**: Verifies merchant location against trusted database, replacing OCR data only when confidence ≥80%
4. **Metadata Tracking**: Annotates each field with source origin (azure, llm_vision, google_places) for traceability
5. **Debug Session Management**: Optional detailed image processing logs saved per request for troubleshooting

### File Location

Main implementation: `python-ocr/app/routers/ocr.py`
- Key pipeline step classes: `python-ocr/app/services/pipeline_steps.py`
- Pipeline steps:
  - `ImageDownloadStep`: Step 1
  - `ReceiptCropStep`: Step 2-3
  - `AzureAnalysisStep`: Step 5
  - `LocationCandidatesStep`: Step 6 (Commented out - kept for reference)
  - `LLMEnhancementStep`: Step 7 (consolidated location, date, items)

## Development Workflows

### Setup
1. .NET API:
   ```bash
   cd dotnet-api
   dotnet restore
   dotnet build
   dotnet run --project src/Receiptly.API
   ```

2. Python OCR:
   ```bash
   cd python-ocr
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

### Configuration
- .NET: Uses `appsettings.json` and user secrets for local development
- Python: Uses `.env` file (copy from `.env.example`)

## Integration Points

1. **AWS Services**
   - **RDS PostgreSQL**: Main database (free tier: db.t3.micro, 20GB storage)
     - Database name: `receiptly`
     - Credentials stored in AWS Secrets Manager: `receiptly/database/credentials`
     - Contains: username, password, host, port, database, engine
   - **S3**: Receipt image storage
     - Bucket: `receiptly-{environment}-receipts`
     - Credentials stored in AWS Secrets Manager: `receiptly/s3/credentials`
     - Contains: aws_access_key_id, aws_secret_access_key, bucket_name, region
   - **Secrets Manager**: Centralized credential storage
     - .NET API retrieves credentials on startup
     - Uses AWS credential chain (environment vars → ~/.aws/credentials → IAM role)

2. **Azure Services**
   - Azure Computer Vision: OCR processing (configured in `.env`)

3. **Service Communication**
   - REST APIs with JSON payloads
   - Standard receipt format:
   ```json
   {
     "id": "uuid",
     "storeName": "string",
     "items": [{
       "name": "string",
       "price": "decimal",
       "quantity": "integer"
     }]
   }
   ```

## AWS Secrets Manager Integration

### Secret Retrieval Pattern
```csharp
// Retrieve credentials on application startup
using var secretsClient = new AmazonSecretsManagerClient(
    Amazon.RegionEndpoint.GetBySystemName(region)
);

var response = await secretsClient.GetSecretValueAsync(
    new GetSecretValueRequest { SecretId = "receiptly/database/credentials" }
);

var config = JsonSerializer.Deserialize<DatabaseSecretsConfig>(response.SecretString);
```

### Configuration Classes
- `DatabaseSecretsConfig`: Maps receiptly/database/credentials JSON
- `S3SecretsConfig`: Maps receiptly/s3/credentials JSON

### Fallback Strategy
- Production: Uses Secrets Manager with IAM role authentication
- Local Development: Falls back to appsettings.json/user secrets if Secrets Manager unavailable

## Infrastructure (Terraform)

### Staging Environment Resources
- **VPC**: 10.0.0.0/16 with public/private subnets in 2 AZs
- **RDS PostgreSQL**: Free tier (db.t3.micro, 20GB, publicly accessible for GitHub Actions)
- **S3 Bucket**: Receipt storage with versioning, encryption, lifecycle rules
- **Secrets Manager**: Database and S3 credentials
- **IAM**: Dedicated S3 user with scoped permissions

### Terraform Modules
- `modules/vpc`: VPC, subnets, route tables
- `modules/rds`: PostgreSQL RDS instance with security groups
- `modules/s3`: S3 bucket with versioning and lifecycle
- `modules/secrets`: Secrets Manager secrets

## Common Tasks

### Adding New API Endpoints
1. Create controller in `dotnet-api/src/Receiptly.API/Controllers/`
2. Define models in `Receiptly.Domain/Models/`
3. Implement business logic in `Receiptly.Core/Services/`

### Adding OCR Features
1. Extend `AzureVisionService` in `python-ocr/app/services/`
2. Add new endpoints in `python-ocr/app/routers/`

## Testing Approach

- .NET: xUnit tests per project layer
- Python: pytest with async support
- Integration tests use real Azure services in staging environment

## Error Handling

- REST APIs return standard error format:
```json
{
  "type": "string",
  "title": "string",
  "status": integer,
  "detail": "string"
}
```

## Documentation Links
- API Gateway Swagger: `http://localhost:5000/swagger`
- OCR Service Swagger: `http://localhost:8000/docs`

## Areas Requiring Caution

1. Authentication flow between services
2. Receipt data privacy handling
3. OCR service error handling and retries
4. Database migrations during deployments
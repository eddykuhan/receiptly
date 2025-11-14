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

1. **Azure Services**
   - Azure Computer Vision: OCR processing (configured in `.env`)
   - AWS S3: Receipt image storage
   - PostgreSQL: Main database (AWS RDS in production)

2. **Service Communication**
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
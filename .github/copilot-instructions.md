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
     - `Receiptly.API`: Controllers and endpoints
     - `Receiptly.Core`: Business logic
     - `Receiptly.Infrastructure`: Data access, external services
     - `Receiptly.Domain`: Domain models
   - Uses Entity Framework Core with SQL Server
   - Azure AD B2C authentication

2. **Python OCR Service** (`/python-ocr/`)
   - FastAPI-based microservice
   - Azure Computer Vision integration
   - Stateless receipt processing

## Key Patterns and Conventions

### .NET Patterns
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
   - Azure AD B2C: Authentication (configured in `appsettings.json`)
   - Azure Computer Vision: OCR processing (configured in `.env`)
   - Azure SQL: Main database

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
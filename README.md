# Receiptly

A smart receipt scanning and price comparison application that helps users find the best deals.

## Architecture Overview

```ascii
[ Mobile / Web App (Angular, iOS, etc.) ]
             │
             ▼
     [ .NET 8 API Gateway ]
             │
     ├── Handles Auth (Azure AD, JWT)
     ├── Routes requests
     ├── Stores metadata (SQL)
     └── Calls OCR/AI Service via REST
             │
             ▼
     [ Python Microservice (FastAPI) ]
             ├── Performs OCR (Azure Vision / Tesseract)
             ├── Cleans and parses data
             ├── Runs AI logic (LLM, embeddings, etc.)
             └── Returns structured JSON to .NET
```

## Repository Structure

- `/dotnet-api` - .NET 8 API Gateway
  - Core API functionality
  - Authentication & Authorization
  - SQL database integration
  - Request routing and middleware
  
- `/python-ocr` - Python FastAPI Microservice
  - OCR processing with Azure Computer Vision
  - Receipt data parsing and structuring
  - AI/ML processing pipeline
  
- `/shared` - Shared Resources
  - API contracts
  - Common DTOs
  - Shared utilities
  - Documentation

- `/front-end` - Frontend Applications
  - Web application
  - Mobile app resources

## Tech Stack

### API Gateway (.NET 8)
- .NET 8 Web API
- Entity Framework Core
- Azure AD B2C
- SQL Server/Azure SQL
- Azure Service Bus (for async processing)

### OCR/AI Service (Python)
- FastAPI
- Azure Computer Vision
- Azure OpenAI/LLM integration
- PostgreSQL (for OCR results caching)
- Redis (for rate limiting/caching)

### Frontend (TBD)
- Options under consideration:
  - Angular/React for web
  - iOS/Android native apps

## Getting Started

### Prerequisites

- .NET 8 SDK
- Python 3.11+
- Visual Studio Code (recommended) or Visual Studio
- Azure subscription (for Computer Vision API)

### Setting Up the Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/eddykuhan/receiptly.git
   cd receiptly
   ```

2. Set up .NET API Gateway:
   ```bash
   cd dotnet-api
   dotnet restore
   dotnet build
   ```

3. Set up Python OCR Service:
   ```bash
   cd python-ocr
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env` in the python-ocr directory
   - Update Azure Vision API credentials in `.env`
   - Configure any necessary API Gateway settings in `appsettings.Development.json`

### Starting the Services

1. Start the .NET API Gateway:
   ```bash
   cd dotnet-api
   dotnet run --project src/Receiptly.API
   ```
   The API will be available at: http://localhost:5188
   Swagger UI: http://localhost:5188/swagger

2. Start the Python OCR Service:
   ```bash
   cd python-ocr
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   uvicorn app.main:app --reload
   ```
   The OCR service will be available at: http://localhost:8000
   API Documentation: http://localhost:8000/docs

### Development Tools

- VS Code Extensions:
  - C# Dev Kit
  - Python
  - REST Client
  - Thunder Client (or Postman) for API testing

### Debugging

- .NET API: Use VS Code's built-in debugger (F5)
- Python OCR: Use VS Code's Python debugger with the provided launch configurations

## Contributing

[Contribution guidelines will be added]

## License

[License information will be added]

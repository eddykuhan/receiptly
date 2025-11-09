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

[Development setup instructions will be added]

## Contributing

[Contribution guidelines will be added]

## License

[License information will be added]

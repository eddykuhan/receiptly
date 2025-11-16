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
  
- `/angular-app` - Angular PWA Frontend
  - Progressive Web App
  - Receipt scanning UI
  - Dashboard and analytics
  
- `/scripts` - Automation Scripts
  - Service management (start/stop/check)
  - Deployment scripts
  - Log viewing utilities
  
- `/docs` - Documentation
  - Setup guides
  - Architecture documentation
  - Deployment guides
  
- `/shared` - Shared Resources
  - API contracts
  - Common DTOs
  - Shared utilities

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

## Monitoring & Logging

### CloudWatch Logs (Production)

View logs from AWS CloudWatch without SSM access:

```bash
# Interactive log viewer
./scripts/view-cloudwatch-logs.sh staging

# Real-time log streaming
./scripts/tail-cloudwatch-logs.sh staging ocr

# Search logs
./scripts/search-cloudwatch-logs.sh staging ocr "error" 6
```

Log groups:
- `/receiptly/{env}/ocr` - Python OCR service
- `/receiptly/{env}/api` - .NET API service
- `/receiptly/{env}/system` - System logs

See [docs/CLOUDWATCH_LOGS.md](docs/CLOUDWATCH_LOGS.md) for detailed setup and usage.

### EC2 Logs (via SSM)

Alternative log access using AWS Systems Manager:

```bash
# Check service status and logs
./scripts/check-ec2-logs.sh staging all

# View logs interactively
./scripts/view-ec2-logs.sh staging
```

See [docs/SSM_ACCESS_FIX.md](docs/SSM_ACCESS_FIX.md) for SSM setup.

### Service Management Scripts

```bash
# Local development
./scripts/start-services.sh   # Start all services
./scripts/check-services.sh   # Check service status
./scripts/stop-services.sh    # Stop all services
```

See [docs/SCRIPTS.md](docs/SCRIPTS.md) for all available scripts.

## Documentation

- [docs/CLOUDWATCH_LOGS.md](docs/CLOUDWATCH_LOGS.md) - CloudWatch Logs setup and usage
- [docs/CLOUDWATCH_QUICK_REFERENCE.md](docs/CLOUDWATCH_QUICK_REFERENCE.md) - Quick command reference
- [docs/SCRIPTS.md](docs/SCRIPTS.md) - Service management scripts
- [docs/SSM_ACCESS_FIX.md](docs/SSM_ACCESS_FIX.md) - SSM access troubleshooting
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - AWS deployment guide
- [docs/DOCKER.md](docs/DOCKER.md) - Docker setup and usage
- [docs/CLOUDWATCH_IMPLEMENTATION.md](docs/CLOUDWATCH_IMPLEMENTATION.md) - CloudWatch implementation details
- [docs/AWS_SECRETS_INTEGRATION.md](docs/AWS_SECRETS_INTEGRATION.md) - AWS Secrets Manager integration
- [docs/ARCHITECTURE_MIGRATION.md](docs/ARCHITECTURE_MIGRATION.md) - Architecture evolution
- [docs/PWA_TESTING_GUIDE.md](docs/PWA_TESTING_GUIDE.md) - PWA testing guide

## Contributing

[Contribution guidelines will be added]

## License

[License information will be added]

# Receiptly

A smart receipt scanning and price comparison application that helps users find the best deals by extracting data from receipts using OCR technology.

## Architecture Overview

Receiptly uses a microservices architecture with clear separation of concerns:

```ascii
[Frontend (TBD)]
       │
       ▼
[ .NET 8 API Gateway ]
       │
       ├─► 1. Upload image to AWS S3 → Get presigned URL
       ├─► 2. Call Python OCR with URL
       │
       ▼
[ Python OCR Service (FastAPI) ]
       │
       └─► 3. Download from S3 → Azure Document Intelligence → Return raw JSON
       │
       ▼
[ .NET 8 API Gateway ]
       │
       ├─► 4. Save raw response to S3
       ├─► 5. Extract structured data
       ├─► 6. Save extracted data to S3
       ├─► 7. Save to SQL database
       └─► 8. Return receipt to frontend
```

### Key Design Principles

- **Stateless Python Service**: Focuses solely on OCR processing, making it easy to scale horizontally
- **Centralized Storage**: All S3 and database operations managed by .NET API for consistency
- **Clear Separation**: Python handles OCR, .NET handles business logic and data management
- **Secure**: AWS credentials only in .NET API, Azure credentials only in Python service

## Repository Structure

```
receiptly/
├── dotnet-api/              # .NET 8 API Gateway
│   ├── src/
│   │   ├── Receiptly.API/          # Controllers and endpoints
│   │   ├── Receiptly.Core/         # Business logic
│   │   ├── Receiptly.Infrastructure/  # External services (S3, OCR client)
│   │   └── Receiptly.Domain/       # Domain models
│   └── README.md
│
├── python-ocr/              # Python FastAPI OCR Service
│   ├── app/                 # Application code
│   ├── Dockerfile
│   └── requirements.txt
│
├── terraform/               # Infrastructure as Code
│   ├── modules/             # Reusable Terraform modules
│   └── environments/        # Environment-specific configs
│
├── .github/workflows/       # CI/CD pipelines
├── docker-compose.yml       # Local development with Docker
├── start-services.sh        # Start services locally
├── stop-services.sh         # Stop services
└── check-services.sh        # Check service status
```

## Tech Stack

### .NET API Gateway
- **.NET 8** Web API with Clean Architecture
- **Entity Framework Core** for database access
- **AWS S3** for receipt image and data storage
- **Azure AD B2C** (planned for authentication)
- **SQL Server/Azure SQL** for structured data

### Python OCR Service
- **FastAPI** for high-performance API endpoints
- **Azure Document Intelligence** for OCR processing
- **httpx** for downloading images from S3 presigned URLs
- **Pillow** for image preprocessing

### Infrastructure
- **AWS S3** for object storage
- **AWS ECS Fargate** for production deployment (optional)
- **Terraform** for infrastructure as code
- **Docker** and **Docker Compose** for containerization

### Frontend (Planned)
- Web and mobile applications (to be implemented)


## Deployment Options

Receiptly supports multiple deployment approaches depending on your needs:

### 1. Local Development (Quickest Start)

Use the provided shell scripts for easy local development:

```bash
# One-time setup
./start-services.sh

# Check service status
./check-services.sh

# Stop services
./stop-services.sh
```

See [SCRIPTS.md](SCRIPTS.md) for detailed information about service management scripts.

### 2. Docker Compose (Recommended for Development)

Run both services in containers with a single command:

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Azure and AWS credentials

# Start all services
docker-compose up --build

# Access the services:
# - .NET API: http://localhost:5188
# - Python OCR: http://localhost:8000
```

See [DOCKER.md](DOCKER.md) for complete Docker setup and usage instructions.

### 3. AWS Production Deployment

Deploy to AWS ECS Fargate using Terraform:

```bash
cd terraform/environments/staging
terraform init
terraform apply
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive AWS deployment guide, including:
- Infrastructure as Code with Terraform
- CI/CD with GitHub Actions
- Multi-environment setup (staging/production)
- Cost optimization strategies

## Getting Started

### Prerequisites

- **.NET 8 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/8.0)
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Docker Desktop** (optional, for Docker deployment) - [Download](https://www.docker.com/products/docker-desktop)
- **Azure subscription** - For Document Intelligence API
- **AWS account** - For S3 storage (optional for local testing)

### Quick Start (Local Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/eddykuhan/receiptly.git
   cd receiptly
   ```

2. **Set up Python OCR Service:**
   ```bash
   cd python-ocr
   python3 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   # Edit .env with your Azure Document Intelligence credentials
   cd ..
   ```

3. **Set up .NET API Gateway:**
   ```bash
   cd dotnet-api
   dotnet restore
   dotnet build
   
   # Configure user secrets (AWS credentials)
   cd src/Receiptly.API
   dotnet user-secrets set "AWS:AccessKeyId" "your-access-key"
   dotnet user-secrets set "AWS:SecretAccessKey" "your-secret-key"
   dotnet user-secrets set "AWS:S3BucketName" "your-bucket-name"
   dotnet user-secrets set "AWS:Region" "ap-southeast-1"
   dotnet user-secrets set "PythonOcr:ServiceUrl" "http://localhost:8000"
   cd ../../..
   ```

4. **Start the services:**
   ```bash
   # Option A: Use convenience scripts
   ./start-services.sh
   
   # Option B: Manual start
   # Terminal 1 - Python OCR
   cd python-ocr
   source venv/bin/activate
   uvicorn app.main:app --reload
   
   # Terminal 2 - .NET API
   cd dotnet-api/src/Receiptly.API
   dotnet run
   ```

5. **Access the services:**
   - **.NET API**: http://localhost:5188
   - **API Documentation**: http://localhost:5188/swagger
   - **Python OCR**: http://localhost:8000  
   - **OCR Documentation**: http://localhost:8000/docs

### Development Tools

**Recommended IDE:**
- Visual Studio Code with extensions:
  - C# Dev Kit
  - Python
  - REST Client
  - Docker (if using containers)

**API Testing:**
- Swagger UI (built-in at `/swagger` and `/docs`)
- Thunder Client (VS Code extension)
- Postman
- curl

### Project Configuration

#### Azure Document Intelligence Setup

1. Create an Azure Document Intelligence resource in the [Azure Portal](https://portal.azure.com)
2. Copy the endpoint and key to `python-ocr/.env`:
   ```env
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key-here
   ```

#### AWS S3 Setup (Optional for local testing)

1. Create an S3 bucket in your AWS account
2. Create an IAM user with S3 permissions
3. Configure using .NET user secrets (see Quick Start step 3)

For detailed setup instructions, see:
- [dotnet-api/README.md](dotnet-api/README.md) - .NET API configuration
- [ARCHITECTURE_MIGRATION.md](ARCHITECTURE_MIGRATION.md) - Architecture details and migration guide

## Documentation

- **[ARCHITECTURE_MIGRATION.md](ARCHITECTURE_MIGRATION.md)** - Detailed architecture overview and S3 migration details
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - AWS deployment with Terraform and CI/CD
- **[DOCKER.md](DOCKER.md)** - Docker and Docker Compose usage guide  
- **[SCRIPTS.md](SCRIPTS.md)** - Service management scripts documentation
- **[dotnet-api/README.md](dotnet-api/README.md)** - .NET API setup and configuration
- **[python-ocr/API_REFERENCE.md](python-ocr/API_REFERENCE.md)** - Python OCR API reference

## How It Works

1. **Upload**: Client uploads receipt image to .NET API
2. **Store**: API uploads image to S3 and generates presigned URL
3. **Analyze**: API calls Python OCR service with the presigned URL
4. **Process**: Python service downloads image, preprocesses it, and sends to Azure Document Intelligence
5. **Extract**: .NET API receives raw OCR results and extracts structured data (merchant, items, totals, etc.)
6. **Save**: API stores raw response and extracted data to S3, then saves to SQL database
7. **Return**: Structured receipt data returned to client

For detailed workflow, see [ARCHITECTURE_MIGRATION.md](ARCHITECTURE_MIGRATION.md).

## API Examples

### Upload a Receipt

```bash
curl -X POST http://localhost:5188/api/receipts/upload \
  -F "file=@receipt.jpg"
```

### Response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "storeName": "Target",
  "storeAddress": "123 Main St",
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
  "createdAt": "2025-11-10T15:00:00Z"
}
```

See [Swagger UI](http://localhost:5188/swagger) for complete API documentation.

## Debugging

**VS Code Launch Configurations:**

Both services include `.vscode/launch.json` configurations:

- **.NET API**: Press F5 in VS Code (select ".NET Core Launch (web)")
- **Python OCR**: Use the Python debugger with FastAPI configuration

**Logs:**

When using the start scripts, logs are available at:
- `logs/python-ocr.log`
- `logs/dotnet-api.log`

**Health Checks:**
```bash
# Check Python OCR
curl http://localhost:8000/health

# Check .NET API  
curl http://localhost:5188/health
```

## Contributing

We welcome contributions to Receiptly! Here's how you can help:

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

**Code Style:**
- **.NET**: Follow [C# Coding Conventions](https://docs.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions)
- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and single-purpose

**Testing:**
- Write unit tests for new features
- Ensure existing tests pass
- Add integration tests for API endpoints

**Commits:**
- Write clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits focused on a single change

**Pull Requests:**
- Provide a clear description of changes
- Link to related issues
- Update documentation as needed
- Ensure CI/CD checks pass

### Areas for Contribution

We're particularly interested in contributions for:

- Frontend development (web/mobile applications)
- Additional OCR providers or fallback options
- Price comparison features
- Enhanced data extraction algorithms
- Performance optimizations
- Additional deployment options (Azure, GCP)
- Improved error handling and logging
- Documentation improvements
- Test coverage expansion

### Reporting Issues

Found a bug or have a feature request?

1. Check if the issue already exists in [GitHub Issues](https://github.com/eddykuhan/receiptly/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Detailed description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (OS, .NET version, Python version)

## License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2024 Receiptly Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Acknowledgments

- **Azure Document Intelligence** for OCR capabilities
- **FastAPI** for the high-performance Python framework
- **.NET Team** for the excellent web framework and tooling
- All contributors who help improve this project

## Support

- **Documentation**: Check the docs listed in the [Documentation](#documentation) section
- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/eddykuhan/receiptly/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/eddykuhan/receiptly/discussions)

---

**Built with ❤️ by the Receiptly Team**

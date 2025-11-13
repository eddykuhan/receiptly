# Receiptly Docker Setup

This guide will help you run the entire Receiptly application using Docker Compose.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Azure Document Intelligence credentials
- AWS S3 credentials

## Quick Start

### 1. Create Environment File

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your actual credentials:

```env
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-azure-key-here

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_BUCKET_NAME=your-s3-bucket-name
AWS_REGION=ap-southeast-1
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up -d --build
```

### 3. Access the Services

- **API Gateway**: http://localhost:5188
- **API Swagger UI**: http://localhost:5188/swagger
- **Python OCR Service**: http://localhost:8000
- **OCR Swagger UI**: http://localhost:8000/docs

### 4. Test the Application

Upload a receipt:

```bash
curl -X POST http://localhost:5188/api/Receipts/upload \
  -F "file=@/path/to/receipt.jpg"
```

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dotnet-api
docker-compose logs -f python-ocr
```

### Stop Services

```bash
docker-compose down
```

### Rebuild After Code Changes

```bash
docker-compose up --build
```

### Clean Up Everything

```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  .NET API    │─────▶│ Python OCR  │
│             │      │  (Gateway)   │      │  (FastAPI)  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                      │
                            ▼                      │
                     ┌─────────────┐              │
                     │   AWS S3    │◀─────────────┘
                     │  (Storage)  │
                     └─────────────┘
```

## Services

### dotnet-api
- **Port**: 5188 → 8080 (container)
- **Purpose**: API Gateway for receipt uploads and processing
- **Dependencies**: python-ocr service
- **Health Check**: http://localhost:5188/health

### python-ocr
- **Port**: 8000 → 8000 (container)
- **Purpose**: OCR processing using Azure Document Intelligence
- **Health Check**: http://localhost:8000/health

## Networking

Both services run on the `receiptly-network` bridge network, allowing them to communicate using service names:
- The .NET API calls Python OCR at `http://python-ocr:8000`

## Environment Variables

### .NET API
- `AWS__AccessKeyId`: AWS access key
- `AWS__SecretAccessKey`: AWS secret key
- `AWS__S3BucketName`: S3 bucket name
- `AWS__Region`: AWS region
- `PythonOcr__ServiceUrl`: Python OCR service URL (set to `http://python-ocr:8000` in Docker)

### Python OCR
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`: Azure Document Intelligence endpoint
- `AZURE_DOCUMENT_INTELLIGENCE_KEY`: Azure Document Intelligence key

## Troubleshooting

### Service Won't Start

Check the logs:
```bash
docker-compose logs -f <service-name>
```

### Connection Issues Between Services

Verify network:
```bash
docker network ls
docker network inspect receiptly_receiptly-network
```

### Port Already in Use

Stop any local instances:
```bash
# Kill .NET API on port 5188
lsof -ti:5188 | xargs kill -9

# Kill Python OCR on port 8000
lsof -ti:8000 | xargs kill -9
```

### Environment Variables Not Loading

Ensure `.env` file exists in the project root and contains all required variables.

## Development Workflow

1. Make code changes
2. Rebuild and restart: `docker-compose up --build`
3. Test the changes
4. View logs: `docker-compose logs -f`

## Production Considerations

For production deployment:

1. Use proper secrets management (AWS Secrets Manager, Azure Key Vault)
2. Enable HTTPS with proper certificates
3. Set up proper logging and monitoring
4. Use production-grade databases
5. Implement rate limiting
6. Set up container orchestration (Kubernetes, ECS)

# ECR Migration and LLM Service Deployment - Summary

## Overview

Successfully migrated from S3-based Docker image storage to Amazon ECR (Elastic Container Registry) and added full LLM service deployment support to the infrastructure and CI/CD pipeline.

## Changes Made

### 1. Terraform Infrastructure

#### ECR Repositories (`terraform/environments/staging/main.tf`)
- ✅ Added 3 ECR repositories:
  - `receiptly-staging-dotnet-api`
  - `receiptly-staging-python-ocr`
  - `receiptly-staging-llm-service`
- ✅ Configured automatic image scanning on push
- ✅ Set 30-image retention lifecycle policy

#### AWS Secrets Manager Updates
- ✅ Added `receiptly/ecr/repositories` secret containing:
  - ECR repository URLs for all services
  - Registry ID
  - AWS region
- ✅ Updated `receiptly/ocr/service` secret to include:
  - `llm_service_url`: URL for LLM service connection

#### EC2 Instance Configuration (`terraform/modules/ec2/main.tf`)
- ✅ Added LLM service port (8500) to security group
- ✅ Created `/opt/receiptly/llm` directory for LLM service
- ✅ Added `receiptly-llm` systemd service with:
  - ECR authentication before pulling images
  - Dynamic image URL fetching from Secrets Manager
  - CloudWatch Logs integration
  - Docker network connectivity
- ✅ Updated all systemd services to use ECR instead of local images
- ✅ Made OCR service dependent on LLM service startup

#### Terraform Outputs (`terraform/environments/staging/outputs.tf`)
- ✅ Added ECR repository URL outputs
- ✅ Added ECR registry ID output

### 2. GitHub Actions CI/CD (`.github/workflows/deploy-combined.yml`)

#### Triggers
- ✅ Added `llm_service/**` path to trigger deployments

#### Secrets Retrieval
- ✅ Fetch ECR repository URLs from Secrets Manager
- ✅ Fetch LLM service URL for OCR service configuration
- ✅ Support for OpenAI and Groq API keys (via GitHub Secrets)

#### Build and Push
- ✅ Replaced S3 upload with ECR push workflow:
  1. Login to Amazon ECR
  2. Build Docker images for all 3 services
  3. Tag with `latest` and commit SHA
  4. Push to ECR
  5. Clean up local images to save disk space
- ✅ No more tar.gz compression/decompression

#### Environment Files
- ✅ Added `llm.env` creation with:
  - `USE_GROQ` (default: false)
  - `OPENAI_API_KEY` (from GitHub Secrets)
  - `MODEL_NAME` (default: gpt-4o-mini)
  - `GROQ_API_KEY` (from GitHub Secrets)
- ✅ Updated `ocr.env` to include `LLM_SERVICE_URL`

#### Deployment Steps
- ✅ ECR login on EC2 instance
- ✅ Deploy services in order:
  1. LLM Service (port 8500)
  2. Python OCR (port 8000) - depends on LLM
  3. .NET API (port 5000)
- ✅ Pull images directly from ECR (no S3 download)

#### Health Checks
- ✅ Added LLM service health check
- ✅ Check order: LLM → OCR → API

#### Deployment Summary
- ✅ Display all 3 service URLs
- ✅ Show documentation endpoints for all services
- ✅ Display ECR image tags used

### 3. Configuration Updates

#### OCR Service (`python-ocr/.env.example`)
- ✅ Added `LLM_SERVICE_URL` configuration

#### LLM Service
- ✅ Already had proper configuration in place

## Required GitHub Secrets

Add these to your GitHub repository secrets:

```
OPENAI_API_KEY=sk-your-openai-key          # Required if USE_GROQ=false
GROQ_API_KEY=your-groq-key                 # Required if USE_GROQ=true  
MODEL_NAME=gpt-4o-mini                     # Optional (default: gpt-4o-mini)
USE_GROQ=false                             # Optional (default: false)
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                          │
│  1. Build images                                            │
│  2. Push to ECR (latest + SHA tags)                         │
│  3. Deploy to EC2 via SSM                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Amazon ECR                                │
│  • receiptly-staging-dotnet-api                             │
│  • receiptly-staging-python-ocr                             │
│  • receiptly-staging-llm-service                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    EC2 Instance                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LLM Service (Port 8500)                             │   │
│  │  - OpenAI/Groq integration                          │   │
│  │  - Item canonicalization                            │   │
│  │  - Location selection                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Python OCR (Port 8000)                              │   │
│  │  - Azure Document Intelligence                      │   │
│  │  - Calls LLM service for enhancement                │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ .NET API (Port 5000)                                │   │
│  │  - Main application API                             │   │
│  │  - Calls OCR service                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Service Dependencies

```
.NET API (5000)
    ↓
Python OCR (8000)
    ↓
LLM Service (8500)
    ↓
OpenAI/Groq APIs
```

## Next Steps

1. **Apply Terraform Changes**:
   ```bash
   cd terraform/environments/staging
   terraform init
   terraform plan
   terraform apply
   ```

2. **Add GitHub Secrets**:
   - Go to Repository Settings → Secrets and Variables → Actions
   - Add `OPENAI_API_KEY` or `GROQ_API_KEY`
   - Optionally add `MODEL_NAME` and `USE_GROQ`

3. **Trigger Deployment**:
   ```bash
   git add .
   git commit -m "Add ECR support and LLM service deployment"
   git push origin feature/ocr
   ```

4. **Monitor Deployment**:
   - Watch GitHub Actions workflow
   - Check EC2 systemd services: `systemctl status receiptly-*`
   - Verify health endpoints

## Benefits of ECR Migration

### Before (S3-based)
- ❌ Large tar.gz files (500MB-1GB each)
- ❌ Slow S3 upload/download
- ❌ Extra disk space needed
- ❌ Compression/decompression overhead
- ❌ No image versioning
- ❌ Manual cleanup required

### After (ECR-based)
- ✅ Direct Docker push/pull
- ✅ Fast layer-based transfers
- ✅ Automatic deduplication
- ✅ Built-in image scanning
- ✅ SHA and latest tags
- ✅ Automatic lifecycle policies (keep 30 images)
- ✅ IAM-based access control
- ✅ No intermediate storage needed

## Rollback Instructions

If needed, you can rollback to a previous image:

```bash
# SSH into EC2 or use SSM Session Manager
cd /opt/receiptly/llm  # or /api or /ocr

# Pull specific version
docker pull <ecr-repo-url>:<commit-sha>

# Update systemd or restart manually
docker stop receiptly-llm
docker run --name receiptly-llm ... <ecr-repo-url>:<commit-sha>
```

## Monitoring

### CloudWatch Logs
- `/receiptly/staging/api` - .NET API logs
- `/receiptly/staging/ocr` - Python OCR logs  
- `/receiptly/staging/llm` - LLM Service logs

### Health Endpoints
- `http://<ec2-ip>:5000/health` - .NET API
- `http://<ec2-ip>:8000/health` - Python OCR
- `http://<ec2-ip>:8500/docs` - LLM Service

### Service Status
```bash
systemctl status receiptly-api
systemctl status receiptly-ocr
systemctl status receiptly-llm
docker ps
```

## Cost Optimization

- **ECR Storage**: First 500 MB/month free, then $0.10/GB
- **Image Lifecycle**: Automatically keeps only last 30 images
- **Data Transfer**: Free within same AWS region
- **EC2**: Using t3.micro (free tier eligible)

## Security Enhancements

- ✅ ECR repositories encrypted at rest (AES256)
- ✅ IAM role-based access (no long-lived credentials)
- ✅ Automatic vulnerability scanning
- ✅ Secrets stored in AWS Secrets Manager
- ✅ API keys never in code or logs

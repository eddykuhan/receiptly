# AWS Deployment Summary

## Overview

Successfully set up Terraform Infrastructure as Code for deploying the Receiptly Python OCR service to AWS using ECS Fargate.

## Architecture

```
GitHub → GitHub Actions → AWS ECR → ECS Fargate → Azure Document Intelligence
                              ↓
                         S3 (Receipts)
                              ↓
                    Secrets Manager (Credentials)
```

## What Was Created

### Terraform Modules (Reusable Components)

1. **ECR Module** (`terraform/modules/ecr/`)
   - Container registry for Docker images
   - Vulnerability scanning enabled
   - Lifecycle policy (30 images retained)

2. **VPC Module** (`terraform/modules/vpc/`)
   - Multi-AZ VPC with public/private subnets
   - Internet Gateway
   - NAT Gateway (optional, for production)
   - Security groups for ECS tasks

3. **ECS Module** (`terraform/modules/ecs/`)
   - Fargate cluster and service
   - Task definitions with environment variables
   - CloudWatch Logs integration
   - Health checks and auto-recovery

4. **IAM Module** (`terraform/modules/iam/`)
   - Task execution role (pull images, read secrets)
   - Task role (S3 access, application permissions)
   - Least privilege policies

5. **S3 Module** (`terraform/modules/s3/`)
   - Receipt storage bucket
   - Versioning and encryption enabled
   - Lifecycle rules for cost optimization

6. **Secrets Module** (`terraform/modules/secrets/`)
   - Stores Azure credentials securely
   - Encrypted at rest

### Environments

#### Staging (`terraform/environments/staging/`)
- **Cost**: ~$15-20/month
- **Resources**:
  - CPU: 0.5 vCPU (512)
  - Memory: 1 GB
  - Tasks: 1
  - Network: Public subnets (no NAT gateway)
  - S3 Retention: 90 days

#### Production (`terraform/environments/production/`)
- **Cost**: ~$100-150/month
- **Resources**:
  - CPU: 1 vCPU (1024)
  - Memory: 2 GB
  - Tasks: 2 (Multi-AZ)
  - Network: Private subnets with NAT gateway
  - S3 Retention: 365 days

### CI/CD Workflows

1. **Docker Build** (`.github/workflows/docker-build.yml`)
   - Builds Docker image on push
   - Tags: `{environment}-{commit-sha}`, `{environment}-latest`
   - Pushes to ECR
   - Triggers deployment

2. **Terraform Deploy** (`.github/workflows/terraform-deploy.yml`)
   - Runs `terraform plan` on PRs
   - Auto-deploys to staging on merge
   - Manual production deployment with approval

## File Structure

```
receiptly/
├── terraform/
│   ├── modules/
│   │   ├── ecr/          # Container registry
│   │   ├── vpc/          # Networking
│   │   ├── ecs/          # Container orchestration
│   │   ├── iam/          # Permissions
│   │   ├── s3/           # Storage
│   │   └── secrets/      # Secrets management
│   ├── environments/
│   │   ├── staging/      # Staging configuration
│   │   └── production/   # Production configuration
│   ├── setup-backend.sh  # One-time backend setup
│   ├── README.md         # Full documentation
│   └── QUICKSTART.md     # Quick reference
├── .github/workflows/
│   ├── docker-build.yml       # Build & push images
│   └── terraform-deploy.yml   # Deploy infrastructure
└── python-ocr/
    └── Dockerfile        # Updated with build metadata
```

## Getting Started

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.0 installed
3. **AWS CLI** configured
4. **Azure Document Intelligence** subscription

### Initial Setup (One-Time)

#### 1. Create AWS Backend Resources

```bash
cd terraform
./setup-backend.sh
```

This creates:
- S3 bucket for Terraform state
- DynamoDB table for state locking

#### 2. Configure GitHub Secrets

Add to repository secrets (Settings → Secrets and variables → Actions):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AZURE_ENDPOINT`
- `AZURE_KEY`

#### 3. Deploy Staging

```bash
cd terraform/environments/staging

# Set Azure credentials locally
export TF_VAR_azure_endpoint="https://your-endpoint.cognitiveservices.azure.com/"
export TF_VAR_azure_key="your-azure-key"

# Initialize and deploy
terraform init
terraform plan
terraform apply
```

### Deployment Workflow

#### For Regular Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-change
   ```

2. **Make Changes** to Python OCR code

3. **Push and Create PR**
   ```bash
   git push origin feature/my-change
   ```
   - GitHub Actions builds Docker image
   - Terraform runs `plan` and comments on PR

4. **Merge to Main**
   - GitHub Actions automatically:
     - Builds production image
     - Deploys to staging

#### For Production Deployment

1. Go to **Actions** → **Terraform Deploy**
2. Click **Run workflow**
3. Select **production**
4. Approve deployment
5. GitHub Actions deploys to production

## Key Features

### Infrastructure as Code
- ✅ All infrastructure version controlled
- ✅ Reproducible deployments
- ✅ State management with locking
- ✅ Terraform modules for reusability

### Security
- ✅ Secrets stored in AWS Secrets Manager
- ✅ S3 encryption enabled
- ✅ Private subnets for production
- ✅ IAM least privilege
- ✅ Terraform state encrypted

### Reliability
- ✅ Multi-AZ deployment (production)
- ✅ Health checks
- ✅ Auto-recovery
- ✅ CloudWatch logging
- ✅ Container image scanning

### Cost Optimization
- ✅ Staging uses public subnets (no NAT costs)
- ✅ Right-sized instances per environment
- ✅ S3 lifecycle rules
- ✅ Pay-per-request DynamoDB

## Common Operations

### View Service Status
```bash
aws ecs describe-services \
  --cluster receiptly-staging-cluster \
  --services receiptly-staging-service \
  --region ap-southeast-1
```

### View Logs
```bash
aws logs tail /ecs/receiptly-staging --follow --region ap-southeast-1
```

### Scale Service
Edit `terraform/environments/staging/resources.tf`:
```hcl
module "ecs" {
  # ...
  desired_count = 3
}
```

Apply:
```bash
terraform apply
```

### Update Docker Image
```bash
# Trigger via GitHub Actions (recommended)
git push origin main

# Or manually
cd terraform/environments/staging
terraform apply -var="ecr_image_tag=v1.2.3"
```

## Cost Breakdown

### Staging (~$15-20/month)
- ECS Fargate: $15/month
- CloudWatch Logs: $1/month
- S3: $0.50/month
- Secrets Manager: $0.40/month

### Production (~$100-150/month)
- ECS Fargate: $60/month
- NAT Gateway: $32/month
- CloudWatch Logs: $5/month
- S3: $5/month
- ECR: $1/month
- Data Transfer: $5-10/month

## Monitoring

### CloudWatch Dashboards
View in AWS Console:
- ECS cluster metrics
- Task CPU/Memory utilization
- Log insights

### Logs
```bash
# Real-time logs
aws logs tail /ecs/receiptly-staging --follow

# Filter for errors
aws logs tail /ecs/receiptly-staging --filter-pattern "ERROR"
```

## Troubleshooting

### State Lock Error
```bash
terraform force-unlock <LOCK_ID>
```

### ECS Task Not Starting
1. Check CloudWatch logs
2. Verify secrets are set correctly
3. Check IAM permissions
4. Verify Docker image exists in ECR

### High Costs
1. Check ECS task count
2. Review NAT Gateway usage
3. Check S3 storage size
4. Review CloudWatch Logs retention

## Next Steps

### Recommended Improvements

1. **Add Application Load Balancer**
   - Distribute traffic across tasks
   - Enable HTTPS with ACM certificate
   - Add custom domain

2. **Add Auto Scaling**
   - Scale based on CPU/memory
   - Scale based on request count
   - Schedule scaling for peak hours

3. **Add Monitoring Alerts**
   - High CPU/memory usage
   - Task failures
   - High error rates

4. **Add CI/CD Tests**
   - Unit tests before build
   - Integration tests after deploy
   - Smoke tests in staging

5. **Add Backup Strategy**
   - S3 cross-region replication
   - RDS snapshots (if added later)
   - Disaster recovery plan

## Documentation

- **Full Guide**: `terraform/README.md`
- **Quick Reference**: `terraform/QUICKSTART.md`
- **Module Docs**: Each module has its own README

## Resources

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

---

**Created**: 2024
**Managed By**: Terraform
**Region**: ap-southeast-1 (Singapore)

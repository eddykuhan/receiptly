# Terraform Infrastructure

This directory contains Terraform configurations for deploying Receiptly's Python OCR service to AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                         VPC                              │  │
│  │                                                          │  │
│  │  ┌─────────────┐     ┌─────────────┐     ┌──────────┐  │  │
│  │  │   Public    │────▶│     NAT     │────▶│ Internet │  │  │
│  │  │   Subnet    │     │   Gateway   │     │ Gateway  │  │  │
│  │  └─────────────┘     └─────────────┘     └──────────┘  │  │
│  │                             │                           │  │
│  │                             ▼                           │  │
│  │  ┌─────────────────────────────────────────────────┐   │  │
│  │  │         Private Subnets (Multi-AZ)              │   │  │
│  │  │                                                 │   │  │
│  │  │  ┌────────────────────────────────────────┐    │   │  │
│  │  │  │      ECS Fargate Cluster               │    │   │  │
│  │  │  │                                        │    │   │  │
│  │  │  │  ┌──────────┐     ┌──────────┐       │    │   │  │
│  │  │  │  │  Task 1  │     │  Task 2  │       │    │   │  │
│  │  │  │  │  (OCR)   │     │  (OCR)   │       │    │   │  │
│  │  │  │  └──────────┘     └──────────┘       │    │   │  │
│  │  │  └────────────────────────────────────────┘    │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────┐   ┌────────────┐   ┌─────────────────────┐   │
│  │    ECR     │   │     S3     │   │  Secrets Manager    │   │
│  │  (Images)  │   │ (Receipts) │   │ (Azure Credentials) │   │
│  └────────────┘   └────────────┘   └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
terraform/
├── modules/                    # Reusable Terraform modules
│   ├── ecr/                   # ECR repository for Docker images
│   ├── vpc/                   # VPC, subnets, security groups
│   ├── ecs/                   # ECS cluster, service, task definition
│   ├── iam/                   # IAM roles and policies
│   ├── s3/                    # S3 bucket for receipt storage
│   └── secrets/               # Secrets Manager for credentials
├── environments/
│   ├── staging/              # Staging environment
│   └── production/           # Production environment
└── README.md                 # This file
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.0 ([Installation Guide](https://developer.hashicorp.com/terraform/downloads))
3. **AWS CLI** configured ([Setup Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html))
4. **Azure Document Intelligence** subscription for OCR service

## Initial Setup

### 1. Create Terraform Backend Resources

Before running Terraform, create the S3 bucket and DynamoDB table for state management:

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket receiptly-terraform-state \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket receiptly-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket receiptly-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name receiptly-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-southeast-1
```

### 2. Configure Azure Credentials

Set your Azure Document Intelligence credentials as environment variables:

```bash
export TF_VAR_azure_endpoint="https://your-endpoint.cognitiveservices.azure.com/"
export TF_VAR_azure_key="your-azure-key"
```

Or create a `terraform.tfvars` file (DO NOT COMMIT):

```hcl
azure_endpoint = "https://your-endpoint.cognitiveservices.azure.com/"
azure_key      = "your-azure-key"
```

### 3. Configure GitHub Secrets (for CI/CD)

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AZURE_ENDPOINT`: Azure Document Intelligence endpoint
- `AZURE_KEY`: Azure Document Intelligence key

## Deployment

### Local Deployment

#### Deploy to Staging

```bash
cd terraform/environments/staging

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply changes
terraform apply
```

#### Deploy to Production

```bash
cd terraform/environments/production

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply changes
terraform apply
```

### CI/CD Deployment

The GitHub Actions workflow automatically:

1. **On Pull Request**: Runs `terraform plan` and comments the plan on the PR
2. **On Merge to Main**: Deploys to staging automatically
3. **Manual Trigger**: Can deploy to production via workflow dispatch

#### Workflow Triggers

```yaml
# Automatic staging deployment
git checkout main
git merge feature-branch
git push origin main

# Manual production deployment
# Go to Actions → Terraform Deploy → Run workflow → Select "production"
```

## Environments

### Staging

- **Purpose**: Testing and development
- **Cost**: ~$15-20/month
- **Specs**:
  - CPU: 0.5 vCPU (512)
  - Memory: 1 GB (1024)
  - Tasks: 1
  - Network: Public subnets (no NAT gateway)
  - S3 Retention: 90 days
  - Logging: INFO level

### Production

- **Purpose**: Live customer traffic
- **Cost**: ~$100-150/month
- **Specs**:
  - CPU: 1 vCPU (1024)
  - Memory: 2 GB (2048)
  - Tasks: 2 (Multi-AZ)
  - Network: Private subnets with NAT gateway
  - S3 Retention: 365 days
  - Logging: WARNING level

## Modules Reference

### ECR Module

Creates a private ECR repository for Docker images.

**Inputs:**
- `repository_name`: Name of the ECR repository
- `image_tag_mutability`: MUTABLE or IMMUTABLE
- `scan_on_push`: Enable vulnerability scanning

**Outputs:**
- `repository_url`: ECR repository URL
- `repository_arn`: ECR repository ARN

### VPC Module

Creates VPC with public and private subnets across multiple AZs.

**Inputs:**
- `vpc_cidr`: CIDR block for VPC
- `availability_zones`: List of AZs
- `public_subnet_cidrs`: Public subnet CIDRs
- `private_subnet_cidrs`: Private subnet CIDRs
- `enable_nat_gateway`: Enable NAT gateway for private subnets
- `single_nat_gateway`: Use single NAT vs. one per AZ

**Outputs:**
- `vpc_id`: VPC ID
- `public_subnet_ids`: Public subnet IDs
- `private_subnet_ids`: Private subnet IDs
- `ecs_security_group_id`: Security group for ECS tasks

### ECS Module

Creates ECS Fargate cluster, task definition, and service.

**Inputs:**
- `ecr_repository_url`: ECR repository URL
- `image_tag`: Docker image tag
- `cpu`: Task CPU (256, 512, 1024, 2048, 4096)
- `memory`: Task memory in MB
- `desired_count`: Number of tasks to run
- `environment_variables`: Environment variables map
- `secrets`: Secrets from AWS Secrets Manager
- `assign_public_ip`: Assign public IP (for public subnets)

**Outputs:**
- `cluster_name`: ECS cluster name
- `service_name`: ECS service name
- `task_definition_arn`: Task definition ARN
- `log_group_name`: CloudWatch log group name

### IAM Module

Creates IAM roles for ECS task execution and application.

**Inputs:**
- `s3_bucket_arn`: S3 bucket ARN for permissions
- `secrets_arns`: List of Secrets Manager ARNs

**Outputs:**
- `ecs_task_execution_role_arn`: Task execution role ARN
- `ecs_task_role_arn`: Task role ARN

### S3 Module

Creates S3 bucket for receipt storage.

**Inputs:**
- `bucket_name`: Bucket name
- `versioning_enabled`: Enable versioning
- `lifecycle_rules`: List of lifecycle rules

**Outputs:**
- `bucket_id`: S3 bucket name
- `bucket_arn`: S3 bucket ARN

### Secrets Module

Creates secrets in AWS Secrets Manager.

**Inputs:**
- `secrets`: Map of secret names to values
- `recovery_window_days`: Recovery window for deleted secrets

**Outputs:**
- `secret_arns`: Map of secret names to ARNs

## Common Operations

### View Outputs

```bash
cd terraform/environments/staging
terraform output
```

### Update Docker Image

```bash
cd terraform/environments/staging

# Update with new image tag
terraform apply -var="ecr_image_tag=v1.2.3"
```

### Scale Service

Edit `resources.tf` in the environment:

```hcl
module "ecs" {
  # ...
  desired_count = 3  # Scale to 3 tasks
}
```

Apply changes:

```bash
terraform apply
```

### View Logs

```bash
# Get log group name
cd terraform/environments/staging
LOG_GROUP=$(terraform output -raw log_group_name)

# Tail logs
aws logs tail $LOG_GROUP --follow --region ap-southeast-1
```

### Destroy Environment

⚠️ **Warning**: This will delete all resources!

```bash
cd terraform/environments/staging
terraform destroy
```

## Cost Estimation

### Staging (~$15-20/month)

- **ECS Fargate**: $15/month (0.5 vCPU, 1GB, 1 task, 730 hours)
- **CloudWatch Logs**: $1/month (~1GB)
- **S3**: $0.50/month (~50GB, 90-day retention)
- **Secrets Manager**: $0.40/month (1 secret)
- **Data Transfer**: Minimal

### Production (~$100-150/month)

- **ECS Fargate**: $60/month (1 vCPU, 2GB, 2 tasks, 730 hours)
- **NAT Gateway**: $32/month
- **CloudWatch Logs**: $5/month (~5GB)
- **S3**: $5/month (~500GB, 365-day retention)
- **Secrets Manager**: $1.20/month (3 secrets)
- **Data Transfer**: $5-10/month
- **ECR**: $1/month (~10GB)

## Troubleshooting

### State Lock Error

If Terraform is stuck with a state lock:

```bash
# List locks
aws dynamodb scan --table-name receiptly-terraform-locks

# Force unlock (use the Lock ID from error message)
terraform force-unlock <LOCK_ID>
```

### ECS Task Not Starting

Check task logs:

```bash
aws ecs describe-tasks \
  --cluster receiptly-staging-cluster \
  --tasks <task-id> \
  --region ap-southeast-1
```

View CloudWatch logs:

```bash
aws logs tail /ecs/receiptly-staging --follow --region ap-southeast-1
```

### Permission Errors

Ensure IAM roles have correct policies:

```bash
cd terraform/environments/staging
terraform state show module.iam.aws_iam_role.ecs_task_execution
```

### High Costs

Check CloudWatch metrics:

```bash
# CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=receiptly-staging-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 3600 \
  --statistics Average \
  --region ap-southeast-1
```

## Security Best Practices

1. ✅ **Secrets Management**: All credentials in AWS Secrets Manager
2. ✅ **Encryption**: S3 encryption enabled, secrets encrypted at rest
3. ✅ **Network Security**: Private subnets for production, security groups restrict access
4. ✅ **State Security**: Terraform state encrypted in S3 with versioning
5. ✅ **Least Privilege**: IAM roles with minimal required permissions

## References

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Task Definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review Terraform plan output
3. Consult AWS documentation
4. Contact DevOps team

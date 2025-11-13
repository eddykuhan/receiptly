# Terraform Quick Start Guide

## First-Time Setup

### 1. Create AWS Backend Resources

```bash
cd terraform
./setup-backend.sh
```

This creates:
- S3 bucket: `receiptly-terraform-state`
- DynamoDB table: `receiptly-terraform-locks`

### 2. Set Azure Credentials

```bash
export TF_VAR_azure_endpoint="https://your-endpoint.cognitiveservices.azure.com/"
export TF_VAR_azure_key="your-azure-key"
```

Or create `terraform/environments/staging/terraform.tfvars`:
```hcl
azure_endpoint = "https://your-endpoint.cognitiveservices.azure.com/"
azure_key      = "your-azure-key"
```

⚠️ **Never commit `terraform.tfvars` to git!**

### 3. Deploy Staging Environment

```bash
cd terraform/environments/staging

# Initialize Terraform
terraform init

# Review changes
terraform plan

# Apply changes
terraform apply
```

## Daily Commands

### View Current Infrastructure

```bash
terraform show
```

### View Outputs

```bash
terraform output
terraform output ecr_repository_url
```

### Update Infrastructure

```bash
# Make changes to .tf files
terraform plan    # Review changes
terraform apply   # Apply changes
```

### Deploy New Docker Image

```bash
# Push new image to ECR
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin <ecr-url>

docker build -t receiptly-python-ocr:v1.2.3 .
docker tag receiptly-python-ocr:v1.2.3 <ecr-url>:v1.2.3
docker push <ecr-url>:v1.2.3

# Update ECS service
cd terraform/environments/staging
terraform apply -var="ecr_image_tag=v1.2.3"
```

### Scale ECS Service

Edit `resources.tf`:
```hcl
module "ecs" {
  # ...
  desired_count = 3  # Change from 1 to 3
}
```

Apply:
```bash
terraform apply
```

### View Logs

```bash
# Get log group name
LOG_GROUP=$(terraform output -raw log_group_name)

# Tail logs
aws logs tail $LOG_GROUP --follow --region ap-southeast-1

# Filter logs
aws logs tail $LOG_GROUP --follow --filter-pattern "ERROR" --region ap-southeast-1
```

## GitHub Actions Deployment

### Setup GitHub Secrets

Go to: Settings → Secrets and variables → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AZURE_ENDPOINT`
- `AZURE_KEY`

### Automatic Deployment

1. Create feature branch
2. Make changes to Terraform files
3. Open Pull Request
4. GitHub Actions runs `terraform plan` and comments on PR
5. Merge PR to `main`
6. GitHub Actions automatically deploys to **staging**

### Manual Production Deployment

1. Go to **Actions** tab
2. Select **Terraform Deploy** workflow
3. Click **Run workflow**
4. Select environment: **production**
5. Click **Run workflow**

## Common Tasks

### Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster receiptly-staging-cluster \
  --services receiptly-staging-service \
  --region ap-southeast-1
```

### Restart ECS Service

```bash
aws ecs update-service \
  --cluster receiptly-staging-cluster \
  --service receiptly-staging-service \
  --force-new-deployment \
  --region ap-southeast-1
```

### View ECS Task Details

```bash
# List tasks
aws ecs list-tasks \
  --cluster receiptly-staging-cluster \
  --service-name receiptly-staging-service \
  --region ap-southeast-1

# Describe specific task
aws ecs describe-tasks \
  --cluster receiptly-staging-cluster \
  --tasks <task-arn> \
  --region ap-southeast-1
```

### Access S3 Bucket

```bash
# List receipts
aws s3 ls s3://receiptly-receipts-staging/

# Download receipt
aws s3 cp s3://receiptly-receipts-staging/receipt-123.json .

# Upload receipt
aws s3 cp receipt.json s3://receiptly-receipts-staging/
```

### View Secrets

```bash
# List secrets
aws secretsmanager list-secrets --region ap-southeast-1

# Get secret value
aws secretsmanager get-secret-value \
  --secret-id receiptly/staging/azure-endpoint \
  --region ap-southeast-1
```

### Update Secret

```bash
aws secretsmanager update-secret \
  --secret-id receiptly/staging/azure-key \
  --secret-string "new-key-value" \
  --region ap-southeast-1
```

After updating secrets, restart ECS service to pick up changes.

## Troubleshooting

### State Lock Error

```bash
# Force unlock (use Lock ID from error message)
terraform force-unlock <LOCK_ID>
```

### Permission Denied Errors

Check IAM role policies:
```bash
terraform state show module.iam.aws_iam_role.ecs_task_execution
terraform state show module.iam.aws_iam_role.ecs_task
```

### ECS Task Won't Start

1. Check task stopped reason:
```bash
aws ecs describe-tasks \
  --cluster receiptly-staging-cluster \
  --tasks <task-arn> \
  --region ap-southeast-1 \
  --query 'tasks[0].stoppedReason'
```

2. Check CloudWatch logs:
```bash
aws logs tail /ecs/receiptly-staging --region ap-southeast-1
```

3. Common issues:
   - Invalid environment variables
   - Missing secrets
   - Incorrect IAM permissions
   - Image pull errors (check ECR permissions)

### Destroy Environment

⚠️ **Warning**: This deletes all resources!

```bash
cd terraform/environments/staging
terraform destroy
```

## Cost Monitoring

### View Current Month Costs

```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Set Billing Alert

1. Go to AWS Console → Billing → Budgets
2. Create budget for Receiptly project
3. Set alert threshold (e.g., $50/month)
4. Add email notification

## Resources

- [Full Documentation](./README.md)
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS CLI Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/index.html)

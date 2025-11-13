#!/bin/bash

# Terraform Backend Setup Script
# This script creates the S3 bucket and DynamoDB table required for Terraform state management

set -e

# Configuration
BUCKET_NAME="receiptly-terraform-state"
DYNAMODB_TABLE="receiptly-terraform-locks"
AWS_REGION="ap-southeast-1"

echo "🚀 Setting up Terraform backend resources..."
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured. Please run:"
    echo "   aws configure"
    exit 1
fi

echo "✅ AWS CLI is configured"
echo "📝 Using account: $(aws sts get-caller-identity --query Account --output text)"
echo ""

# Create S3 bucket
echo "📦 Creating S3 bucket: $BUCKET_NAME"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "   ℹ️  Bucket already exists"
else
    if [ "$AWS_REGION" == "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    echo "   ✅ Bucket created"
fi

# Enable versioning
echo "🔄 Enabling versioning on S3 bucket"
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled
echo "   ✅ Versioning enabled"

# Enable encryption
echo "🔒 Enabling encryption on S3 bucket"
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
        }]
    }'
echo "   ✅ Encryption enabled"

# Block public access
echo "🚫 Blocking public access on S3 bucket"
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "   ✅ Public access blocked"

# Create DynamoDB table
echo "🗄️  Creating DynamoDB table: $DYNAMODB_TABLE"
if aws dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$AWS_REGION" &>/dev/null; then
    echo "   ℹ️  Table already exists"
else
    aws dynamodb create-table \
        --table-name "$DYNAMODB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --tags Key=Project,Value=receiptly Key=ManagedBy,Value=Terraform \
        > /dev/null
    
    echo "   ⏳ Waiting for table to be active..."
    aws dynamodb wait table-exists \
        --table-name "$DYNAMODB_TABLE" \
        --region "$AWS_REGION"
    
    echo "   ✅ Table created"
fi

echo ""
echo "✅ Terraform backend setup complete!"
echo ""
echo "📋 Backend Configuration:"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   DynamoDB Table: $DYNAMODB_TABLE"
echo "   Region: $AWS_REGION"
echo ""
echo "Next steps:"
echo "1. Set your Azure credentials:"
echo "   export TF_VAR_azure_endpoint=\"https://your-endpoint.cognitiveservices.azure.com/\""
echo "   export TF_VAR_azure_key=\"your-azure-key\""
echo ""
echo "2. Initialize Terraform:"
echo "   cd terraform/environments/staging"
echo "   terraform init"
echo ""
echo "3. Review and apply:"
echo "   terraform plan"
echo "   terraform apply"

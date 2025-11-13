#!/bin/bash

# Alternative setup using AWS CloudFormation
# This may work with different IAM permissions than the direct AWS CLI approach

set -e

STACK_NAME="receiptly-terraform-backend"
AWS_REGION="ap-southeast-1"

echo "🚀 Setting up Terraform backend using CloudFormation..."
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed."
    exit 1
fi

# Check if CloudFormation template exists
if [ ! -f "terraform-backend.cfn.yaml" ]; then
    echo "❌ terraform-backend.cfn.yaml not found"
    echo "Make sure you're in the terraform directory"
    exit 1
fi

# Check AWS credentials
echo "📝 Current AWS identity:"
aws sts get-caller-identity || {
    echo "❌ AWS credentials are not configured"
    exit 1
}
echo ""

# Check if stack already exists
echo "🔍 Checking if CloudFormation stack exists..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &>/dev/null; then
    echo "   ℹ️  Stack already exists, updating..."
    
    aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://terraform-backend.cfn.yaml \
        --region "$AWS_REGION" \
        --capabilities CAPABILITY_IAM || {
        
        if [ $? -eq 254 ]; then
            echo "   ℹ️  No updates are needed"
        else
            echo "   ❌ Stack update failed"
            exit 1
        fi
    }
    
    if [ $? -eq 0 ]; then
        echo "   ⏳ Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION"
        echo "   ✅ Stack updated"
    fi
else
    echo "   Creating new stack..."
    
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://terraform-backend.cfn.yaml \
        --region "$AWS_REGION" \
        --capabilities CAPABILITY_IAM
    
    echo "   ⏳ Waiting for stack creation to complete (this may take a few minutes)..."
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION"
    
    echo "   ✅ Stack created"
fi

# Get stack outputs
echo ""
echo "📋 Getting stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs')

BUCKET_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="StateBucketName") | .OutputValue')
TABLE_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LockTableName") | .OutputValue')

echo ""
echo "✅ Terraform backend setup complete!"
echo ""
echo "📋 Backend Configuration:"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   DynamoDB Table: $TABLE_NAME"
echo "   Region: $AWS_REGION"
echo ""
echo "Next steps:"
echo "1. Set your Azure credentials:"
echo "   export TF_VAR_azure_endpoint=\"https://your-endpoint.cognitiveservices.azure.com/\""
echo "   export TF_VAR_azure_key=\"your-azure-key\""
echo ""
echo "2. Initialize Terraform:"
echo "   cd environments/staging"
echo "   terraform init"
echo ""
echo "3. Review and apply:"
echo "   terraform plan"
echo "   terraform apply"

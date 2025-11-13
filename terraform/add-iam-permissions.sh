#!/bin/bash

# Script to add required IAM permissions for Terraform deployment
# Run this with an admin account or ask your AWS administrator to run it

set -e

POLICY_NAME="ReceiptlyTerraformPolicy"
USER_NAME="cli"  # Change this to your IAM user name if different
AWS_ACCOUNT_ID="947685297250"
AWS_REGION="ap-southeast-1"

echo "🔐 Adding IAM permissions for Terraform deployment..."
echo ""
echo "This script will create and attach an IAM policy to user: $USER_NAME"
echo "Policy name: $POLICY_NAME"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed."
    exit 1
fi

# Check if policy file exists
if [ ! -f "required-iam-policy.json" ]; then
    echo "❌ required-iam-policy.json not found"
    echo "Make sure you're in the terraform directory"
    exit 1
fi

# Check current user's permissions
echo "📝 Current AWS identity:"
aws sts get-caller-identity || {
    echo "❌ AWS credentials are not configured"
    exit 1
}
echo ""

# Check if policy already exists
echo "🔍 Checking if policy already exists..."
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn "$POLICY_ARN" &>/dev/null; then
    echo "   ℹ️  Policy already exists"
    
    # Get the current version
    CURRENT_VERSION=$(aws iam get-policy --policy-arn "$POLICY_ARN" --query 'Policy.DefaultVersionId' --output text)
    echo "   Current version: $CURRENT_VERSION"
    
    # Create a new version
    echo "🔄 Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document file://required-iam-policy.json \
        --set-as-default
    
    echo "   ✅ Policy updated"
else
    echo "   Policy does not exist, creating new one..."
    
    # Create the policy
    echo "📋 Creating IAM policy..."
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://required-iam-policy.json \
        --description "Permissions for Receiptly Terraform deployments"
    
    echo "   ✅ Policy created"
fi

# Attach policy to user
echo "🔗 Attaching policy to user: $USER_NAME"
if aws iam attach-user-policy \
    --user-name "$USER_NAME" \
    --policy-arn "$POLICY_ARN" 2>/dev/null; then
    echo "   ✅ Policy attached"
else
    # Check if already attached
    if aws iam list-attached-user-policies --user-name "$USER_NAME" | grep -q "$POLICY_NAME"; then
        echo "   ℹ️  Policy already attached"
    else
        echo "   ❌ Failed to attach policy"
        echo ""
        echo "You may need administrator permissions to attach policies."
        echo "Ask your AWS administrator to run this command:"
        echo ""
        echo "aws iam attach-user-policy \\"
        echo "  --user-name $USER_NAME \\"
        echo "  --policy-arn $POLICY_ARN"
        exit 1
    fi
fi

echo ""
echo "✅ IAM permissions configured successfully!"
echo ""
echo "📋 Policy ARN: $POLICY_ARN"
echo "👤 User: $USER_NAME"
echo ""
echo "⏳ Wait a few seconds for IAM changes to propagate, then run:"
echo "   ./setup-backend.sh"
echo ""

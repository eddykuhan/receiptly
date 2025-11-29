#!/bin/bash
set -e

echo "🚀 Deploying .NET API from S3 to EC2 via SSM"

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=receiptly-staging-app-server" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)

echo "📍 Instance ID: $INSTANCE_ID"

# Deploy via SSM
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "cd /opt/receiptly/api",
    "sudo aws s3 cp s3://receiptly-terraform-state/deployments/api-image.tar.gz .",
    "sudo aws s3 cp s3://receiptly-terraform-state/deployments/api.env .env",
    "sudo docker load -i api-image.tar.gz",
    "sudo rm api-image.tar.gz",
    "sudo docker network create receiptly_default 2>/dev/null || true",
    "sudo systemctl enable receiptly-api",
    "sudo systemctl restart receiptly-api",
    "sleep 5",
    "sudo systemctl status receiptly-api --no-pager"
  ]' \
  --output text \
  --query "Command.CommandId")

echo "⏳ Command ID: $COMMAND_ID"
echo "⏳ Waiting for deployment to complete..."

# Wait for command to complete
aws ssm wait command-executed \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID"

# Get command output
OUTPUT=$(aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --query "StandardOutputContent" \
  --output text)

echo ""
echo "📋 Deployment output:"
echo "$OUTPUT"

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

echo ""
echo "🧪 Testing health endpoint..."
sleep 3

if curl -f -s "http://$INSTANCE_IP:5000/health" > /dev/null; then
    echo "✅ API is healthy!"
    echo ""
    echo "🎉 Deployment complete!"
    echo "   API URL: http://$INSTANCE_IP:5000"
    echo "   Swagger: http://$INSTANCE_IP:5000/swagger"
else
    echo "❌ API health check failed"
    exit 1
fi

#!/bin/bash
set -e

echo "🚀 Manual deployment script for .NET API to EC2"
echo ""

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=receiptly-staging-app-server" \
            "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

echo "📍 Instance ID: $INSTANCE_ID"

# Build Docker image
echo ""
echo "🔨 Building .NET API Docker image..."
cd dotnet-api
docker build -t receiptly-api:latest .

# Save image
echo ""
echo "💾 Saving Docker image..."
cd ..
docker save receiptly-api:latest | gzip > api-image.tar.gz

# Upload to S3
echo ""
echo "☁️  Uploading to S3..."
aws s3 cp api-image.tar.gz s3://receiptly-terraform-state/deployments/api-image.tar.gz

# Create .env file
echo ""
echo "📝 Creating environment file..."
cat > api.env <<EOF
AWS__Region=ap-southeast-1
ASPNETCORE_ENVIRONMENT=Production
ASPNETCORE_URLS=http://+:5000
EOF

aws s3 cp api.env s3://receiptly-terraform-state/deployments/api.env

# Deploy via SSM
echo ""
echo "🚢 Deploying to EC2..."
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "set -e",
    "echo === Downloading .NET API image ===",
    "cd /opt/receiptly/api",
    "aws s3 cp s3://receiptly-terraform-state/deployments/api-image.tar.gz .",
    "aws s3 cp s3://receiptly-terraform-state/deployments/api.env .env",
    "echo === Loading Docker image ===",
    "docker load < api-image.tar.gz",
    "echo === Starting API service ===",
    "systemctl enable receiptly-api",
    "systemctl restart receiptly-api",
    "sleep 5",
    "echo === Checking service status ===",
    "systemctl status receiptly-api --no-pager || true",
    "docker ps -a | grep api || true",
    "echo === Done ==="
  ]' \
  --output text \
  --query 'Command.CommandId')

echo "Command ID: $COMMAND_ID"
echo ""
echo "⏳ Waiting for deployment to complete..."
sleep 20

# Get output
echo ""
echo "📋 Deployment output:"
aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --query 'StandardOutputContent' \
  --output text

# Test
echo ""
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "🏥 Testing API at http://$INSTANCE_IP:5000/health"
sleep 5
curl -f "http://$INSTANCE_IP:5000/health" && echo "" && echo "✅ API is healthy!" || echo "❌ API health check failed"

echo ""
echo "🎉 Deployment complete!"
echo "API URL: http://$INSTANCE_IP:5000"
echo "Swagger: http://$INSTANCE_IP:5000/swagger"

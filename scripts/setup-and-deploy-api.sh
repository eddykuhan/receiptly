#!/bin/bash
set -e

echo "🔧 Setting up .NET API infrastructure on EC2"

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=receiptly-staging-app-server" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)

echo "📍 Instance ID: $INSTANCE_ID"

# Execute setup via SSM
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "sudo mkdir -p /opt/receiptly/api",
    "sudo chown ec2-user:ec2-user /opt/receiptly/api",
    "sudo tee /etc/systemd/system/receiptly-api.service > /dev/null <<EOF",
    "[Unit]",
    "Description=Receiptly .NET API Service",
    "After=docker.service",
    "Requires=docker.service",
    "",
    "[Service]",
    "Type=simple",
    "WorkingDirectory=/opt/receiptly/api",
    "ExecStartPre=-/usr/bin/docker stop receiptly-api",
    "ExecStartPre=-/usr/bin/docker rm receiptly-api",
    "ExecStart=/usr/bin/docker run --name receiptly-api -p 5000:5000 --env-file /opt/receiptly/api/.env receiptly-api:latest",
    "ExecStop=/usr/bin/docker stop receiptly-api",
    "Restart=always",
    "",
    "[Install]",
    "WantedBy=multi-user.target",
    "EOF",
    "sudo systemctl daemon-reload",
    "echo Setup complete"
  ]' \
  --output text \
  --query "Command.CommandId")

echo "⏳ Command ID: $COMMAND_ID"
echo "⏳ Waiting for setup to complete..."

# Wait for command to complete
aws ssm wait command-executed \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID"

# Get output
OUTPUT=$(aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --query "StandardOutputContent" \
  --output text)

echo ""
echo "📋 Setup output:"
echo "$OUTPUT"

echo ""
echo "✅ Infrastructure setup complete!"
echo "Now running deployment..."
echo ""

# Now deploy the API
./scripts/deploy-api-via-ssm.sh

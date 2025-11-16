# ==========================================
# EC2 Instance for Python OCR Service
# ==========================================

# Get latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group for Python OCR Service
resource "aws_security_group" "ocr_service" {
  name_prefix = "${var.project_name}-${var.environment}-app-sg-"
  description = "Security group for application services (API + OCR) EC2 instance"
  vpc_id      = var.vpc_id

  # Allow HTTP access to .NET API (port 5000)
  ingress {
    description = ".NET API service"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow HTTP access to Python OCR service (port 8000)
  ingress {
    description = "Python OCR service"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow SSH access (optional, for debugging)
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidr_blocks
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-sg"
    Environment = var.environment
    Project     = var.project_name
  }

  lifecycle {
    create_before_destroy = true
  }
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "ocr_instance" {
  name_prefix = "${var.project_name}-${var.environment}-ocr-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-instance-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for accessing Secrets Manager
resource "aws_iam_role_policy" "ocr_secrets_access" {
  name_prefix = "secrets-access-"
  role        = aws_iam_role.ocr_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:receiptly/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::receiptly-terraform-state/deployments/*"
        ]
      }
    ]
  })
}

# Attach AWS managed policy for SSM
resource "aws_iam_role_policy_attachment" "ssm_managed_instance" {
  role       = aws_iam_role.ocr_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ocr_instance" {
  name_prefix = "${var.project_name}-${var.environment}-ocr-profile-"
  role        = aws_iam_role.ocr_instance.name

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-instance-profile"
    Environment = var.environment
    Project     = var.project_name
  }
}

# User Data Script to install Docker and CloudWatch Agent
locals {
  user_data = <<-EOT
    #!/bin/bash
    set -e
    
    # Update system
    dnf update -y
    
    # Install Docker and CloudWatch Agent
    dnf install -y docker amazon-cloudwatch-agent amazon-ssm-agent
    
    # Start and enable services
    systemctl start docker
    systemctl enable docker
    systemctl start amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    
    # Add ec2-user to docker group
    usermod -a -G docker ec2-user
    
    # Create deployment directories
    mkdir -p /opt/receiptly/api
    mkdir -p /opt/receiptly/ocr
    mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
    
    # Configure CloudWatch Agent
    cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'CWEOF'
    {
      "logs": {
        "logs_collected": {
          "files": {
            "collect_list": [
              {
                "file_path": "/var/log/messages",
                "log_group_name": "/receiptly/${var.environment}/system",
                "log_stream_name": "{instance_id}/messages",
                "timestamp_format": "%b %d %H:%M:%S"
              }
            ]
          }
        },
        "log_stream_name": "{instance_id}"
      }
    }
    CWEOF
    
    # Start CloudWatch Agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
      -a fetch-config \
      -m ec2 \
      -s \
      -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
    
    # Configure Docker daemon to use JSON file logging
    cat > /etc/docker/daemon.json <<'DOCKEREOF'
    {
      "log-driver": "awslogs",
      "log-opts": {
        "awslogs-region": "${var.aws_region}",
        "awslogs-group": "/receiptly/${var.environment}",
        "tag": "{{.Name}}"
      }
    }
    DOCKEREOF
    
    # Restart Docker to apply logging configuration
    systemctl restart docker
    
    # Create Docker network for inter-service communication
    docker network create receiptly_default 2>/dev/null || true
    
    # Create systemd service for .NET API
    cat > /etc/systemd/system/receiptly-api.service <<'EOF'
    [Unit]
    Description=Receiptly .NET API Service
    After=docker.service
    Requires=docker.service
    
    [Service]
    Type=simple
    WorkingDirectory=/opt/receiptly/api
    ExecStartPre=-/usr/bin/docker stop receiptly-api
    ExecStartPre=-/usr/bin/docker rm receiptly-api
    ExecStart=/usr/bin/docker run --name receiptly-api --network receiptly_default -p 5000:5000 --log-driver=awslogs --log-opt awslogs-region=${var.aws_region} --log-opt awslogs-group=/receiptly/${var.environment}/api --log-opt awslogs-stream=receiptly-api --env-file /opt/receiptly/api/.env receiptly-api:latest
    ExecStop=/usr/bin/docker stop receiptly-api
    Restart=always
    
    [Install]
    WantedBy=multi-user.target
    EOF
    
    # Create systemd service for Python OCR
    cat > /etc/systemd/system/receiptly-ocr.service <<'EOF'
    [Unit]
    Description=Receiptly Python OCR Service
    After=docker.service
    Requires=docker.service
    
    [Service]
    Type=simple
    WorkingDirectory=/opt/receiptly/ocr
    ExecStartPre=-/usr/bin/docker stop receiptly-ocr
    ExecStartPre=-/usr/bin/docker rm receiptly-ocr
    ExecStart=/usr/bin/docker run --name receiptly-ocr --network receiptly_default -p 8000:8000 --log-driver=awslogs --log-opt awslogs-region=${var.aws_region} --log-opt awslogs-group=/receiptly/${var.environment}/ocr --log-opt awslogs-stream=receiptly-ocr --env-file /opt/receiptly/ocr/.env python-ocr:latest
    ExecStop=/usr/bin/docker stop receiptly-ocr
    Restart=always
    
    [Install]
    WantedBy=multi-user.target
    EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    # Note: Initial deployment will be done via GitHub Actions
    echo "EC2 instance ready for deployment with CloudWatch Logs" > /opt/receiptly/status.txt
  EOT
}

# EC2 Instance
resource "aws_instance" "ocr_service" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ocr_service.id]
  iam_instance_profile   = aws_iam_instance_profile.ocr_instance.name
  
  user_data = local.user_data

  # Amazon Linux 2023 requires minimum 30GB volume
  # Note: Free tier includes 30GB of EBS storage
  root_block_device {
    volume_type           = "gp2"
    volume_size           = 30
    delete_on_termination = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-server"
    Environment = var.environment
    Project     = var.project_name
    Service     = "api-ocr"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for static public IP address
resource "aws_eip" "ocr_service" {
  domain   = "vpc"
  instance = aws_instance.ocr_service.id

  tags = {
    Name        = "${var.project_name}-${var.environment}-eip"
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [aws_instance.ocr_service]
}

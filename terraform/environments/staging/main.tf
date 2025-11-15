terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "s3" {
    bucket         = "receiptly-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "ap-southeast-1"
    encrypt        = true
    dynamodb_table = "receiptly-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ==========================================
# VPC for RDS and Future Services
# ==========================================
module "vpc" {
  source = "../../modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = "10.0.0.0/16"

  # Use 2 AZs (minimum for RDS)
  availability_zones = ["ap-southeast-1a", "ap-southeast-1b"]

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24"]

  # NAT gateway not needed for free tier staging (RDS in private subnets, public access enabled)
  enable_nat_gateway = false
}

# ==========================================
# RDS PostgreSQL Database
# ==========================================
module "database" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = var.environment

  # Network Configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  # Allow access from anywhere for staging (GitHub Actions, local dev)
  # For production: restrict to specific IPs or VPC CIDR
  allowed_cidr_blocks = ["0.0.0.0/0"]

  # Free Tier Configuration
  postgres_version  = "16.6"
  instance_class    = "db.t3.micro" # Free tier eligible
  allocated_storage = 20             # Free tier: up to 20GB

  # Database Configuration
  database_name   = "receiptly"
  master_username = var.db_username

  # Network
  publicly_accessible = true # Required for GitHub Actions and local dev

  # Backup (free tier: 1 day max)
  backup_retention_period = 1

  # For staging: no final snapshot or deletion protection
  skip_final_snapshot = true
  deletion_protection = false
}

# ==========================================
# EC2 Instance for Python OCR Service
# ==========================================
module "ocr_service" {
  source = "../../modules/ec2"

  project_name = var.project_name
  environment  = var.environment

  # Network Configuration - use existing VPC
  vpc_id    = module.vpc.vpc_id
  subnet_id = module.vpc.public_subnet_ids[0] # Deploy to first public subnet

  # Free Tier Configuration
  instance_type = "t3.micro" # Free tier eligible (or t2.micro)

  # Allow access from anywhere for staging (API calls, SSH if needed)
  allowed_cidr_blocks     = ["0.0.0.0/0"]
  ssh_allowed_cidr_blocks = [] # No SSH access for security

  aws_region = var.aws_region
}

# ==========================================
# S3 Bucket for Receipt Storage
# ==========================================
module "receipts_bucket" {
  source = "../../modules/s3"

  bucket_name        = "${var.project_name}-${var.environment}-receipts"
  versioning_enabled = true

  lifecycle_rules = [
    {
      id              = "archive-old-receipts"
      enabled         = true
      expiration_days = 365
    }
  ]

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "Receipt Image Storage"
  }
}

# ==========================================
# IAM User for S3 Access
# ==========================================

# Create IAM user for application S3 access
resource "aws_iam_user" "s3_user" {
  name = "${var.project_name}-${var.environment}-s3-user"
  path = "/applications/"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Create access key for the IAM user
resource "aws_iam_access_key" "s3_user" {
  user = aws_iam_user.s3_user.name
}

# Create policy for S3 bucket access
resource "aws_iam_user_policy" "s3_access" {
  name = "${var.project_name}-${var.environment}-s3-access"
  user = aws_iam_user.s3_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.receipts_bucket.bucket_arn,
          "${module.receipts_bucket.bucket_arn}/*"
        ]
      }
    ]
  })
}

# ==========================================
# Secrets Manager - All Credentials
# ==========================================

# Store all credentials in AWS Secrets Manager
module "secrets" {
  source = "../../modules/secrets"

  secrets = {
    "receiptly/database/credentials" = {
      description = "PostgreSQL database credentials for Receiptly ${var.environment}"
      value = jsonencode({
        username = module.database.db_username
        password = module.database.db_password
        host     = module.database.db_instance_address
        port     = module.database.db_instance_port
        database = module.database.db_name
        engine   = "postgres"
      })
    }
    "receiptly/s3/credentials" = {
      description = "S3 access credentials for Receiptly ${var.environment}"
      value = jsonencode({
        aws_access_key_id     = aws_iam_access_key.s3_user.id
        aws_secret_access_key = aws_iam_access_key.s3_user.secret
        bucket_name           = module.receipts_bucket.bucket_id
        region                = var.aws_region
      })
    }
  }

  recovery_window_days = 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

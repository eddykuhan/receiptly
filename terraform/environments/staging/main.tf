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

# Generate secure random password for database
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store all credentials in AWS Secrets Manager
module "secrets" {
  source = "../../modules/secrets"

  secrets = {
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

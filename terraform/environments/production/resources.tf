# Use shared ECR repository (created in staging)
data "aws_ecr_repository" "python_ocr" {
  name = "${var.project_name}-python-ocr"
}

# VPC and Networking
module "vpc" {
  source = "../../modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = "10.1.0.0/16"
  availability_zones = var.availability_zones

  public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  private_subnet_cidrs = ["10.1.11.0/24", "10.1.12.0/24", "10.1.13.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false # Multi-AZ for production

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

# S3 Bucket
module "s3" {
  source = "../../modules/s3"

  bucket_name        = "${var.project_name}-receipts-${var.environment}"
  versioning_enabled = true

  lifecycle_rules = [
    {
      id              = "archive-old-receipts"
      enabled         = true
      expiration_days = 365
    }
  ]

  tags = {
    Name = "${var.project_name}-receipts-${var.environment}"
  }
}

# Secrets Manager
module "secrets" {
  source = "../../modules/secrets"

  secrets = {
    "${var.project_name}/${var.environment}/azure-endpoint" = {
      description = "Azure Document Intelligence Endpoint"
      value       = var.azure_endpoint
    }
    "${var.project_name}/${var.environment}/azure-key" = {
      description = "Azure Document Intelligence Key"
      value       = var.azure_key
    }
    "${var.project_name}/${var.environment}/s3-bucket" = {
      description = "S3 Bucket Name"
      value       = module.s3.bucket_id
    }
  }

  recovery_window_days = 30

  tags = {
    Name = "${var.project_name}-${var.environment}-secrets"
  }
}

# IAM Roles
module "iam" {
  source = "../../modules/iam"

  project_name  = var.project_name
  environment   = var.environment
  s3_bucket_arn = module.s3.bucket_arn
  secrets_arns  = values(module.secrets.secret_arns)

  tags = {
    Name = "${var.project_name}-${var.environment}-iam"
  }
}

# ECS Cluster and Service
module "ecs" {
  source = "../../modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.ecs_security_group_id]

  ecr_repository_url = data.aws_ecr_repository.python_ocr.repository_url
  image_tag          = var.ecr_image_tag

  cpu           = "1024"
  memory        = "2048"
  desired_count = 2

  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  environment_variables = {
    ENVIRONMENT                = var.environment
    AWS_REGION                 = var.aws_region
    LOG_LEVEL                  = "WARNING"
    API_PREFIX                 = "/api/v1"
    ENABLE_IMAGE_PREPROCESSING = "true"
    ENABLE_PDF_SUPPORT         = "true"
  }

  secrets = {
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = module.secrets.secret_arns["${var.project_name}/${var.environment}/azure-endpoint"]
    AZURE_DOCUMENT_INTELLIGENCE_KEY      = module.secrets.secret_arns["${var.project_name}/${var.environment}/azure-key"]
    AWS_S3_BUCKET_NAME                   = module.secrets.secret_arns["${var.project_name}/${var.environment}/s3-bucket"]
  }

  assign_public_ip = false # Use private subnets with NAT

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs"
  }

  depends_on = [module.iam]
}

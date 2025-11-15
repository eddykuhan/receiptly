# ==========================================
# VPC Outputs
# ==========================================
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (used for RDS)"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# ==========================================
# Database Outputs
# ==========================================
output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.database.db_instance_endpoint
}

output "db_instance_address" {
  description = "RDS instance address (hostname)"
  value       = module.database.db_instance_address
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = module.database.db_instance_port
}

output "db_name" {
  description = "Database name"
  value       = module.database.db_name
}

# ==========================================
# EC2 Outputs
# ==========================================
output "app_instance_id" {
  description = "Application server EC2 instance ID"
  value       = module.ocr_service.instance_id
}

output "app_instance_public_ip" {
  description = "Application server EC2 instance public IP"
  value       = module.ocr_service.instance_public_ip
}

output "api_service_url" {
  description = ".NET API service URL"
  value       = module.ocr_service.api_service_url
}

output "ocr_service_url" {
  description = "Python OCR service URL"
  value       = module.ocr_service.ocr_service_url
}

# ==========================================
# S3 Bucket Outputs
# ==========================================
output "receipts_bucket_name" {
  description = "S3 bucket name for receipts"
  value       = module.receipts_bucket.bucket_id
}

output "receipts_bucket_arn" {
  description = "S3 bucket ARN for receipts"
  value       = module.receipts_bucket.bucket_arn
}

# ==========================================
# IAM User Outputs
# ==========================================
output "s3_user_name" {
  description = "IAM user name for S3 access"
  value       = aws_iam_user.s3_user.name
}

output "s3_user_arn" {
  description = "IAM user ARN"
  value       = aws_iam_user.s3_user.arn
}

# ==========================================
# Secrets Manager Outputs
# ==========================================
output "db_secret_name" {
  description = "Name of the Secrets Manager secret containing database credentials"
  value       = "receiptly/database/credentials"
}

output "s3_secret_name" {
  description = "Name of the Secrets Manager secret containing S3 credentials"
  value       = "receiptly/s3/credentials"
}

output "db_secret_retrieval_command" {
  description = "AWS CLI command to retrieve database credentials"
  value       = "aws secretsmanager get-secret-value --secret-id receiptly/database/credentials --query SecretString --output text | jq -r"
}

output "s3_secret_retrieval_command" {
  description = "AWS CLI command to retrieve S3 credentials"
  value       = "aws secretsmanager get-secret-value --secret-id receiptly/s3/credentials --query SecretString --output text | jq -r"
}

# ==========================================
# Setup Instructions
# ==========================================
output "setup_complete" {
  description = "Next steps after Terraform apply"
  value       = <<-EOT
    ✅ Terraform setup complete!
    
    �️  Database: ${module.database.db_instance_endpoint}
    �📦 S3 Bucket: ${module.receipts_bucket.bucket_id}
    🔐 Database Secret: receiptly/database/credentials
    🔐 S3 Secret: receiptly/s3/credentials
    
    Retrieve credentials:
    
    # Database credentials
    aws secretsmanager get-secret-value --secret-id receiptly/database/credentials --query SecretString --output text | jq
    
    # S3 credentials
    aws secretsmanager get-secret-value --secret-id receiptly/s3/credentials --query SecretString --output text | jq
    
    # Connection string for local testing:
    postgresql://$(aws secretsmanager get-secret-value --secret-id receiptly/database/credentials --query SecretString --output text | jq -r '.username'):$(aws secretsmanager get-secret-value --secret-id receiptly/database/credentials --query SecretString --output text | jq -r '.password')@${module.database.db_instance_address}:${module.database.db_instance_port}/${module.database.db_name}
  EOT
}

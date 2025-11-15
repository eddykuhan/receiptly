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
    
    📦 S3 Bucket: ${module.receipts_bucket.bucket_id}
    🔐 Database Secret: receiptly/database/credentials
    🔐 S3 Secret: receiptly/s3/credentials
    
    Retrieve credentials:
    
    # Database credentials
    aws secretsmanager get-secret-value --secret-id receiptly/database/credentials --query SecretString --output text | jq
    
    # S3 credentials
    aws secretsmanager get-secret-value --secret-id receiptly/s3/credentials --query SecretString --output text | jq
  EOT
}

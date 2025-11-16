output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.ocr_service.id
}

output "instance_public_ip" {
  description = "EC2 instance public IP (Elastic IP)"
  value       = aws_eip.ocr_service.public_ip
}

output "instance_private_ip" {
  description = "EC2 instance private IP"
  value       = aws_instance.ocr_service.private_ip
}

output "elastic_ip" {
  description = "Elastic IP address"
  value       = aws_eip.ocr_service.public_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.ocr_service.id
}

output "ocr_service_url" {
  description = "Python OCR service URL"
  value       = "http://${aws_eip.ocr_service.public_ip}:8000"
}

output "api_service_url" {
  description = ".NET API service URL"
  value       = "http://${aws_eip.ocr_service.public_ip}:5000"
}

output "instance_role_arn" {
  description = "IAM role ARN for EC2 instance"
  value       = aws_iam_role.ocr_instance.arn
}

output "cloudwatch_log_group_ocr" {
  description = "CloudWatch Log Group for Python OCR service"
  value       = aws_cloudwatch_log_group.ocr_service.name
}

output "cloudwatch_log_group_api" {
  description = "CloudWatch Log Group for .NET API service"
  value       = aws_cloudwatch_log_group.api_service.name
}

output "cloudwatch_log_group_system" {
  description = "CloudWatch Log Group for system logs"
  value       = aws_cloudwatch_log_group.system.name
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.ocr_service.id
}

output "instance_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_instance.ocr_service.public_ip
}

output "instance_private_ip" {
  description = "EC2 instance private IP"
  value       = aws_instance.ocr_service.private_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.ocr_service.id
}

output "ocr_service_url" {
  description = "Python OCR service URL"
  value       = "http://${aws_instance.ocr_service.public_ip}:8000"
}

output "instance_role_arn" {
  description = "IAM role ARN for EC2 instance"
  value       = aws_iam_role.ocr_instance.arn
}

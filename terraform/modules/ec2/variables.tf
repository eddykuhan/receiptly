variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instance (should be public subnet)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type (Free tier: t2.micro or t3.micro)"
  type        = string
  default     = "t3.micro"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the OCR service"
  type        = list(string)
  default     = ["0.0.0.0/0"] # For staging, adjust for production
}

variable "ssh_allowed_cidr_blocks" {
  description = "CIDR blocks allowed SSH access"
  type        = list(string)
  default     = [] # No SSH access by default
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 7 # Free tier includes 5GB ingestion
}

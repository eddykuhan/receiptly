variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "receiptly"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

# ==========================================
# Database Configuration
# ==========================================
variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "postgres"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling in GB"
  type        = number
  default     = 100
}

variable "db_storage_type" {
  description = "Storage type"
  type        = string
  default     = "gp3"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false # Set to true for high availability
}

# ==========================================
# HTTPS Configuration
# ==========================================
variable "enable_https" {
  description = "Enable HTTPS with Nginx and Let's Encrypt"
  type        = bool
  default     = false # Set to true to enable HTTPS
}

variable "domain_name" {
  description = "Domain name for SSL certificate (e.g., api.receiptly.com)"
  type        = string
  default     = "" # Set your domain name here
}

variable "letsencrypt_email" {
  description = "Email address for Let's Encrypt SSL certificate notifications"
  type        = string
  default     = "" # Set your email here
}

variable "db_backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot when destroying (set to false for production)"
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "Enable deletion protection (set to true for production)"
  type        = bool
  default     = false
}

# ==========================================
# Azure Configuration
# ==========================================
variable "azure_cv_endpoint" {
  description = "Azure Computer Vision endpoint URL"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_cv_api_key" {
  description = "Azure Computer Vision API key"
  type        = string
  sensitive   = true
  default     = ""
}

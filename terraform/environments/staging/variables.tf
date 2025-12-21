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
  default     = true # Set to true to enable HTTPS
}

variable "domain_name" {
  description = "Domain name for SSL certificate (e.g., api.receiptly.com)"
  type        = string
  default     = "cheap-sy.com"
}

variable "letsencrypt_email" {
  description = "Email address for Let's Encrypt SSL certificate notifications"
  type        = string
  default     = "eddykuhan92@gmail.com"
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

# ==========================================
# LLM Service Configuration
# ==========================================
variable "openai_api_key" {
  description = "OpenAI API key for LLM service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "groq_api_key" {
  description = "Groq API key for LLM service (alternative to OpenAI)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "use_groq" {
  description = "Use Groq instead of OpenAI for LLM service"
  type        = bool
  default     = false
}

variable "model_name" {
  description = "LLM model name to use"
  type        = string
  default     = "gpt-4o-mini"
}

# ==========================================
# Google Places API Configuration
# ==========================================
variable "google_places_api_key" {
  description = "Google Places API key for address autocomplete"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_places_enabled" {
  description = "Enable Google Places API autocomplete functionality"
  type        = bool
  default     = true
}

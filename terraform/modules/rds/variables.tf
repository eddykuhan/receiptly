variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the database security group"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the DB subnet group (must be in at least 2 AZs)"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the database"
  type        = list(string)
  default     = ["0.0.0.0/0"] # For staging, adjust for production
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16.3" # Latest stable version
}

variable "instance_class" {
  description = "RDS instance class (Free tier: db.t3.micro or db.t4g.micro)"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB (Free tier: up to 20GB)"
  type        = number
  default     = 20
}

variable "database_name" {
  description = "Initial database name"
  type        = string
  default     = "receiptly"
}

variable "master_username" {
  description = "Master username for the database"
  type        = string
  default     = "postgres"
}

variable "publicly_accessible" {
  description = "Whether the database is publicly accessible"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Backup retention period in days (Free tier: 0-7 days)"
  type        = number
  default     = 7
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion (true for dev/staging)"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

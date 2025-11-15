variable "bucket_name" {
  description = "Name of the S3 bucket for PWA hosting"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

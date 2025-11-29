# PWA Static Website Hosting
module "pwa" {
  source = "../../modules/s3-cloudfront"

  bucket_name = "receiptly-${var.environment}-pwa"
  environment = var.environment
}

output "pwa_website_url" {
  description = "PWA website URL"
  value       = module.pwa.website_url
}

output "pwa_bucket_name" {
  description = "S3 bucket for PWA files"
  value       = module.pwa.bucket_name
}

output "pwa_cloudfront_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = module.pwa.cloudfront_id
}

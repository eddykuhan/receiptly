output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.pwa.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.pwa.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.pwa.domain_name
}

output "cloudfront_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.pwa.id
}

output "website_url" {
  description = "PWA website URL"
  value       = "https://${aws_cloudfront_distribution.pwa.domain_name}"
}

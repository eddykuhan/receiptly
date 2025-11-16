# ==========================================
# CloudWatch Logs for EC2 Application Logs
# ==========================================

# CloudWatch Log Group for Python OCR Service
resource "aws_cloudwatch_log_group" "ocr_service" {
  name              = "/receiptly/${var.environment}/ocr"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-logs"
    Environment = var.environment
    Project     = var.project_name
    Service     = "python-ocr"
  }
}

# CloudWatch Log Group for .NET API Service
resource "aws_cloudwatch_log_group" "api_service" {
  name              = "/receiptly/${var.environment}/api"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-logs"
    Environment = var.environment
    Project     = var.project_name
    Service     = "dotnet-api"
  }
}

# CloudWatch Log Group for System Logs
resource "aws_cloudwatch_log_group" "system" {
  name              = "/receiptly/${var.environment}/system"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-system-logs"
    Environment = var.environment
    Project     = var.project_name
    Service     = "system"
  }
}

# IAM Policy for CloudWatch Logs
resource "aws_iam_role_policy" "cloudwatch_logs" {
  name_prefix = "cloudwatch-logs-"
  role        = aws_iam_role.ocr_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.ocr_service.arn}:*",
          "${aws_cloudwatch_log_group.api_service.arn}:*",
          "${aws_cloudwatch_log_group.system.arn}:*"
        ]
      }
    ]
  })
}

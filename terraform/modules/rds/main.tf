# ==========================================
# RDS PostgreSQL Instance (Free Tier)
# ==========================================

resource "random_password" "db_password" {
  length  = 16
  special = true
  # Exclude characters that might cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-${var.environment}-db-sg"
  description = "Security group for RDS PostgreSQL instance"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-${var.environment}-db"
  engine         = "postgres"
  engine_version = var.postgres_version

  # Free Tier Configuration
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_type      = "gp2" # Free tier uses gp2

  # Database Configuration
  db_name  = var.database_name
  username = var.master_username
  password = random_password.db_password.result

  # Network Configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = var.publicly_accessible

  # Backup Configuration (required for free tier)
  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00" # UTC
  maintenance_window      = "mon:04:00-mon:05:00"

  # Free Tier: Single-AZ only
  multi_az = false

  # Performance Insights not available in free tier
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  # Deletion Protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  deletion_protection       = var.deletion_protection

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-postgres"
    Environment = var.environment
    Project     = var.project_name
  }
}

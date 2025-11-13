resource "aws_secretsmanager_secret" "this" {
  for_each = var.secrets

  name                    = each.key
  description             = each.value.description
  recovery_window_in_days = var.recovery_window_days

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "this" {
  for_each = var.secrets

  secret_id     = aws_secretsmanager_secret.this[each.key].id
  secret_string = each.value.value
}

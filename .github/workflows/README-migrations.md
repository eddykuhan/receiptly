# Database Migration Deployment

This GitHub Actions workflow automatically deploys EF Core migrations to AWS RDS PostgreSQL.

## Prerequisites

### 1. AWS Secrets Manager Setup

Create a secret in AWS Secrets Manager with only username and password:

```bash
aws secretsmanager create-secret \
  --name receiptly/database/credentials \
  --description "Receiptly database username and password" \
  --secret-string '{
    "username": "postgres",
    "password": "your-secure-password"
  }'
```

The RDS endpoint will be stored in GitHub repository secrets instead.

### 2. IAM Role for GitHub Actions

Create an IAM role with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-southeast-1:*:secret:receiptly/database/credentials-*",
        "arn:aws:secretsmanager:ap-southeast-1:*:secret:receiptly/s3/credentials-*"
      ]
    }
  ]
}
```

Set up OIDC trust relationship:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:eddykuhan/receiptly:*"
        }
      }
    }
  ]
}
```

### 3. GitHub Repository Secrets

Add these secrets to your GitHub repository:

**Repository Secrets** (Settings → Secrets and variables → Actions):
- `AWS_ROLE_ARN`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsRole`
- `AWS_REGION`: `ap-southeast-1`
- `RDS_ENDPOINT`: Your RDS endpoint (e.g., `receiptly.xxxxxx.ap-southeast-1.rds.amazonaws.com`)

**Environment Secrets** for `staging`:
- `DB_SECRET_NAME`: `receiptly/database/credentials`

**Environment Secrets** for `production`:
- `DB_SECRET_NAME`: `receiptly/database/credentials` (or use separate credentials for production)

### 4. Create GitHub Environments

1. Go to repository Settings → Environments
2. Create two environments:
   - `staging` (optional: no protection rules)
   - `production` (recommended: add protection rules)

For production environment, add:
- Required reviewers
- Wait timer (optional)
- Deployment branches: only `main`

## Usage

### Automatic Deployment

Migrations are automatically deployed to staging when:
- Changes are pushed to `main` branch
- Migration files are modified in `dotnet-api/src/Receiptly.Infrastructure/Data/Migrations/`

### Manual Deployment

1. Go to Actions → Deploy Database Migrations
2. Click "Run workflow"
3. Select environment (staging or production)
4. Click "Run workflow"

## Workflow Features

✅ **Idempotent Migrations**: Safe to run multiple times
✅ **SQL Script Preview**: Shows migration script before applying
✅ **Verification**: Checks applied migrations after deployment
✅ **Secure**: Uses AWS Secrets Manager for credentials
✅ **Environment-specific**: Separate staging/production deployments
✅ **Rollback Support**: Optional rollback on production failures

## Local Testing

Test migrations locally before deploying:

```bash
# Export credentials from AWS Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --secret-id receiptly/database/credentials \
  --query SecretString \
  --output text)

DB_USER=$(echo $SECRET_JSON | jq -r '.username')
DB_PASSWORD=$(echo $SECRET_JSON | jq -r '.password')

# Set your RDS endpoint
RDS_ENDPOINT="receiptly.xxxxxx.ap-southeast-1.rds.amazonaws.com"

# Build connection string
export CONNECTION_STRING="Host=${RDS_ENDPOINT};Port=5432;Database=receiptly_db;Username=${DB_USER};Password=${DB_PASSWORD};SSL Mode=Require"

# Apply migrations
cd dotnet-api
dotnet ef database update \
  --project src/Receiptly.Infrastructure/Receiptly.Infrastructure.csproj \
  --startup-project src/Receiptly.API/Receiptly.API.csproj \
  --connection "$CONNECTION_STRING"
```

## Troubleshooting

### Migration fails with SSL error
Add `Trust Server Certificate=true` to connection string or configure RDS SSL certificate.

### Permission denied
Verify IAM role has `secretsmanager:GetSecretValue` permission for the secret.

### Migration already applied
This is normal - migrations are idempotent. Check `__EFMigrationsHistory` table.

## Rollback

To rollback to a previous migration:

```bash
# List all migrations
dotnet ef migrations list \
  --project src/Receiptly.Infrastructure/Receiptly.Infrastructure.csproj \
  --startup-project src/Receiptly.API/Receiptly.API.csproj

# Rollback to specific migration
dotnet ef database update <migration-name> \
  --project src/Receiptly.Infrastructure/Receiptly.Infrastructure.csproj \
  --startup-project src/Receiptly.API/Receiptly.API.csproj \
  --connection "$CONNECTION_STRING"
```

## Security Best Practices

1. ✅ Never commit database credentials to git
2. ✅ Use AWS Secrets Manager for all credentials
3. ✅ Enable SSL for RDS connections
4. ✅ Use IAM roles instead of access keys
5. ✅ Require approvals for production deployments
6. ✅ Backup database before migrations
7. ✅ Test in staging before production

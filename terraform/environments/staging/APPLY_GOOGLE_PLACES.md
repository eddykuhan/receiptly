# Apply Google Places API Secret to AWS

## Quick Start

### 1. Set Your API Key

Create or update `terraform.tfvars`:

```bash
cd terraform/environments/staging

# If terraform.tfvars doesn't exist, copy from example
cp terraform.tfvars.example terraform.tfvars

# Edit the file and add your Google Places API key
# google_places_api_key = "your-api-key-here"
```

**Or use environment variable:**

```bash
export TF_VAR_google_places_api_key="your-api-key-here"
export TF_VAR_google_places_enabled=true
```

### 2. Preview Changes

```bash
cd terraform/environments/staging
terraform plan
```

You should see:
```
# module.secrets.aws_secretsmanager_secret_version.this["receiptly/google/credentials"] will be created
```

### 3. Apply Changes

```bash
terraform apply
```

Type `yes` when prompted.

## What Gets Created

**Secret Name:** `receiptly/google/credentials`

**Secret Value:**
```json
{
  "api_key": "your-google-places-api-key",
  "enabled": true
}
```

**AWS Region:** `ap-southeast-1` (Singapore)

## Verify Creation

### Using AWS CLI

```bash
aws secretsmanager get-secret-value \
  --secret-id receiptly/google/credentials \
  --region ap-southeast-1 \
  --query SecretString \
  --output text | jq .
```

### Using AWS Console

1. Go to AWS Secrets Manager: https://ap-southeast-1.console.aws.amazon.com/secretsmanager/
2. Find secret: `receiptly/google/credentials`
3. Click "Retrieve secret value"

## Disable Google Places (Without Deleting Secret)

If you want to disable the feature without removing the secret:

```bash
# Set enabled to false
export TF_VAR_google_places_enabled=false
terraform apply
```

The secret will update to:
```json
{
  "api_key": "your-api-key",
  "enabled": false
}
```

The .NET API will check this flag and return empty suggestions when disabled.

## Update API Key

To rotate or update the API key:

1. Update `terraform.tfvars` or environment variable
2. Run `terraform apply`
3. Restart .NET API to pick up new secret

No code changes required! 🎉

## Security Best Practices

✅ **Never commit terraform.tfvars** - Contains sensitive keys  
✅ **Use .gitignore** - Already configured to exclude `*.tfvars`  
✅ **Use environment variables** - For CI/CD pipelines  
✅ **Enable secret recovery** - 7-day recovery window by default  
✅ **Restrict IAM access** - Only EC2 instance role can read secrets

## Cost

- **Secrets Manager**: $0.40/month per secret
- **Google Places API**: ~$0.017 per autocomplete request
  - Free tier: $200 credit/month (≈11,700 requests)

## Troubleshooting

**Error: "Secret already exists"**
```bash
# Delete existing secret (if created manually)
aws secretsmanager delete-secret \
  --secret-id receiptly/google/credentials \
  --force-delete-without-recovery \
  --region ap-southeast-1

# Then run terraform apply again
terraform apply
```

**Error: "Invalid API key"**
- Verify API key in Google Cloud Console
- Check Places API (New) is enabled
- Review API key restrictions

**API returns empty suggestions:**
- Check `enabled: true` in secret
- Verify .NET API has IAM permissions to read secret
- Check .NET API logs for secret retrieval errors

## Related Files

- [Main Config](main.tf) - Secret definition (line 290)
- [Variables](variables.tf) - Variable declarations (line 151)
- [Example Config](terraform.tfvars.example) - Example values
- [Setup Guide](../../../docs/GOOGLE_PLACES_API_SETUP.md) - Complete integration docs

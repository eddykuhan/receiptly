# Terraform: Google Places API Secret - Quick Reference

## Summary of Changes

Added Google Places API secret management to Terraform infrastructure.

### Files Modified

1. **[terraform/environments/staging/variables.tf](variables.tf)**
   - Added `google_places_api_key` variable (sensitive)
   - Added `google_places_enabled` variable (boolean)

2. **[terraform/environments/staging/main.tf](main.tf)**
   - Added `receiptly/google/credentials` secret to `module.secrets`
   - Secret contains: `api_key` and `enabled` fields

3. **[terraform/environments/staging/terraform.tfvars.example](terraform.tfvars.example)**
   - Added example configuration with comments
   - Links to Google Cloud Console for API key setup

### Files Created

4. **[APPLY_GOOGLE_PLACES.md](APPLY_GOOGLE_PLACES.md)**
   - Step-by-step guide to apply changes
   - Troubleshooting section
   - Cost information

5. **[docs/GOOGLE_PLACES_API_SETUP.md](../../../docs/GOOGLE_PLACES_API_SETUP.md)** (Updated)
   - Added Terraform as recommended option
   - Links to staging environment guide

## How to Apply

### Quick Steps

```bash
cd terraform/environments/staging

# 1. Set your API key
export TF_VAR_google_places_api_key="AIza..."
export TF_VAR_google_places_enabled=true

# 2. Preview changes
terraform plan

# 3. Apply
terraform apply
```

### What Gets Created

**AWS Secret:**
- Name: `receiptly/google/credentials`
- Region: `ap-southeast-1`
- Value:
  ```json
  {
    "api_key": "your-key-here",
    "enabled": true
  }
  ```

### Verify

```bash
aws secretsmanager get-secret-value \
  --secret-id receiptly/google/credentials \
  --region ap-southeast-1 \
  --query SecretString \
  --output text | jq .
```

## Integration Flow

```
Terraform Apply
    ↓
AWS Secrets Manager
    ↓
.NET API (reads on startup)
    ↓
GooglePlacesClient
    ↓
PlacesController (/api/places/autocomplete)
    ↓
Angular FeedbackModalComponent
```

## Configuration Options

### Enable/Disable Feature

```bash
# Disable without deleting secret
export TF_VAR_google_places_enabled=false
terraform apply
```

### Update API Key

```bash
# Just update the variable and apply
export TF_VAR_google_places_api_key="new-key"
terraform apply

# Restart .NET API to pick up changes
```

## Security Features

✅ API key stored in AWS Secrets Manager (encrypted at rest)  
✅ Variable marked as `sensitive` (hidden in logs)  
✅ 7-day recovery window for accidental deletions  
✅ IAM-based access control  
✅ Never committed to git (.tfvars ignored)

## Cost

- **AWS Secrets Manager**: $0.40/month per secret
- **Terraform State**: Stored in S3 (negligible cost)
- **Google Places API**: ~$0.017 per request, $200/month free tier

## See Also

- [Full Setup Guide](APPLY_GOOGLE_PLACES.md) - Detailed instructions
- [API Documentation](../../../docs/GOOGLE_PLACES_API_SETUP.md) - Complete integration docs
- [Backend Implementation](../../../dotnet-api/src/Receiptly.Infrastructure/Services/GooglePlacesClient.cs)
- [Frontend Implementation](../../../angular-app/src/app/shared/components/feedback-modal.component.ts)

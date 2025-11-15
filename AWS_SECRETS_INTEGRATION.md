# AWS Secrets Manager Integration Guide

## Overview

The .NET API now retrieves S3 credentials from AWS Secrets Manager on application startup instead of hardcoding them in configuration files. This provides better security and centralized credential management.

## Architecture

```
Application Startup
    ↓
Retrieve S3 credentials from Secrets Manager
(receiptly/s3/credentials)
    ↓
Deserialize JSON → S3SecretsConfig
    ↓
Register S3SecretsConfig as singleton
    ↓
Inject into S3StorageService
    ↓
S3StorageService creates authenticated S3 client
```

## Implementation Details

### 1. Secret Structure

The secret `receiptly/s3/credentials` contains:

```json
{
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "bucket_name": "receiptly-staging-receipts",
  "region": "ap-southeast-1"
}
```

### 2. Configuration Class

**File**: `Receiptly.Infrastructure/Configuration/S3SecretsConfig.cs`

Maps the JSON structure from Secrets Manager with JSON property name attributes to match the snake_case format.

### 3. Startup Configuration

**File**: `Receiptly.API/Program.cs`

On application startup:

1. **Retrieve Secret**: Uses `AmazonSecretsManagerClient` to fetch the secret
2. **Deserialize**: Converts JSON to `S3SecretsConfig` object
3. **Register**: Adds the config as a singleton for dependency injection
4. **Fallback**: If Secrets Manager fails (e.g., local development), falls back to appsettings.json/user secrets

### 4. S3 Service Updates

**File**: `Receiptly.Infrastructure/Services/S3StorageService.cs`

- **Old**: Constructor accepted `IConfiguration` and read AWS credentials directly
- **New**: Constructor accepts `S3SecretsConfig` injected from DI container
- **Benefit**: Decoupled from configuration source, testable, secure

## Configuration

### Production (AWS)

No configuration needed! The application automatically:
1. Uses IAM permissions of the EC2/ECS/Lambda instance to access Secrets Manager
2. Retrieves S3 credentials on startup
3. Uses those credentials for all S3 operations

### Local Development

Two options:

#### Option A: Use AWS Secrets Manager (Recommended)

Ensure you have AWS credentials configured:

```bash
# Configure AWS CLI
aws configure

# Test secret retrieval
aws secretsmanager get-secret-value \
  --secret-id receiptly/s3/credentials \
  --query SecretString \
  --output text | jq
```

The application will automatically retrieve credentials from Secrets Manager.

#### Option B: Fallback to User Secrets

If Secrets Manager is unavailable, configure user secrets:

```bash
cd dotnet-api/src/Receiptly.API

dotnet user-secrets set "AWS:AccessKeyId" "your-key"
dotnet user-secrets set "AWS:SecretAccessKey" "your-secret"
dotnet user-secrets set "AWS:S3BucketName" "your-bucket"
dotnet user-secrets set "AWS:Region" "ap-southeast-1"
```

### Override Secret ID (Optional)

To use a different secret:

```json
{
  "AWS": {
    "S3SecretId": "custom/secret/path",
    "Region": "ap-southeast-1"
  }
}
```

## Error Handling

The implementation includes comprehensive error handling:

1. **Secrets Manager Unavailable**: Falls back to configuration with detailed logging
2. **Deserialization Failure**: Throws `InvalidOperationException` with clear message
3. **Missing Credentials**: Throws `InvalidOperationException` for missing required fields

## Security Benefits

✅ **No Hardcoded Credentials**: Credentials never stored in code or config files  
✅ **Centralized Management**: Update credentials in one place (Secrets Manager)  
✅ **Automatic Rotation**: Can enable auto-rotation in Secrets Manager  
✅ **IAM Permissions**: Uses IAM roles instead of access keys in production  
✅ **Audit Trail**: CloudTrail logs all secret access  

## Testing

### Verify Secrets Manager Integration

1. **Start the application** with AWS credentials configured:
   ```bash
   cd dotnet-api/src/Receiptly.API
   dotnet run
   ```

2. **Check logs** for successful secret retrieval:
   ```
   [INF] Retrieving S3 credentials from Secrets Manager: receiptly/s3/credentials
   [INF] Successfully retrieved S3 credentials for bucket: receiptly-staging-receipts
   [INF] S3StorageService initialized with bucket: receiptly-staging-receipts in region: ap-southeast-1
   ```

3. **Test S3 operations** by uploading a receipt through the API

### Verify Fallback Behavior

1. **Disconnect from AWS** (or remove credentials)
2. **Configure user secrets** as shown above
3. **Start the application** and verify it falls back:
   ```
   [ERR] Failed to retrieve S3 credentials from Secrets Manager. Falling back to configuration.
   [INF] S3StorageService initialized with bucket: your-bucket in region: ap-southeast-1
   ```

## Deployment Checklist

- [x] Install `AWSSDK.SecretsManager` NuGet package
- [x] Create `S3SecretsConfig` configuration class
- [x] Update `Program.cs` to retrieve secret on startup
- [x] Refactor `S3StorageService` to use injected config
- [x] Add error handling and logging
- [x] Add fallback to configuration for local development
- [ ] Update CI/CD to ensure IAM permissions for Secrets Manager
- [ ] Test in staging environment
- [ ] Document for team

## IAM Permissions Required

The application or EC2/ECS/Lambda instance needs:

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
        "arn:aws:secretsmanager:ap-southeast-1:*:secret:receiptly/s3/credentials-*"
      ]
    }
  ]
}
```

## Next Steps

1. **Deploy to Staging**: Test Secrets Manager integration in staging environment
2. **Enable Auto-Rotation**: Set up automatic rotation for S3 access keys
3. **Add Database Secrets**: Apply same pattern for database connection strings
4. **Production Deployment**: Roll out to production with proper IAM roles
5. **Remove User Secrets**: Clean up local user secrets once Secrets Manager is working

## Troubleshooting

### "Unable to retrieve credentials from Secrets Manager"

- **Check AWS credentials**: `aws sts get-caller-identity`
- **Verify secret exists**: `aws secretsmanager get-secret-value --secret-id receiptly/s3/credentials`
- **Check IAM permissions**: Ensure the IAM role/user has `secretsmanager:GetSecretValue` permission

### "Failed to deserialize S3 credentials"

- **Verify JSON structure**: Check the secret contains all required fields (aws_access_key_id, aws_secret_access_key, bucket_name, region)
- **Check JSON format**: Ensure valid JSON with proper snake_case field names

### "AWS:AccessKeyId not configured" (Fallback)

- Configure user secrets as shown in the Local Development section
- Or ensure AWS credentials are configured for Secrets Manager access

## Related Documentation

- [Terraform Staging Setup](terraform/environments/staging/README.md)
- [AWS Deployment Guide](DEPLOYMENT.md)
- [Architecture Migration](ARCHITECTURE_MIGRATION.md)

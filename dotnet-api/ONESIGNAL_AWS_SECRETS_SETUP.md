# OneSignal AWS Secrets Manager Setup

## Create Secret via AWS CLI

```bash
# Create the OneSignal credentials secret
aws secretsmanager create-secret \
    --name receiptly/onesignal/credentials \
    --description "OneSignal push notification credentials for Receiptly" \
    --secret-string '{
      "app_id": "7744f1a9-f1ba-4775-b239-ae324842f619",
      "rest_api_key": "YOUR_ONESIGNAL_REST_API_KEY",
      "safari_web_id": ""
    }' \
    --region us-east-1

# Verify the secret
aws secretsmanager get-secret-value \
    --secret-id receiptly/onesignal/credentials \
    --region us-east-1
```

## Update Existing Secret

```bash
aws secretsmanager update-secret \
    --secret-id receiptly/onesignal/credentials \
    --secret-string '{
      "app_id": "7744f1a9-f1ba-4775-b239-ae324842f619",
      "rest_api_key": "YOUR_NEW_REST_API_KEY",
      "safari_web_id": ""
    }' \
    --region us-east-1
```

## Get OneSignal REST API Key

1. Go to [OneSignal Dashboard](https://onesignal.com)
2. Select your app
3. Settings → Keys & IDs
4. Copy "REST API Key"

## Required IAM Permissions

Add this policy to your EC2/ECS instance role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:receiptly/onesignal/credentials-*"
      ]
    }
  ]
}
```

## Local Development Fallback

For local development, create `appsettings.Development.json` or user secrets:

```json
{
  "OneSignal": {
    "AppId": "7744f1a9-f1ba-4775-b239-ae324842f619",
    "RestApiKey": "YOUR_REST_API_KEY"
  }
}
```

Or use .NET user secrets:

```bash
cd /Users/kuhan/Projects/receiptly/dotnet-api/src/Receiptly.API

dotnet user-secrets set "OneSignal:AppId" "7744f1a9-f1ba-4775-b239-ae324842f619"
dotnet user-secrets set "OneSignal:RestApiKey" "YOUR_REST_API_KEY"
```

## How It Works

1. **Production**: API retrieves credentials from AWS Secrets Manager on startup
2. **Development**: Falls back to `appsettings.json` or user secrets if Secrets Manager unavailable
3. **Configuration Override**: Secrets Manager values override appsettings values
4. **Logging**: Check logs for "Successfully retrieved OneSignal credentials" or fallback warning

## Deployment Steps

1. Create secret in AWS Secrets Manager (use command above)
2. Ensure EC2/ECS instance has IAM permissions
3. Set `AWS:Region` and `AWS:OneSignalSecretId` in appsettings (optional, defaults provided)
4. Deploy application
5. Verify logs show successful secret retrieval

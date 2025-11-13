# IAM Permission Issue - Solutions

## Problem
Your IAM user `cli` doesn't have permission to create DynamoDB tables.

## Solutions (Choose ONE)

### ✅ Solution 1: Use CloudFormation (Recommended - Easiest)

CloudFormation may work with your current permissions:

```bash
cd terraform
./setup-backend-cfn.sh
```

**Why this might work:** CloudFormation uses different API calls and your account might have `cloudformation:*` permissions.

---

### ✅ Solution 2: Add Required IAM Permissions

If you have admin access or can ask an admin:

```bash
cd terraform
./add-iam-permissions.sh
```

This will create and attach a policy with all required permissions.

**Manual alternative** (if script fails):

1. Go to AWS Console → IAM → Policies
2. Click **Create Policy**
3. Click **JSON** tab
4. Copy the contents of `required-iam-policy.json`
5. Click **Next**, name it `ReceiptlyTerraformPolicy`
6. Click **Create Policy**
7. Go to IAM → Users → `cli`
8. Click **Add permissions** → **Attach policies directly**
9. Search for `ReceiptlyTerraformPolicy` and attach it

Then retry:
```bash
./setup-backend.sh
```

---

### ✅ Solution 3: Use AWS Console (Manual)

Create resources manually in AWS Console:

#### Create S3 Bucket
1. Go to AWS Console → S3
2. Click **Create bucket**
3. Bucket name: `receiptly-terraform-state`
4. Region: `ap-southeast-1`
5. Enable **Bucket Versioning**
6. Enable **Default encryption** (SSE-S3)
7. **Block all public access** ✓
8. Click **Create bucket**

#### Create DynamoDB Table
1. Go to AWS Console → DynamoDB
2. Click **Create table**
3. Table name: `receiptly-terraform-locks`
4. Partition key: `LockID` (String)
5. Table settings: **On-demand**
6. Click **Create table**

Then skip to deploying Terraform:
```bash
cd environments/staging
terraform init
```

---

### ✅ Solution 4: Ask Your Administrator

Send this to your AWS administrator:

```
Hi,

I need permissions to set up Terraform infrastructure for the Receiptly project.

Please attach the policy from this file to my IAM user (cli):
terraform/required-iam-policy.json

Or run this command:
aws iam attach-user-policy \
  --user-name cli \
  --policy-arn arn:aws:iam::947685297250:policy/ReceiptlyTerraformPolicy

(After creating the policy from required-iam-policy.json)

Thank you!
```

---

## Quick Comparison

| Solution | Difficulty | Requires Admin | Time |
|----------|-----------|----------------|------|
| 1. CloudFormation | Easy | Maybe not | 2 min |
| 2. Add IAM permissions | Medium | Yes | 5 min |
| 3. AWS Console | Easy | Maybe not | 10 min |
| 4. Ask admin | Easy | Yes | Varies |

---

## Testing Your Permissions

Check what permissions you currently have:

```bash
# Test S3 access
aws s3 ls

# Test DynamoDB access
aws dynamodb list-tables --region ap-southeast-1

# Test CloudFormation access
aws cloudformation list-stacks --region ap-southeast-1
```

---

## After Permissions Are Fixed

Once you have the right permissions, continue with:

```bash
cd terraform

# If using CloudFormation:
./setup-backend-cfn.sh

# OR if permissions added:
./setup-backend.sh

# Then proceed to deploy:
cd environments/staging
export TF_VAR_azure_endpoint="your-azure-endpoint"
export TF_VAR_azure_key="your-azure-key"
terraform init
terraform plan
terraform apply
```

---

## Need Help?

Check the [CHECKLIST.md](CHECKLIST.md) for the complete deployment flow.

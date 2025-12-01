# Deployment Checklist - ECR Migration & LLM Service

## Pre-Deployment Checklist

### 1. AWS Credentials ✓
- [ ] AWS CLI configured locally
- [ ] Terraform has access to AWS (via AWS_PROFILE or credentials)
- [ ] GitHub Actions has AWS role configured (AWS_ROLE_ARN secret)

### 2. GitHub Secrets
- [ ] Add `OPENAI_API_KEY` (if using OpenAI)
- [ ] Add `GROQ_API_KEY` (if using Groq)
- [ ] Optionally set `USE_GROQ=true` (default: false)
- [ ] Optionally set `MODEL_NAME` (default: gpt-4o-mini)

### 3. Code Review
- [ ] Review Terraform changes in `terraform/environments/staging/main.tf`
- [ ] Review GitHub Actions changes in `.github/workflows/deploy-combined.yml`
- [ ] Review EC2 module changes in `terraform/modules/ec2/main.tf`

## Deployment Steps

### Step 1: Apply Terraform Changes

```bash
cd terraform/environments/staging

# Initialize (if needed)
terraform init

# Review changes
terraform plan

# Expected changes:
# + 3 ECR repositories (dotnet-api, python-ocr, llm-service)
# ~ Update secrets (add ECR info, LLM URL)
# ~ Update EC2 security group (add port 8500)
# ~ Update EC2 user data (add LLM service)

# Apply changes
terraform apply
```

**Verification:**
- [ ] ECR repositories created
- [ ] Secrets updated in AWS Secrets Manager
- [ ] EC2 security group has port 8500
- [ ] Note down ECR repository URLs from output

### Step 2: Update EC2 Instance (if already running)

The EC2 user data only runs on first boot. If you have an existing instance, you need to manually update it:

```bash
# Option 1: Terminate and recreate (recommended for clean state)
terraform destroy -target=aws_instance.ocr_service
terraform apply

# Option 2: Manual update (via SSM Session Manager)
aws ssm start-session --target <instance-id>

# Then run these commands:
sudo mkdir -p /opt/receiptly/llm

# Create systemd service for LLM
sudo tee /etc/systemd/system/receiptly-llm.service > /dev/null <<'EOF'
[Unit]
Description=Receiptly LLM Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/receiptly/llm
ExecStartPre=-/usr/bin/docker stop receiptly-llm
ExecStartPre=-/usr/bin/docker rm receiptly-llm
ExecStartPre=/usr/bin/bash -c 'eval $(aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-southeast-1.amazonaws.com)'
ExecStart=/usr/bin/bash -c 'docker run --name receiptly-llm --network receiptly_default -p 8500:8500 --log-driver=awslogs --log-opt awslogs-region=ap-southeast-1 --log-opt awslogs-group=/receiptly/staging/llm --log-opt awslogs-stream=receiptly-llm --env-file /opt/receiptly/llm/.env $(aws secretsmanager get-secret-value --secret-id receiptly/ecr/repositories --query SecretString --output text | jq -r .llm_service_repository):latest'
ExecStop=/usr/bin/docker stop receiptly-llm
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Update existing services for ECR
# ... (similar updates for api and ocr services)

sudo systemctl daemon-reload
```

**Verification:**
- [ ] `/opt/receiptly/llm` directory exists
- [ ] `receiptly-llm.service` file created
- [ ] Systemd services updated

### Step 3: Commit and Push Changes

```bash
# From project root
git add .
git commit -m "feat: migrate to ECR and add LLM service deployment

- Add ECR repositories for all 3 services
- Update GitHub Actions to push images to ECR
- Add LLM service to EC2 deployment
- Update secrets with ECR info and LLM service URL
- Configure systemd services to use ECR images"

git push origin feature/ocr
```

**Verification:**
- [ ] All files committed
- [ ] Pushed to remote
- [ ] GitHub Actions workflow triggered

### Step 4: Monitor GitHub Actions Deployment

Watch the workflow: https://github.com/eddykuhan/receiptly/actions

**Expected steps:**
1. ✓ Checkout code
2. ✓ Configure AWS credentials
3. ✓ Get EC2 instance details
4. ✓ Get credentials from Secrets Manager
5. ✓ Free disk space
6. ✓ Login to Amazon ECR
7. ✓ Build and Push .NET API to ECR
8. ✓ Build and Push Python OCR to ECR
9. ✓ Build and Push LLM Service to ECR
10. ✓ Create environment files
11. ✓ Deploy to EC2 using SSM
12. ✓ Health Check (LLM → OCR → API)
13. ✓ Deployment Summary

**Verification:**
- [ ] All steps complete successfully
- [ ] Images pushed to ECR (check AWS Console)
- [ ] Services deployed to EC2
- [ ] Health checks pass

### Step 5: Verify Services

#### Check ECR Repositories

```bash
# List images in each repository
aws ecr list-images --repository-name receiptly-staging-dotnet-api
aws ecr list-images --repository-name receiptly-staging-python-ocr
aws ecr list-images --repository-name receiptly-staging-llm-service
```

**Verification:**
- [ ] Each repository has at least 2 tags (latest + commit SHA)
- [ ] Images are marked as scanned

#### Check EC2 Services

```bash
# Get EC2 public IP
EC2_IP=$(terraform output -raw app_instance_public_ip)

# Check service status via SSM
aws ssm start-session --target $(terraform output -raw app_instance_id)

# Inside EC2
sudo systemctl status receiptly-llm
sudo systemctl status receiptly-ocr
sudo systemctl status receiptly-api
docker ps
```

**Verification:**
- [ ] All 3 services running
- [ ] Containers using ECR images
- [ ] No restart loops

#### Test Endpoints

```bash
# Get EC2 IP from Terraform output
EC2_IP=$(cd terraform/environments/staging && terraform output -raw app_instance_public_ip)

# Test LLM Service
curl http://$EC2_IP:8500/docs

# Test OCR Service
curl http://$EC2_IP:8000/health

# Test API
curl http://$EC2_IP:5000/health

# Test LLM functionality
curl -X POST http://$EC2_IP:8500/canonicalize_item \
  -H "Content-Type: application/json" \
  -d '{"raw_item": "Farm Fresh Pure Fresh 1L"}'

# Expected: {"canonical_name": "Farm Fresh Fresh Milk 1L"}
```

**Verification:**
- [ ] LLM service docs accessible
- [ ] OCR health check returns OK
- [ ] API health check returns OK
- [ ] LLM canonicalization works

### Step 6: Check CloudWatch Logs

```bash
# View logs for each service
aws logs tail /receiptly/staging/llm --follow
aws logs tail /receiptly/staging/ocr --follow
aws logs tail /receiptly/staging/api --follow
```

**Verification:**
- [ ] No errors in logs
- [ ] Services starting successfully
- [ ] LLM service processing requests

## Post-Deployment Checklist

### Functionality Tests
- [ ] Upload a receipt via API
- [ ] Verify OCR processing works
- [ ] Check items are canonicalized by LLM
- [ ] Verify location selection works

### Performance
- [ ] Response times acceptable (<5s for OCR)
- [ ] LLM calls completing (<30s timeout)
- [ ] No memory issues

### Monitoring
- [ ] CloudWatch Logs working
- [ ] Docker logs visible
- [ ] No crash loops

### Cost Tracking
- [ ] Check ECR storage usage
- [ ] Monitor LLM API costs (OpenAI/Groq dashboard)
- [ ] Review CloudWatch costs

## Rollback Plan

If deployment fails:

### Option 1: Rollback Terraform

```bash
cd terraform/environments/staging
terraform plan -destroy -target=module.ecr_llm_service
terraform destroy -target=module.ecr_llm_service
```

### Option 2: Rollback GitHub Actions

```bash
git revert HEAD
git push origin feature/ocr
```

### Option 3: Manual Service Restart

```bash
# SSH to EC2
aws ssm start-session --target <instance-id>

# Stop LLM service
sudo systemctl stop receiptly-llm

# Check other services
sudo systemctl status receiptly-ocr
sudo systemctl status receiptly-api
```

## Common Issues

### Issue: ECR authentication failed
**Solution:**
```bash
# Manually login to ECR
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com
```

### Issue: LLM service not starting
**Check:**
1. `.env` file exists: `ls -la /opt/receiptly/llm/.env`
2. API key is valid
3. Check logs: `journalctl -u receiptly-llm -f`

### Issue: OCR can't connect to LLM
**Check:**
1. LLM service is running: `docker ps | grep llm`
2. Network exists: `docker network ls | grep receiptly`
3. Environment variable: `cat /opt/receiptly/ocr/.env | grep LLM`

### Issue: GitHub Actions timeout
**Solution:**
- Increase timeout in workflow file
- Use smaller Docker images
- Check GitHub runner disk space

## Success Criteria

✅ All checks passed:
- [ ] Terraform apply successful
- [ ] ECR repositories created
- [ ] GitHub Actions deployment successful
- [ ] All 3 services running on EC2
- [ ] Health checks passing
- [ ] LLM functionality working
- [ ] OCR processing receipts
- [ ] API returning data
- [ ] CloudWatch logs flowing
- [ ] No errors in logs

## Next Steps

After successful deployment:

1. **Test thoroughly** - Run integration tests
2. **Monitor costs** - Check ECR and LLM API usage
3. **Set up alerts** - CloudWatch alarms for errors
4. **Document** - Update README with new URLs
5. **Clean up** - Remove old S3 deployment artifacts (if desired)
6. **Production** - Replicate for production environment

## Support

If you encounter issues:
- Check `ECR_MIGRATION_SUMMARY.md` for architecture overview
- Check `GITHUB_SECRETS_SETUP.md` for API key setup
- Review CloudWatch logs
- Check GitHub Actions workflow logs
- Verify AWS Secrets Manager values

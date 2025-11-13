# Terraform Deployment Checklist

Use this checklist to ensure proper setup and deployment of the Receiptly infrastructure.

## ✅ Pre-Deployment Checklist

### AWS Setup
- [ ] AWS account created and accessible
- [ ] AWS CLI installed (`aws --version`)
- [ ] AWS credentials configured (`aws configure`)
- [ ] Verify account ID: `aws sts get-caller-identity`

### Terraform Setup
- [ ] Terraform installed (`terraform --version`)
- [ ] Terraform >= 1.0 confirmed

### Azure Setup
- [ ] Azure Document Intelligence resource created
- [ ] Azure endpoint URL obtained
- [ ] Azure API key obtained

### GitHub Setup
- [ ] Repository forked/cloned
- [ ] GitHub Secrets added:
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
  - [ ] `AZURE_ENDPOINT`
  - [ ] `AZURE_KEY`

## ✅ First-Time Deployment

### Step 1: Create Backend Resources

**Option A: Using CloudFormation (Recommended)**
```bash
cd terraform
./setup-backend-cfn.sh
```

**Option B: Using AWS CLI directly**
```bash
cd terraform
./setup-backend.sh
```

**If you get permission errors**, see [PERMISSION-FIX.md](PERMISSION-FIX.md) for solutions.

Verify:
- [ ] S3 bucket `receiptly-terraform-state` created
- [ ] DynamoDB table `receiptly-terraform-locks` created
- [ ] No errors in script output

### Step 2: Set Local Credentials
```bash
export TF_VAR_azure_endpoint="https://your-endpoint.cognitiveservices.azure.com/"
export TF_VAR_azure_key="your-azure-key"
```

Verify:
- [ ] Environment variables set (`echo $TF_VAR_azure_endpoint`)

### Step 3: Deploy Staging
```bash
cd terraform/environments/staging
terraform init
```

Verify:
- [ ] Terraform initialized successfully
- [ ] Backend configured (should see S3 backend message)
- [ ] Providers downloaded

```bash
terraform plan
```

Verify:
- [ ] Plan shows resources to be created (not destroyed)
- [ ] No errors in plan
- [ ] Review resource count (should be ~30-40 resources)

```bash
terraform apply
```

Verify:
- [ ] Apply completed successfully
- [ ] No errors
- [ ] Outputs displayed (ECR URL, ECS cluster, etc.)

### Step 4: Build and Push Docker Image

**Option A: Via GitHub Actions (Recommended)**
```bash
git add .
git commit -m "Add Terraform infrastructure"
git push origin main
```

Verify:
- [ ] GitHub Actions workflow triggered
- [ ] Docker build job successful
- [ ] Image pushed to ECR
- [ ] Deployment job successful

**Option B: Manual**
```bash
# Get ECR URL from Terraform output
cd terraform/environments/staging
ECR_URL=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push
cd ../../python-ocr
docker build -t receiptly-python-ocr:staging-latest .
docker tag receiptly-python-ocr:staging-latest $ECR_URL:staging-latest
docker push $ECR_URL:staging-latest
```

Verify:
- [ ] Docker build successful
- [ ] Image pushed to ECR
- [ ] Image visible in AWS Console (ECR → receiptly-python-ocr)

### Step 5: Update ECS Service
```bash
cd terraform/environments/staging
terraform apply
```

Verify:
- [ ] ECS service updated with new image
- [ ] Tasks running (check AWS Console → ECS)

### Step 6: Verify Deployment
```bash
# Check ECS service
aws ecs describe-services \
  --cluster receiptly-staging-cluster \
  --services receiptly-staging-service \
  --region ap-southeast-1 \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'
```

Verify:
- [ ] Service status: ACTIVE
- [ ] Running count matches desired count
- [ ] No deployment failures

```bash
# Check logs
aws logs tail /ecs/receiptly-staging --follow --region ap-southeast-1
```

Verify:
- [ ] Application logs visible
- [ ] No error messages
- [ ] Health check passing

## ✅ Production Deployment

### Prerequisites
- [ ] Staging deployed and tested
- [ ] Docker image tested in staging
- [ ] All tests passing

### Deploy Production
```bash
cd terraform/environments/production

# Set credentials
export TF_VAR_azure_endpoint="https://your-endpoint.cognitiveservices.azure.com/"
export TF_VAR_azure_key="your-azure-key"

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply
```

Verify:
- [ ] All resources created successfully
- [ ] 2 tasks running (check AWS Console)
- [ ] NAT gateway created
- [ ] Private subnets used

## ✅ Post-Deployment Verification

### Health Checks
- [ ] ECS tasks running (AWS Console → ECS)
- [ ] CloudWatch logs flowing
- [ ] No errors in application logs

### Security
- [ ] Secrets stored in Secrets Manager (not in code)
- [ ] S3 bucket has encryption enabled
- [ ] S3 public access blocked
- [ ] IAM roles use least privilege

### Cost Monitoring
- [ ] Check initial costs (AWS Cost Explorer)
- [ ] Set up billing alerts
- [ ] Budget created for project

### Documentation
- [ ] Team notified of new infrastructure
- [ ] Deployment guide shared
- [ ] Secrets documented (location, not values)

## ✅ CI/CD Verification

### GitHub Actions
- [ ] Workflows visible in Actions tab
- [ ] Docker build workflow triggered on push
- [ ] Terraform deploy workflow triggered on merge
- [ ] All jobs passing

### Test Deployment Flow
1. Create feature branch
   ```bash
   git checkout -b test/deployment-flow
   echo "# Test" >> README.md
   git add . && git commit -m "Test deployment"
   git push origin test/deployment-flow
   ```

2. Create Pull Request
   - [ ] PR created
   - [ ] GitHub Actions runs terraform plan
   - [ ] Plan comment added to PR

3. Merge PR
   - [ ] PR merged to main
   - [ ] Docker build triggered
   - [ ] Staging deployment triggered
   - [ ] All jobs successful

## ✅ Operational Readiness

### Monitoring
- [ ] CloudWatch dashboard created
- [ ] Log insights queries saved
- [ ] Alarms configured (optional but recommended)

### Runbooks
- [ ] Deployment procedure documented
- [ ] Rollback procedure documented
- [ ] Troubleshooting guide reviewed

### Access
- [ ] AWS access documented
- [ ] GitHub access verified
- [ ] Azure access verified

## 🆘 Troubleshooting

### Common Issues

**Issue: State lock error**
```bash
terraform force-unlock <LOCK_ID>
```

**Issue: ECS tasks not starting**
1. Check CloudWatch logs
2. Verify secrets are set
3. Check IAM permissions
4. Verify Docker image exists

**Issue: High costs**
1. Check task count
2. Review NAT gateway usage
3. Check S3 storage size

**Issue: GitHub Actions failing**
1. Verify secrets are set
2. Check AWS credentials
3. Review workflow logs

## 📋 Maintenance Tasks

### Weekly
- [ ] Review CloudWatch logs for errors
- [ ] Check ECS task health
- [ ] Monitor costs

### Monthly
- [ ] Review and optimize costs
- [ ] Update Docker images
- [ ] Review security groups
- [ ] Update dependencies

### Quarterly
- [ ] Terraform version update
- [ ] AWS provider update
- [ ] Security audit
- [ ] Disaster recovery test

## 🎉 Deployment Complete!

If all items are checked, your deployment is complete and operational!

**Staging**: http://[your-alb-url].ap-southeast-1.elb.amazonaws.com
**Logs**: AWS Console → CloudWatch → Log groups → /ecs/receiptly-staging

### Next Steps
1. Add custom domain (Route 53 + ACM)
2. Configure Application Load Balancer
3. Set up auto-scaling
4. Add monitoring alerts
5. Implement backup strategy

---

**Need Help?**
- Check: `terraform/README.md`
- Quick reference: `terraform/QUICKSTART.md`
- Deployment guide: `DEPLOYMENT.md`

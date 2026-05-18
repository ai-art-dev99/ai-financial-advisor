# راهنمای Deploy روی AWS

## پیش‌نیازها

```bash
# نصب ابزارها
brew install awscli terraform   # macOS
# یا برای Windows: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html

aws configure
# AWS Access Key ID: ...
# AWS Secret Access Key: ...
# Default region: us-east-1
# Default output format: json
```

---

## مرحله ۱ — backend state برای Terraform

```bash
# یک‌بار اجرا کن (قبل از terraform init)
aws s3 mb s3://robo-advisor-tfstate --region us-east-1
aws s3api put-bucket-versioning \
  --bucket robo-advisor-tfstate \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name robo-advisor-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## مرحله ۲ — اجرای Terraform

```bash
cd infrastructure/terraform/envs/prod

terraform init

terraform plan \
  -var="domain_name=yourdomain.com" \
  -var="db_password=STRONG_PASSWORD" \
  -var="jwt_secret=RANDOM_64_CHAR_STRING" \
  -var="anthropic_api_key=sk-ant-..." \
  -var="alpha_vantage_key=YOUR_KEY"

terraform apply   # تایپ 'yes' برای تأیید
```

بعد از apply:
```bash
terraform output alb_dns        # آدرس load balancer
terraform output cloudfront_url # آدرس frontend
terraform output ecr_urls       # آدرس ECR repos
```

---

## مرحله ۳ — تنظیم DNS

در پنل دامنه‌ات (Cloudflare، Route53، و غیره):

```
# API backend
api.yourdomain.com  CNAME  <alb_dns از terraform output>

# Frontend
yourdomain.com      CNAME  <cloudfront_url از terraform output>
```

---

## مرحله ۴ — push اولین image به ECR

```bash
# دریافت آدرس‌های ECR
ECR=$(terraform output -json ecr_urls)
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

# لاگین به ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $REGISTRY

# Build و push هر سرویس
for svc in auth portfolio ai-advisor market-data; do
  docker build -t $REGISTRY/robo-advisor-$svc:latest services/$svc/
  docker push $REGISTRY/robo-advisor-$svc:latest
done
```

---

## مرحله ۵ — GitHub Secrets

در مخزن GitHub خودت برو به Settings > Secrets > Actions و این‌ها رو اضافه کن:

| Secret | مقدار |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | کلید AWS |
| `AWS_SECRET_ACCESS_KEY` | secret AWS |
| `AWS_ACCOUNT_ID` | شماره حساب AWS |
| `DOMAIN_NAME` | yourdomain.com |
| `FRONTEND_BUCKET` | نام bucket از terraform output |
| `CLOUDFRONT_DISTRIBUTION_ID` | از terraform output |

---

## مرحله ۶ — اولین deploy خودکار

```bash
git add .
git commit -m "feat: phase 3 - AWS deployment"
git push origin main
# GitHub Actions شروع می‌کنه: test → build → deploy → smoke test
```

---

## چک‌های بعد از deploy

```bash
# بررسی سرویس‌ها
aws ecs list-services --cluster robo-advisor-prod

# لاگ‌ها
aws logs tail /ecs/robo-advisor --follow

# health check
curl https://api.yourdomain.com/api/v1/auth/health
curl https://api.yourdomain.com/api/v1/portfolio/health
curl https://api.yourdomain.com/api/v1/ai/health
```

---

## هزینه تخمینی ماهانه

| سرویس | نوع | هزینه |
|-------|-----|--------|
| ECS Fargate (4 task × 0.5 vCPU) | ~$25 |
| RDS PostgreSQL db.t3.small | ~$25 |
| RDS TimescaleDB db.t3.small | ~$25 |
| ElastiCache t3.small | ~$25 |
| ALB | ~$20 |
| CloudFront + S3 | ~$5 |
| NAT Gateway | ~$35 |
| **جمع** | **~$160/ماه** |

> برای محیط dev هزینه رو با `desired_count = 0` در ساعات غیرکاری کاهش بده.
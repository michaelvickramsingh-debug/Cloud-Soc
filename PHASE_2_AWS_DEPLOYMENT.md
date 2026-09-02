# Phase 2: AWS Deployment Guide

**Objective**: Deploy CloudGuard to AWS with real CloudTrail ingestion, auto-scaling, and production-grade infrastructure.

**Timeline**: 2-3 hours
**Cost**: $150-300/month (estimated)

---

## Prerequisites

Before starting, ensure you have:

```bash
# AWS CLI configured with credentials
aws --version
aws sts get-caller-identity  # Verify credentials

# Required tools
terraform --version         # Infrastructure as Code
docker --version           # Container builds
jq --version              # JSON parsing
```

If not installed:
```bash
# macOS
brew install awscli terraform docker jq

# Linux
sudo apt-get install awscli terraform docker.io jq
```

---

## Phase 2.1: AWS Account Setup (30 mins)

### Step 1: Create CloudGuard AWS Account Resources

```bash
# Set variables
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLOUDGUARD_ENV="production"

echo "Region: $AWS_REGION"
echo "Account ID: $AWS_ACCOUNT_ID"
```

### Step 2: Create IAM Roles

**Lambda Execution Role:**
```bash
cat > /tmp/lambda-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name cloudguard-lambda-role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --region $AWS_REGION

# Attach policy for S3 and logs
aws iam put-role-policy \
  --role-name cloudguard-lambda-role \
  --policy-name cloudguard-lambda-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": "arn:aws:s3:::cloudtrail-logs-*/*"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": "arn:aws:logs:*:*:*"
      }
    ]
  }'
```

**ECS Task Execution Role:**
```bash
cat > /tmp/ecs-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name cloudguard-ecs-task-role \
  --assume-role-policy-document file:///tmp/ecs-trust-policy.json

aws iam attach-role-policy \
  --role-name cloudguard-ecs-task-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### Step 3: Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name cloudguard-backend \
  --region $AWS_REGION

aws ecr create-repository \
  --repository-name cloudguard-frontend \
  --region $AWS_REGION

# Get ECR login
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

---

## Phase 2.2: Database Setup (20 mins)

### Step 1: Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier cloudguard-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username cloudguard_admin \
  --master-user-password "ChangeMe123!@#" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --db-name cloudguard \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxxxxx \
  --multi-az false \
  --backup-retention-period 7 \
  --enable-cloudwatch-logs-exports postgresql \
  --region $AWS_REGION
```

Wait for database to be available (5-10 minutes):
```bash
aws rds wait db-instance-available --db-instance-identifier cloudguard-db --region $AWS_REGION
```

### Step 2: Get Database Endpoint

```bash
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier cloudguard-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region $AWS_REGION)

echo "Database endpoint: $DB_ENDPOINT"

# Connection string
DATABASE_URL="postgresql://cloudguard_admin:ChangeMe123!@#@$DB_ENDPOINT:5432/cloudguard"
```

### Step 3: Initialize Database Schema

```bash
# From local machine or EC2 jump host
psql $DATABASE_URL < backend/database/schema.sql
```

---

## Phase 2.3: S3 & CloudTrail Setup (20 mins)

### Step 1: Create S3 Bucket for CloudTrail Logs

```bash
BUCKET_NAME="cloudtrail-logs-cloudguard-$(date +%s)"

aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### Step 2: Create CloudTrail

```bash
aws cloudtrail create-trail \
  --name cloudguard-trail \
  --s3-bucket-name $BUCKET_NAME \
  --region $AWS_REGION \
  --is-multi-region-trail \
  --enable-log-file-validation

# Start logging
aws cloudtrail start-logging \
  --trail-name cloudguard-trail \
  --region $AWS_REGION
```

### Step 3: Configure S3 Event Notifications for Lambda

```bash
cat > /tmp/s3-lambda-notification.json <<'EOF'
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT_ID:function:cloudguard-parse-logs",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "AWSLogs/"
            },
            {
              "Name": "suffix",
              "Value": ".json.gz"
            }
          ]
        }
      }
    }
  ]
}
EOF

# Replace placeholders
sed -i "s/REGION/$AWS_REGION/g" /tmp/s3-lambda-notification.json
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" /tmp/s3-lambda-notification.json

aws s3api put-bucket-notification-configuration \
  --bucket $BUCKET_NAME \
  --notification-configuration file:///tmp/s3-lambda-notification.json
```

---

## Phase 2.4: Lambda Deployment (20 mins)

### Step 1: Package Lambda Function

```bash
./backend/lambda/build_deployment_package.sh

# Upload to S3
aws s3 cp lambda/deployment.zip s3://$BUCKET_NAME/lambda/deployment.zip \
  --region $AWS_REGION
```

### Step 2: Create Lambda Function

```bash
LAMBDA_ROLE_ARN=$(aws iam get-role \
  --role-name cloudguard-lambda-role \
  --query 'Role.Arn' \
  --output text)

aws lambda create-function \
  --function-name cloudguard-parse-logs \
  --runtime python3.11 \
  --role $LAMBDA_ROLE_ARN \
  --handler parse_cloudtrail.lambda_handler \
  --timeout 60 \
  --memory-size 512 \
  --code S3Bucket=$BUCKET_NAME,S3Key=lambda/deployment.zip \
  --environment "Variables={CLOUDGUARD_API=https://YOUR_BACKEND_URL/api/logs/ingest}" \
  --region $AWS_REGION
```

### Step 3: Grant S3 Permission to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name cloudguard-parse-logs \
  --statement-id AllowS3Invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::$BUCKET_NAME \
  --region $AWS_REGION
```

---

## Phase 2.5: Backend Deployment (30 mins)

### Step 1: Build and Push Docker Image

```bash
cd /Users/micvic/code/CloudSoc/Cloud-Soc

# Build image
docker build -t cloudguard-backend:latest ./backend

# Tag for ECR
docker tag cloudguard-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cloudguard-backend:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cloudguard-backend:latest
```

### Step 2: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name cloudguard-cluster \
  --region $AWS_REGION

# Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /ecs/cloudguard-backend \
  --region $AWS_REGION
```

### Step 3: Create ECS Task Definition

```bash
cat > /tmp/ecs-task-def.json <<'EOF'
{
  "family": "cloudguard-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/cloudguard-backend:latest",
      "portMappings": [
        {
          "containerPort": 5001,
          "hostPort": 5001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "5001"
        },
        {
          "name": "DATABASE_URL",
          "value": "DATABASE_URL_HERE"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cloudguard-backend",
          "awslogs-region": "REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5001/api/stats || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Replace placeholders
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" /tmp/ecs-task-def.json
sed -i "s/REGION/$AWS_REGION/g" /tmp/ecs-task-def.json
sed -i "s|DATABASE_URL_HERE|$DATABASE_URL|g" /tmp/ecs-task-def.json

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file:///tmp/ecs-task-def.json \
  --region $AWS_REGION
```

### Step 4: Create ECS Service

```bash
aws ecs create-service \
  --cluster cloudguard-cluster \
  --service-name cloudguard-backend-service \
  --task-definition cloudguard-backend:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --region $AWS_REGION
```

---

## Phase 2.6: Frontend Deployment (20 mins)

### Step 1: Build Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Deploy to S3
aws s3 sync dist/ s3://cloudguard-frontend-$AWS_ACCOUNT_ID --delete
```

### Step 2: Create CloudFront Distribution

```bash
aws cloudfront create-distribution \
  --origin-domain-name cloudguard-frontend-$AWS_ACCOUNT_ID.s3.amazonaws.com \
  --default-root-object index.html \
  --region $AWS_REGION
```

---

## Phase 2.7: Integration Testing (30 mins)

### Test 1: Verify Lambda Execution

```bash
# Trigger a test CloudTrail event
aws ec2 describe-instances --region $AWS_REGION

# Check Lambda logs
aws logs tail /aws/lambda/cloudguard-parse-logs --follow --region $AWS_REGION
```

### Test 2: Verify Backend Connectivity

```bash
# Get backend URL
BACKEND_URL=$(aws ecs describe-services \
  --cluster cloudguard-cluster \
  --services cloudguard-backend-service \
  --query 'services[0].loadBalancers[0].targetGroupArn' \
  --region $AWS_REGION)

# Test API
curl https://$BACKEND_URL/api/stats
```

### Test 3: Load Test

```bash
# Send 100 test logs
for i in {1..100}; do
  curl -X POST https://$BACKEND_URL/api/logs/ingest \
    -H "Content-Type: application/json" \
    -d "{\"logs\": [{\"timestamp\": \"2024-08-28T$(printf '%02d' $((RANDOM % 24))):$(printf '%02d' $((RANDOM % 60))):00Z\", \"user\": \"test-user-$i\", \"event\": \"PutUserPolicy\", \"source\": \"iam.amazonaws.com\", \"ip\": \"203.0.113.$((RANDOM % 255))\", \"region\": \"us-east-1\", \"status\": \"success\", \"resource\": \"test\"}], \"source\": \"cloudtrail\"}" &
done

wait

# Check logs in CloudWatch
aws logs tail /ecs/cloudguard-backend --follow --region $AWS_REGION
```

---

## Phase 2.8: Monitoring & Alerts

### Create CloudWatch Alarms

```bash
# High error rate alert
aws cloudwatch put-metric-alarm \
  --alarm-name cloudguard-backend-errors \
  --alarm-description "Alert when error rate > 5%" \
  --metric-name ErrorCount \
  --namespace AWS/ECS \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --region $AWS_REGION

# High latency alert
aws cloudwatch put-metric-alarm \
  --alarm-name cloudguard-backend-latency \
  --alarm-description "Alert when latency > 1000ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --region $AWS_REGION
```

---

## Troubleshooting

### Lambda Not Invoking
```bash
# Check S3 notification configuration
aws s3api get-bucket-notification-configuration --bucket $BUCKET_NAME

# Check Lambda execution role permissions
aws iam list-role-policies --role-name cloudguard-lambda-role
```

### Backend Not Responding
```bash
# Check ECS task logs
aws logs tail /ecs/cloudguard-backend --follow

# Check task status
aws ecs describe-tasks \
  --cluster cloudguard-cluster \
  --tasks $(aws ecs list-tasks --cluster cloudguard-cluster --query 'taskArns[0]' --output text) \
  --region $AWS_REGION
```

### Database Connection Failed
```bash
# Test connectivity
psql -h $DB_ENDPOINT -U cloudguard_admin -d cloudguard -c "SELECT version();"

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxx --region $AWS_REGION
```

---

## Cost Estimation

| Service | Instance | Estimate/Month |
|---------|----------|----------------|
| RDS PostgreSQL | t3.micro | $30 |
| ECS Fargate | 256 CPU, 512 MB | $50 |
| Lambda | 1M invocations | $20 |
| S3 | 100 GB storage | $20 |
| CloudTrail | Enabled | $2 |
| CloudFront | 1 TB data | $50 |
| **Total** | | **~$170** |

---

## Success Checklist

- [ ] CloudTrail enabled and logging to S3
- [ ] S3 bucket configured with Lambda notifications
- [ ] Lambda function deployed and receiving events
- [ ] RDS PostgreSQL instance running
- [ ] Backend deployed to ECS Fargate
- [ ] Frontend deployed to S3 + CloudFront
- [ ] Backend responding to /api/logs/ingest
- [ ] Logs flowing through entire pipeline
- [ ] Alerts appearing on frontend dashboard
- [ ] CloudWatch monitoring configured
- [ ] Auto-scaling policies configured

---

## Next Steps

1. **Auto-Scaling**: Configure ECS auto-scaling (1-5 tasks based on load)
2. **Multi-AZ**: Deploy to multiple availability zones for HA
3. **Custom Domain**: Configure Route 53 with custom domain
4. **SSL/TLS**: Install ACM certificate for HTTPS
5. **Backup Strategy**: Configure automated RDS backups

---

**Ready to deploy?** Start with Phase 2.1 and work through each section sequentially.

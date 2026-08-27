# CloudGuard AWS Lab Environment Configuration

## Local Development (Docker)
```bash
# Start services with docker-compose
docker-compose up -d

# Services will be available at:
# Frontend:   http://localhost:3000
# Backend:    http://localhost:5001/api
# Database:   localhost:5432
# pgAdmin:    http://localhost:5050
```

## Environment Variables

### Backend (.env or docker-compose)
```
FLASK_ENV=production
DEBUG=False
PORT=5001
WORKERS=4

# Database
DB_TYPE=postgresql
DATABASE_URL=postgresql://user:password@host:5432/cloudguard
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# AWS Services (if using CloudTrail, CloudWatch)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=${YOUR_KEY}
AWS_SECRET_ACCESS_KEY=${YOUR_SECRET}

# CloudWatch Logs
CLOUDWATCH_LOG_GROUP=/cloudguard/backend
CLOUDWATCH_LOG_STREAM=backend-prod

# Prowler Integration
PROWLER_ENABLED=true
PROWLER_BUCKET=s3://your-prowler-results-bucket
```

### Frontend (.env)
```
REACT_APP_API_URL=http://backend:5001/api
REACT_APP_ENVIRONMENT=production
```

## AWS RDS Configuration

### Create RDS Instance (PostgreSQL)
```bash
aws rds create-db-instance \
  --db-instance-identifier cloudguard-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username cloudguard_user \
  --master-user-password ${SECURE_PASSWORD} \
  --allocated-storage 20 \
  --storage-type gp3 \
  --db-name cloudguard \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx \
  --multi-az false \
  --backup-retention-period 7 \
  --enable-cloudwatch-logs-exports postgresql
```

### Connection String
```
postgresql://cloudguard_user:PASSWORD@cloudguard-db.xxxxx.rds.amazonaws.com:5432/cloudguard
```

## AWS ECS Deployment

### Task Definition (backend)
```json
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
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:cloudguard/db-url"
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
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:5001/api/stats || exit 1"
        ],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

### Task Definition (frontend)
```json
{
  "family": "cloudguard-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/cloudguard-frontend:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REACT_APP_API_URL",
          "value": "https://api.cloudguard.example.com"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cloudguard-frontend",
          "awslogs-region": "REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "wget --quiet --tries=1 --spider http://localhost:3000 || exit 1"
        ],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

## CloudWatch Monitoring

### Log Groups
```bash
# Create log groups
aws logs create-log-group --log-group-name /cloudguard/backend
aws logs create-log-group --log-group-name /cloudguard/frontend
aws logs create-log-group --log-group-name /cloudguard/database
```

### CloudWatch Dashboards
- API response times
- Error rates
- Alert generation rate
- Database query performance
- Frontend load times

## Security Best Practices

1. **IAM Roles** - Service-to-service communication
2. **Secrets Manager** - Store database credentials
3. **Security Groups** - Restrict network access
4. **VPC** - Private subnets for database
5. **SSL/TLS** - HTTPS for all communications
6. **API Keys** - For CloudTrail & Prowler integration

## Scaling Configuration

### Horizontal Scaling (ECS Auto Scaling)
```bash
# Target tracking: 70% CPU utilization
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/cloudguard-cluster/cloudguard-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cloudguard-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

### Vertical Scaling (Task Size)
- Start: t3.micro (256 CPU, 512 MB)
- Scale up to t3.small (512 CPU, 1024 MB) if needed

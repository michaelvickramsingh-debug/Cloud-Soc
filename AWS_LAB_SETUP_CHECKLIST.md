# AWS Lab Setup Checklist
## Phase 1: Foundation Setup ✅ (START HERE)
### 1.1 Prerequisites
- [ ] AWS Account created with billing enabled
- [ ] AWS CLI installed (`aws --version`)
- [ ] AWS credentials configured (`aws configure`)
- [ ] Docker installed (`docker --version`)
- [ ] Verify AWS access: `aws sts get-caller-identity`

**Save your AWS Account ID:** _______________

### 1.2 VPC & Network
- [ ] VPC created (10.0.0.0/16)
  - VPC ID: _______________
- [ ] 2 Public Subnets created (ALB)
  - Public Subnet 1 (us-east-1a): _______________
  - Public Subnet 2 (us-east-1b): _______________
- [ ] 2 Private Subnets created (RDS)
  - Private Subnet 1 (us-east-1a): _______________
  - Private Subnet 2 (us-east-1b): _______________
- [ ] Internet Gateway created
  - IGW ID: _______________
- [ ] Route Table created & associated with public subnets
  - Route Table ID: _______________

### 1.3 Security Groups
- [ ] ALB Security Group created
  - SG ID: _______________
  - Rules: HTTP (80), HTTPS (443)
- [ ] ECS Security Group created
  - SG ID: _______________
  - Rules: 5001 (backend), 3000 (frontend) from ALB
- [ ] RDS Security Group created
  - SG ID: _______________
  - Rules: 5432 (PostgreSQL) from ECS SG

### 1.4 RDS PostgreSQL Database
- [ ] DB Subnet Group created
  - Name: cloudguard-db-subnet
- [ ] RDS Instance created
  - Identifier: cloudguard-db
  - Endpoint: _______________
  - Username: cloudguard_user
  - Password: [SAVED SECURELY]
  - Database: cloudguard
  - Status: available ✓

### 1.5 ECR Container Registry
- [ ] Backend repository created
  - Repository: cloudguard-backend
  - URI: _______________
- [ ] Frontend repository created
  - Repository: cloudguard-frontend
  - URI: _______________

### 1.6 Docker Images
- [ ] Backend image built & pushed to ECR
  - Tag: latest
  - Size: [MB]
- [ ] Frontend image built & pushed to ECR
  - Tag: latest
  - Size: [MB]

### 1.7 ECS Cluster & IAM
- [ ] ECS Cluster created
  - Cluster: cloudguard-cluster
- [ ] CloudWatch Log Groups created
  - [ ] /ecs/cloudguard-backend
  - [ ] /ecs/cloudguard-frontend
- [ ] IAM Role created (ecsTaskExecutionRole)
  - Role ARN: _______________

---

## Phase 2: Deployment Setup 📋 (NEXT)

### 2.1 Task Definitions
- [ ] Backend Task Definition registered
  - Family: cloudguard-backend
  - Latest revision: ___
  - Memory: 512 MB
  - CPU: 256
  - Container name: backend
  - Image: [ECR URI]:latest
  - Port: 5001
  - Log group: /ecs/cloudguard-backend

- [ ] Frontend Task Definition registered
  - Family: cloudguard-frontend
  - Latest revision: ___
  - Memory: 512 MB
  - CPU: 256
  - Container name: frontend
  - Image: [ECR URI]:latest
  - Port: 3000
  - Log group: /ecs/cloudguard-frontend

### 2.2 Application Load Balancer
- [ ] ALB created
  - ALB Name: cloudguard-alb
  - ALB DNS: _______________
  - Scheme: internet-facing
  - Subnets: [2 public subnets]
  - Security Group: [ALB SG]

- [ ] Target Group (Backend) created
  - Name: cloudguard-backend-tg
  - Port: 5001
  - Protocol: HTTP
  - Target type: IP
  - Health check path: /api/stats
  - Health check interval: 30s

- [ ] Target Group (Frontend) created
  - Name: cloudguard-frontend-tg
  - Port: 3000
  - Protocol: HTTP
  - Target type: IP
  - Health check path: /
  - Health check interval: 30s

- [ ] ALB Listeners configured
  - [ ] HTTP (80) → Backend TG
  - [ ] HTTP (80) → Frontend TG (path-based)

### 2.3 ECS Services
- [ ] Backend Service created
  - Cluster: cloudguard-cluster
  - Service: cloudguard-backend
  - Task definition: cloudguard-backend:1
  - Desired count: 2
  - Min: 1, Max: 5 (auto-scaling)
  - Target group: cloudguard-backend-tg
  - Status: ACTIVE

- [ ] Frontend Service created
  - Cluster: cloudguard-cluster
  - Service: cloudguard-frontend
  - Task definition: cloudguard-frontend:1
  - Desired count: 2
  - Min: 1, Max: 5 (auto-scaling)
  - Target group: cloudguard-frontend-tg
  - Status: ACTIVE

### 2.4 CloudWatch Monitoring
- [ ] CloudWatch Dashboards created
  - [ ] Backend dashboard (CPU, Memory, Requests)
  - [ ] Frontend dashboard (Latency, Errors)
  - [ ] Database dashboard (Connections, Query time)

- [ ] CloudWatch Alarms created
  - [ ] Backend CPU > 80%
  - [ ] Backend Memory > 85%
  - [ ] Error rate > 1%
  - [ ] RDS Connection pool exhausted
  - [ ] ALB Target Unhealthy

### 2.5 Auto-Scaling
- [ ] Auto Scaling Policy created for Backend
  - Min: 1, Max: 5 instances
  - Target CPU: 70%
  - Scale-out cooldown: 300s
  - Scale-in cooldown: 300s

- [ ] Auto Scaling Policy created for Frontend
  - Min: 1, Max: 5 instances
  - Target CPU: 70%
  - Scale-out cooldown: 300s
  - Scale-in cooldown: 300s

---

## Phase 3: Testing & Validation 🧪 (VERIFY)

### 3.1 API Connectivity
- [ ] Backend API accessible via ALB
  - URL: http://[ALB-DNS]/api/stats
  - Status: 200 OK
- [ ] Frontend accessible via ALB
  - URL: http://[ALB-DNS]
  - Status: 200 OK
- [ ] Frontend can call backend API
  - Check browser console for no CORS errors

### 3.2 Database Connectivity
- [ ] Connect to RDS from ECS tasks
  - Connection string verified
  - Test query works
- [ ] Database populated with schema
  - Tables created
  - Initial data loaded

### 3.3 Application Testing
- [ ] Dashboard loads correctly
- [ ] Scenario simulation works
- [ ] Logs are generated
- [ ] Alerts are created
- [ ] Detection metrics display

### 3.4 Performance Testing
- [ ] Backend responds < 200ms (p99)
- [ ] Frontend loads < 3s
- [ ] Database queries < 100ms
- [ ] Load test: 100 req/s successful

### 3.5 Monitoring Verification
- [ ] CloudWatch logs appearing
- [ ] Metrics being recorded
- [ ] Dashboards show data
- [ ] Alarms configured correctly

---

## Phase 4: Production Hardening 🔐 (FINALIZE)

### 4.1 Security Configuration
- [ ] Secrets Manager secrets created
  - [ ] Database password
  - [ ] API keys
  - [ ] JWT secrets
- [ ] Security groups locked down
- [ ] VPC endpoints configured (if needed)
- [ ] WAF rules configured (if needed)

### 4.2 High Availability
- [ ] Multi-AZ RDS enabled
- [ ] Services deployed in 2+ AZs
- [ ] ALB health checks verified
- [ ] Manual failover tested

### 4.3 Backup & Disaster Recovery
- [ ] RDS automated backups enabled (7 days)
- [ ] Manual backup created
- [ ] Backup restore tested
- [ ] Disaster recovery runbook created

### 4.4 DNS & TLS
- [ ] Route 53 DNS configured
- [ ] ACM Certificate created
- [ ] HTTPS listeners configured
- [ ] HTTP → HTTPS redirect enabled

### 4.5 Cost Optimization
- [ ] Reserved capacity purchased (if prod)
- [ ] Right-sized instances verified
- [ ] Data transfer costs reviewed
- [ ] Estimated monthly cost: $___

### 4.6 Compliance & Audit
- [ ] CloudTrail enabled
- [ ] VPC Flow Logs enabled
- [ ] Access logging configured
- [ ] Audit log retention set

---

## Phase 5: Go-Live 🚀 (LAUNCH)

### 5.1 Pre-Launch Verification
- [ ] All Phase 3 & 4 tests passing
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Monitoring & alerts working
- [ ] Disaster recovery tested

### 5.2 Team Readiness
- [ ] Team trained on monitoring
- [ ] Runbooks documented
- [ ] On-call rotation established
- [ ] Escalation path defined

### 5.3 Go-Live Execution
- [ ] Traffic switched to new environment
- [ ] Monitoring dashboards live
- [ ] Alert notifications tested
- [ ] Rollback plan ready

### 5.4 Post-Launch
- [ ] Monitor for 24 hours
- [ ] Verify logs & metrics
- [ ] Customer feedback collected
- [ ] Document lessons learned

---

## Important URLs & Credentials

| Item | Value | Status |
|------|-------|--------|
| AWS Account ID | | ✓ |
| VPC ID | | ✓ |
| ALB DNS | | ⏳ |
| Backend URL | | ⏳ |
| Frontend URL | | ⏳ |
| RDS Endpoint | | ⏳ |
| DB Username | cloudguard_user | ✓ |
| DB Password | [SECURE] | ✓ |
| ECS Cluster | cloudguard-cluster | ✓ |
| ECR Backend URI | | ⏳ |
| ECR Frontend URI | | ⏳ |

---

## Troubleshooting

### ECS Task Won't Start
1. Check CloudWatch logs: `/ecs/cloudguard-backend`
2. Verify IAM role has permissions
3. Check security group rules
4. Verify database connectivity

### Database Won't Connect
1. Verify RDS status: `aws rds describe-db-instances`
2. Check security group rules allow ECS SG
3. Verify subnet is in DB subnet group
4. Test connection from bastion host

### ALB Health Checks Failing
1. Check target group health: `aws elbv2 describe-target-health`
2. Verify security group rules
3. Check application logs for startup errors
4. Increase health check timeout

---

## Next Steps

Once Phase 1 is complete:
1. Review Phase 2 instructions
2. Follow AWS_DEPLOYMENT.md for JSON task definitions
3. Run Phase 2 setup commands
4. Execute Phase 3 testing checklist
5. Proceed to Phase 4 for production hardening

**Estimated Time:**
- Phase 1: 2-3 hours
- Phase 2: 1-2 hours
- Phase 3: 1-2 hours
- Phase 4: 2-3 hours
- Phase 5: 1+ hour

**Total: 7-11 hours of setup & testing**

---

**Last Updated:** 2026-08-27
**Status:** Ready for Phase 1 Implementation
**Owner:** [Your Name]

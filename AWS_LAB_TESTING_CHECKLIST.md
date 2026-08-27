# CloudGuard AWS Lab Testing Checklist

## Pre-Deployment

- [ ] **Docker Images Built**
  - [ ] Backend image builds without errors
  - [ ] Frontend image builds without errors
  - [ ] Images tagged with version numbers
  - [ ] Images uploaded to ECR

- [ ] **AWS Environment Prepared**
  - [ ] VPC and subnets configured
  - [ ] Security groups created (port 80, 443, 5432, 5001, 3000)
  - [ ] RDS PostgreSQL instance created
  - [ ] Database initialized with schema
  - [ ] Secrets Manager secrets created (DB password, API keys)
  - [ ] IAM roles created for ECS tasks
  - [ ] CloudWatch log groups created

- [ ] **Network Configuration**
  - [ ] ALB (Application Load Balancer) configured
  - [ ] Security group rules allow ALB → ECS traffic
  - [ ] Security group rules allow ECS → RDS traffic
  - [ ] NAT Gateway for outbound internet (Prowler calls)
  - [ ] Route 53 DNS entries (if using custom domain)

## Docker Deployment Testing

### Local Docker Testing (Before AWS)
```bash
# Terminal 1: Start services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Terminal 2: Test backend
curl http://localhost:5001/api/stats
curl http://localhost:5001/api/scenarios

# Test frontend
curl http://localhost:3000

# Test database
psql -h localhost -U cloudguard_user -d cloudguard -c "SELECT COUNT(*) FROM scenarios;"
```

Testing Checklist:
- [ ] All containers start without errors
- [ ] All containers report "healthy" status
- [ ] Backend API responds to requests
- [ ] Frontend loads without 404 errors
- [ ] Database connection works
- [ ] Cross-container communication works
- [ ] Logs are captured in CloudWatch

## AWS ECS Deployment Testing

### Task Definition Deployment
- [ ] Backend task definition created
- [ ] Frontend task definition created
- [ ] Both point to correct ECR images
- [ ] Environment variables set correctly
- [ ] Secrets referenced from Secrets Manager
- [ ] Log configuration correct

### Service Deployment
- [ ] Backend service created in ECS cluster
- [ ] Frontend service created in ECS cluster
- [ ] Services set desired count = 2 (for HA)
- [ ] Services set minimum = 1, maximum = 5 (auto-scaling)
- [ ] ALB target groups configured
- [ ] ALB listeners configured (HTTP → HTTPS)

### Verification Commands
```bash
# List services
aws ecs list-services --cluster cloudguard-cluster

# Get service details
aws ecs describe-services --cluster cloudguard-cluster --services cloudguard-backend

# View running tasks
aws ecs list-tasks --cluster cloudguard-cluster

# Get task details
aws ecs describe-tasks --cluster cloudguard-cluster --tasks <TASK_ARN>

# View CloudWatch logs
aws logs tail /ecs/cloudguard-backend --follow

# Check task health
aws elbv2 describe-target-health --target-group-arn <ARN>
```

## API Testing (AWS)

### Connectivity Tests
- [ ] Backend accessible via ALB
  ```bash
  curl https://api.cloudguard.example.com/api/stats
  ```
- [ ] Frontend accessible via CloudFront
  ```bash
  curl https://cloudguard.example.com
  ```
- [ ] Frontend can reach backend API
  - [ ] Check browser console for no CORS errors
  - [ ] Check browser Network tab for successful API calls

### Functionality Tests

#### Dashboard
- [ ] [ ] Dashboard loads with correct layout
- [ ] [ ] Metrics panel shows correct numbers
- [ ] [ ] Charts render properly
- [ ] [ ] No console errors in browser DevTools

#### Simulation
- [ ] [ ] Scenario dropdown shows all 5 scenarios
- [ ] [ ] Clicking "Simulate" triggers backend
- [ ] [ ] Logs are generated and appear in dashboard
- [ ] [ ] Alerts are created and appear in Alerts page
- [ ] [ ] Detection metrics update correctly

#### Alerts Page
- [ ] [ ] All alerts load and display
- [ ] [ ] Severity filter works (Critical, High, Medium)
- [ ] [ ] Alert detail view shows full information
- [ ] [ ] "Resolve" button works
- [ ] [ ] Resolved alerts disappear from open list

#### Logs Page
- [ ] [ ] All logs display with proper formatting
- [ ] [ ] Search/filter works
- [ ] [ ] Log detail view shows MITRE ATT&CK mapping
- [ ] [ ] Timeline filter shows only selected scenario

#### Best Practices Page
- [ ] [ ] All 5 best practices render
- [ ] [ ] Simulator buttons work for each BP
- [ ] [ ] Results update in real-time

## Database Testing

### RDS Connectivity
- [ ] Bastion host can connect to RDS
  ```bash
  psql -h <RDS_ENDPOINT> -U cloudguard_user -d cloudguard
  ```
- [ ] ECS tasks can connect to RDS
- [ ] Connection pooling active (check pg_stat_statements)

### Data Integrity
- [ ] Scenarios table has 5 rows
- [ ] Logs table increases with simulations
- [ ] Alerts table increases with detections
- [ ] Foreign key relationships maintained
- [ ] No orphaned records

### Backup & Recovery
- [ ] Automated backups configured (daily)
- [ ] Manual backup created
- [ ] Backup size reasonable (~10-50MB)
- [ ] Restore from backup works

## Performance Testing

### Load Testing (Backend)
```bash
# Install hey (load testing tool)
go get -u github.com/rakyll/hey

# Test API endpoint under load
hey -n 1000 -c 10 https://api.cloudguard.example.com/api/stats

# Monitor CloudWatch metrics
# - Check CPU utilization (should stay < 70%)
# - Check memory (should stay < 80%)
# - Check request latency (should be < 200ms p99)
```

Testing Checklist:
- [ ] API responds to 100 req/s with < 200ms latency
- [ ] Database handles 50 concurrent connections
- [ ] No memory leaks (memory stable after load)
- [ ] Auto-scaling triggers at configured thresholds
- [ ] Load balancer distributes traffic evenly

### Load Testing (Frontend)
- [ ] Frontend loads in < 3 seconds (on 4G)
- [ ] Dashboard interactive within 1 second of load
- [ ] Simulation completes in < 5 seconds
- [ ] No visual glitches or layout shifts

## CloudWatch Monitoring

### Metrics Review
- [ ] Backend CPU utilization graph shows
- [ ] Backend memory utilization graph shows
- [ ] Request count graph shows
- [ ] Error rate graph shows (should be 0%)
- [ ] Latency p50, p90, p99 visible
- [ ] ALB health checks passing

### Alarms Configured
- [ ] CPU > 80% → Alert
- [ ] Memory > 85% → Alert
- [ ] Error rate > 1% → Alert
- [ ] Health check failed → Alert
- [ ] Database connection pool exhausted → Alert

### Logs Analysis
```bash
# Find errors in backend logs
aws logs filter-log-events --log-group-name /ecs/cloudguard-backend \
  --filter-pattern "ERROR"

# Count requests by endpoint
aws logs filter-log-events --log-group-name /ecs/cloudguard-backend \
  --filter-pattern "GET /api"

# Find slow requests
aws logs filter-log-events --log-group-name /ecs/cloudguard-backend \
  --filter-pattern "[... , latency > 1000]"
```

Testing Checklist:
- [ ] No ERROR or CRITICAL logs
- [ ] Request latency < 500ms (p95)
- [ ] Database query latency < 100ms
- [ ] No auth/permission failures
- [ ] Metrics ingestion working

## Security Testing

### SSL/TLS
- [ ] Certificate valid (check expiry date)
- [ ] HTTPS redirects work
- [ ] Mixed content warnings absent
- [ ] SSL Labs score: A or A+

### Secrets Management
- [ ] Database password in Secrets Manager (not in code)
- [ ] API keys in Secrets Manager
- [ ] Secrets Manager access restricted to ECS role
- [ ] Secrets rotation configured (30-90 days)

### Network Security
- [ ] Backend not directly accessible (behind ALB)
- [ ] Database not publicly accessible
- [ ] Security groups follow least-privilege principle
- [ ] No open SSH ports (bastion only)
- [ ] WAF rules configured (if using)

### Application Security
- [ ] No hardcoded credentials in Docker image
- [ ] No debug mode enabled in production
- [ ] CORS properly configured (not `*`)
- [ ] Rate limiting enabled
- [ ] Input validation working

## AWS Lab Integration Testing

### CloudTrail Integration
- [ ] CloudTrail enabled for relevant services
- [ ] Logs sent to S3
- [ ] Backend can read CloudTrail logs
- [ ] Simulated actions appear in dashboard

### Prowler Integration
- [ ] Prowler role created with scan permissions
- [ ] Backend service role can invoke Prowler
- [ ] Prowler results appear in dashboard
- [ ] Findings mapped to security controls

### SNS Notifications (Optional)
- [ ] Critical alerts trigger SNS message
- [ ] SNS message format correct
- [ ] Email/Slack notifications received

## Failover & High Availability Testing

### Task Replacement
- [ ] Kill running backend task
- [ ] ECS automatically launches replacement
- [ ] Service remains available (no downtime)
- [ ] ALB removes failed task from rotation

### Zone Failure Simulation
- [ ] Deploy tasks in multiple AZs
- [ ] Simulate AZ failure
- [ ] Traffic automatically routes to healthy AZ
- [ ] No data loss

### Database Failover
- [ ] Enable Multi-AZ for RDS
- [ ] Trigger manual failover
- [ ] ECS tasks reconnect automatically
- [ ] Service available during failover

## Cost Optimization

- [ ] [ ] Right-sized task CPU/memory (not over-provisioned)
- [ ] [ ] Auto-scaling configured (scale down during off-hours)
- [ ] [ ] RDS instance right-sized
- [ ] [ ] Unused resources cleaned up
- [ ] [ ] Cost monitoring dashboard set up
- [ ] [ ] Estimated monthly cost < budget

## Documentation & Handoff

- [ ] [ ] Deployment guide complete
- [ ] [ ] Runbook for common issues
- [ ] [ ] Architecture diagrams updated
- [ ] [ ] Team trained on monitoring
- [ ] [ ] On-call procedures documented
- [ ] [ ] Escalation path defined

## Final Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps | | | |
| QA | | | |
| Security | | | |
| Product | | | |

## Known Issues & Workarounds

(To be filled during testing)

| Issue | Severity | Status | Workaround |
|-------|----------|--------|-----------|
| | | | |

---

**Testing Started:** ___________
**Testing Completed:** ___________
**Deployment Date:** ___________

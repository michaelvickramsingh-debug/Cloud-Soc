# Live Log Ingestion Pipeline Guide

## Overview

CloudGuard now supports real-time log streaming from AWS CloudTrail with automatic threat detection. This guide covers the complete pipeline: from CloudTrail events to live UI updates.

## Architecture

```
AWS CloudTrail
      ↓
   S3 Bucket
      ↓
Lambda (parse_cloudtrail.py)
      ↓
Backend /api/logs/ingest (POST)
      ↓
Log Ingestion Service
      ├→ Parse logs
      ├→ Threat Detection
      ├→ Database storage
      └→ WebSocket broadcast
      ↓
Frontend WebSocket (/logs)
      ↓
Real-time UI update
```

## Components

### 1. Lambda Function (`backend/lambda/parse_cloudtrail.py`)

**Purpose**: Triggered by S3 events when CloudTrail logs arrive. Parses and forwards to backend.

**Trigger**: S3 `ObjectCreated` events on CloudTrail S3 bucket

**Key Features**:
- Decompresses gzipped CloudTrail logs
- Extracts relevant fields (user, event, IP, region, etc.)
- Sends logs in batches of 100 to avoid timeouts
- Continues processing even if one batch fails
- Logs to CloudWatch for troubleshooting

**Configuration**:
```python
CLOUDGUARD_API = 'http://backend:5001/api/logs/ingest'  # Update for AWS deployment
BATCH_SIZE = 100
TIMEOUT = 30  # seconds
```

**Payload Example**:
```json
{
  "logs": [
    {
      "timestamp": "2024-08-27T10:15:30Z",
      "user": "alice",
      "event": "GetObject",
      "source": "s3.amazonaws.com",
      "ip": "203.0.113.45",
      "region": "us-east-1",
      "status": "success",
      "resource": "my-bucket",
      "raw": "{...}"
    }
  ],
  "source": "cloudtrail",
  "timestamp": "2024-08-27T10:15:30Z"
}
```

### 2. Backend Log Ingestion Service (`backend/services/log_ingestion.py`)

**Purpose**: Receives CloudTrail logs from Lambda and processes them.

**Key Functions**:
- `LogIngestionService.ingest_logs(logs, source)` - Main entry point
- `parse_log(log_entry, source)` - Route to source-specific parser
- `save_log(log_record)` - Store in database
- `create_alert(log_record, severity, reasons)` - Generate alerts

**Returns**:
```json
{
  "total": 100,
  "processed": 98,
  "alerts": 5,
  "errors": 2
}
```

### 3. REST Endpoint (`backend/routes/live_logs.py`)

**POST /api/logs/ingest**

Receives parsed logs from Lambda. Triggers ingestion pipeline.

**Request**:
```bash
curl -X POST http://localhost:5001/api/logs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [...],
    "source": "cloudtrail"
  }'
```

**Response**:
```json
{
  "status": "ok",
  "count": 98,
  "alerts": 5
}
```

### 4. Threat Detection (`backend/services/detection.py`)

**Purpose**: Analyzes logs against security rules.

**Detection Rules**:
- **Critical**: Root activity, privilege escalation, data exfiltration, data deletion
- **High**: Unauthorized access, policy changes, bulk operations, failed logins
- **Medium**: Account creation, key creation, anomalous IPs
- **Low**: Resource creation

**Function**: `detect_threat_from_log(log_dict)` → `(severity, [reasons])`

**Example**:
```python
log = {
    'event': 'PutUserPolicy',
    'user': 'alice',
    'ip': '203.0.113.45'
}

severity, reasons = detect_threat_from_log(log)
# Returns: ('Critical', ['Potential privilege escalation', ...])
```

### 5. WebSocket Server (`backend/routes/live_logs.py`)

**Namespace**: `/logs`

**Events**:

**From Client:**
- `connect` - Initial connection
- `subscribe` - Start receiving logs with optional filters
- `unsubscribe` - Stop receiving logs
- `filter_update` - Update subscription filters

**From Server:**
- `connected` - Connection acknowledged
- `new_logs` - New logs batch
- `new_alert` - Alert generated
- `ingestion_complete` - Batch processing finished
- `error` - Error message

**Example Client**:
```javascript
const socket = io('http://localhost:5001', {
  path: '/socket.io',
  transports: ['websocket', 'polling']
});

socket.on('connect', () => {
  socket.emit('subscribe', {
    filters: {
      severity: 'Critical',
      user: 'alice'
    }
  });
});

socket.on('new_logs', (data) => {
  console.log('Received logs:', data.logs);
});

socket.on('new_alert', (alert) => {
  console.log('Alert:', alert);
});
```

### 6. Frontend (`frontend/src/pages/Logs.jsx`)

**Features**:
- **Go Live Button** - Enables real-time WebSocket streaming
- **Live Indicator** - Shows connection status
- **Alert Panel** - Displays recent detected threats
- **Real-time Updates** - Logs and alerts appear instantly
- **Search & Filter** - Works with live data

**States**:
- `connected` (🟢) - Live streaming active
- `disconnected` (⚪) - No connection
- `error` (🔴) - Connection failed

## Setup Instructions

### 1. Local Development

No additional setup needed. The system works with the existing `startup.py`:

```bash
python startup.py
```

Then visit `http://localhost:3000` and click "🟢 Go Live" on the Logs page to test WebSocket streaming.

### 2. AWS Deployment

#### Step 1: Configure CloudTrail

```bash
# Create S3 bucket for CloudTrail logs
aws s3 mb s3://cloudtrail-logs-$(date +%s)

# Enable CloudTrail
aws cloudtrail create-trail \
  --name cloudguard-trail \
  --s3-bucket-name cloudtrail-logs-xxx \
  --region us-east-1

# Enable logging
aws cloudtrail start-logging --trail-name cloudguard-trail
```

#### Step 2: Configure Lambda

```bash
# Package Lambda function
cd backend/lambda
zip parse_cloudtrail.zip parse_cloudtrail.py

# Create Lambda function
aws lambda create-function \
  --function-name cloudguard-parse-cloudtrail \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-role \
  --handler parse_cloudtrail.lambda_handler \
  --zip-file fileb://parse_cloudtrail.zip \
  --environment Variables={CLOUDGUARD_API=https://api.cloudguard.example.com/api/logs/ingest}

# Set S3 trigger
aws lambda create-event-source-mapping \
  --event-source arn:aws:s3:::cloudtrail-logs-xxx \
  --function-name cloudguard-parse-cloudtrail \
  --enabled
```

#### Step 3: Update Backend Configuration

```bash
# In docker-compose.yml or ECS task definition
environment:
  - CLOUDGUARD_API_ENDPOINT=http://backend:5001/api/logs/ingest
  - LOG_RETENTION_DAYS=30
```

#### Step 4: Deploy

```bash
# Build and push Docker images
docker-compose build
docker-compose push

# Deploy to ECS
python aws_deploy.py --full --region us-east-1
```

## Database Schema

The logs are stored in the `logs` table:

```sql
CREATE TABLE logs (
  id INTEGER PRIMARY KEY,
  timestamp TEXT NOT NULL,
  user TEXT,
  event TEXT,
  source TEXT,
  ip TEXT,
  region TEXT,
  user_agent TEXT,
  status TEXT,
  error_code TEXT,
  resource TEXT,
  raw_data TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Monitoring

### CloudWatch Logs

Lambda logs to `/aws/lambda/cloudguard-parse-cloudtrail`:

```bash
aws logs tail /aws/lambda/cloudguard-parse-cloudtrail --follow
```

### Backend Logs

Check backend container logs:

```bash
# Docker
docker logs cloudguard-backend

# ECS
aws logs tail /ecs/cloudguard-backend --follow
```

### WebSocket Connections

Monitor active connections:

```bash
# In backend logs, look for:
# - "Client connected to /logs: <session_id>"
# - "Client subscribed with filters: {...}"
# - "Client disconnected from /logs: <session_id>"
```

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/test_log_pipeline.py -v
```

### Manual Test: Ingest Logs

```bash
curl -X POST http://localhost:5001/api/logs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {
        "timestamp": "2024-08-27T10:15:30Z",
        "user": "alice",
        "event": "PutUserPolicy",
        "source": "iam.amazonaws.com",
        "ip": "203.0.113.45",
        "region": "us-east-1",
        "status": "success",
        "resource": "arn:aws:iam::123456789012:user/alice"
      }
    ],
    "source": "cloudtrail"
  }'
```

### Manual Test: WebSocket Connection

```bash
# Using wscat
npm install -g wscat
wscat -c ws://localhost:5001/logs

# Then send subscribe command
{"event": "subscribe", "data": {"filters": {}}}
```

## Troubleshooting

### WebSocket Connection Fails

1. Verify backend is running: `curl http://localhost:5001/api/stats`
2. Check firewall allows WebSocket on port 5001
3. Verify Socket.IO path in frontend matches backend
4. Check browser console for connection errors

### Logs Not Appearing

1. Check Lambda function logs in CloudWatch
2. Verify CloudTrail is configured and logging
3. Check backend database has logs table
4. Verify API endpoint in Lambda is correct

### Alerts Not Detected

1. Verify log event names match detection rules
2. Check detection.py rule keywords
3. Review backend logs for detection errors
4. Test with `curl` to verify ingestion endpoint works

### Performance Issues

1. Reduce BATCH_SIZE in Lambda if timeouts occur
2. Increase backend workers: `WORKERS=8` in config
3. Enable database connection pooling
4. Monitor database query performance

## Scaling

### Horizontal Scaling

1. Deploy multiple backend instances
2. Use load balancer (ALB) to distribute traffic
3. Use Redis for WebSocket session management

### Vertical Scaling

1. Increase Lambda memory: 256MB → 512MB
2. Increase backend task CPU/memory in ECS
3. Upgrade database instance class

## Security Considerations

1. **API Authentication**: Add API key or OAuth to `/api/logs/ingest`
2. **HTTPS**: Use TLS for WebSocket connections
3. **Rate Limiting**: Implement rate limiting on ingest endpoint
4. **Data Retention**: Implement log retention policy (e.g., 30 days)
5. **IAM Permissions**: Restrict Lambda S3 access to specific bucket
6. **Network**: Use VPC endpoints for internal Lambda-to-Backend communication

## Next Steps

1. Test with real CloudTrail logs in AWS
2. Implement custom detection rules for your environment
3. Add alerting integrations (Slack, PagerDuty, etc.)
4. Set up CloudWatch dashboards for monitoring
5. Configure auto-scaling policies
6. Implement log encryption and compliance features

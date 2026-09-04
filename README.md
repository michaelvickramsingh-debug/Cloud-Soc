# Cloud Detection and Response — Survival Guide for the SOC
### An Interactive Simulation Tool & Dashboard with AWS-Powered Live Backend
> Based on the CrowdStrike Whitepaper: *Cloud Detection and Response Survival Guide for the SOC*

---

## 🎯 Project Status

**Current State**: Fully functional AWS-backed Cloud Detection & Response (CDR) platform  
**Deployment**: Live on AWS (API Gateway + ECS + PostgreSQL + CloudTrail + Lambda)  
**Last Updated**: September 4, 2026

### ✅ What's Working
- Real-time AWS CloudTrail ingestion via S3 → Lambda → ECS backend
- PostgreSQL database for production-grade persistence
- Live log streaming with WebSocket support
- 5 attack scenario simulations with MITRE ATT&CK mapping
- Prowler CSPM integration with one-click scan + ingest
- Alert generation and triage workflow
- Attack timeline reconstruction
- Dashboard metrics and statistics
- One-click launcher for demos (`./start.sh`)

---

## 👥 Team
- **Member 1** — Backend (Python, Flask, Simulation Engine, Detection Rules, AWS Infrastructure)
- **Member 2** — Frontend (React, Dashboard, Pages, Charts)

---

## 🏗️ Architecture

### Production Architecture (AWS)
```
┌─────────────────┐
│  AWS CloudTrail │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   S3 Bucket     │ ← CloudTrail logs land here
└────────┬────────┘
         │ (S3 Event Notification)
         ▼
┌─────────────────┐
│ Lambda Function │ ← parse_cloudtrail.py
│ (Parser)        │   Reads S3, extracts events
└────────┬────────┘
         │ (HTTPS POST)
         ▼
┌─────────────────┐
│  API Gateway    │ ← HTTPS endpoint (public)
└────────┬────────┘
         │ (VPC Link)
         ▼
┌─────────────────┐
│  Internal ALB   │ ← Private load balancer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ECS Fargate    │ ← Flask backend container
│  (Backend API)  │   - Log ingestion
└────────┬────────┘   - Detection engine
         │            - Prowler scanner
         ▼
┌─────────────────┐
│  RDS PostgreSQL │ ← Production database
└─────────────────┘
         ▲
         │ (reads/writes)
┌────────┴────────┐
│  React Frontend │ ← Local or hosted dashboard
│  (localhost)    │   Connects via API Gateway
└─────────────────┘
```

### Key Components

**Data Ingestion Pipeline**
- CloudTrail captures all AWS API activity
- S3 stores logs and triggers Lambda
- Lambda parses and forwards to backend
- Backend detection engine analyzes events
- Alerts and logs stored in PostgreSQL

**Detection Engine**
- 15+ detection rules for IOA (Indicators of Attack)
- MITRE ATT&CK technique mapping
- Severity classification (Critical/High/Medium/Low)
- Real-time alert generation

**Prowler Integration**
- One-click scan execution from UI
- Automatic IOM (Indicator of Misconfiguration) ingestion
- Compliance posture tracking
- Remediation guidance

**Frontend Dashboard**
- Live log streaming (WebSocket with polling fallback)
- Alert triage and resolution
- Attack timeline visualization
- MITRE technique mapping
- Prowler findings with scan log viewer

---

## 📁 Project Structure

```
cloudguard/
├── backend/
│   ├── app.py                      ← Flask entry point
│   ├── config.py                   ← Environment config (DB, API keys, CORS)
│   ├── requirements.txt            ← Python deps (includes Prowler 5.12.2)
│   ├── Dockerfile                  ← Multi-stage build for ECS (ARM64)
│   ├── database/
│   │   ├── database.py             ← SQLite + PostgreSQL compatibility layer
│   │   ├── schema.sql              ← SQLite schema (local dev)
│   │   ├── schema.postgresql.sql   ← PostgreSQL schema (production)
│   │   └── migrations.postgresql.sql ← Schema migrations for RDS
│   ├── lambda/
│   │   ├── parse_cloudtrail.py     ← CloudTrail log parser (Lambda function)
│   │   └── build_deployment_package.sh ← Lambda packaging script
│   ├── models/
│   │   ├── alert.py                ← Alert model (IOA + IOM)
│   │   └── log.py                  ← Cloud log model
│   ├── routes/
│   │   ├── api.py                  ← Blueprint registry
│   │   ├── alerts.py               ← GET /api/alerts, resolve endpoints
│   │   ├── logs.py                 ← GET /api/logs, timeline
│   │   ├── live_logs.py            ← WebSocket + /api/logs/ingest
│   │   ├── stats.py                ← Stats, metrics, simulate, practices
│   │   └── prowler.py              ← Prowler scan + ingest + summary
│   ├── services/
│   │   ├── detection.py            ← Threat detection engine
│   │   ├── simulation.py           ← 5 attack scenario generators
│   │   ├── log_ingestion.py        ← Live log processing
│   │   └── prowler.py              ← Prowler output parser
│   ├── utils/
│   │   ├── helpers.py              ← Shared utilities
│   │   └── logger.py               ← Logging setup
│   ├── tests/                      ← pytest suite
│   └── data/                       ← Runtime output (prowler_output.json)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js              ← Dev server + API proxy config
│   ├── .env.local                  ← VITE_API_URL + VITE_SOCKET_URL
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                 ← Router + layout
│       ├── components/
│       │   └── layout/
│       │       └── Sidebar.jsx
│       ├── utils/
│       │   └── api.js              ← API client (AWS default)
│       └── pages/
│           ├── Home.jsx            ← Dashboard stats + navigation
│           ├── WhyCloud.jsx        ← Attack surface explainer
│           ├── BestPractice.jsx    ← 5 BP pages + simulation triggers
│           ├── Alerts.jsx          ← Alert triage dashboard
│           ├── Logs.jsx            ← Live log viewer with Go Live
│           ├── Timeline.jsx        ← Attack chain reconstruction
│           ├── Mitre.jsx           ← MITRE ATT&CK technique map
│           └── Prowler.jsx         ← CSPM findings + scan button + log
│
├── startup.py                      ← One-click launcher (Python)
├── start.sh                        ← One-click launcher (Bash, AWS mode)
└── README.md                       ← This file
```

---

## 🔴 LIVE LOG INGESTION

CloudGuard now supports **real-time log streaming from AWS CloudTrail** with automatic threat detection. See [LIVE_LOG_INGESTION_GUIDE.md](LIVE_LOG_INGESTION_GUIDE.md) for complete setup.

### Quick Features:
- **WebSocket Streaming**: Real-time logs appear in the dashboard as they occur
- **Threat Detection**: Automatic analysis against 15+ security rules
- **Alert Broadcast**: Critical/High severity events trigger instant alerts
- **Lambda Integration**: Serverless log parsing from CloudTrail S3 bucket
- **Batch Processing**: Efficient handling of large log volumes (100 logs/batch)
- **Live Dashboard**: "Go Live" button on Logs page enables real-time view

### Architecture:
```
CloudTrail S3 → Lambda Function → Backend /api/logs/ingest → 
Threat Detection → WebSocket Broadcast → Frontend Real-time UI
```

---

## 🚀 How to Run

### 🎯 Quick Start — One Click (AWS Live Mode)
```bash
./start.sh
```

This launches the frontend in **AWS live mode**:
- ✅ Kills any processes on ports 3000 and 5001
- ✅ Installs frontend dependencies if needed
- ✅ Starts frontend on http://localhost:3000
- ✅ Connects to live AWS backend automatically
- ✅ Opens dashboard in your browser
- ✅ Ready to run simulations and scans

**Default behavior**: Connects to production AWS backend (API Gateway + ECS + PostgreSQL)

---

### 🔧 Local Development Mode

If you need to run the backend locally (for development/debugging):

```bash
python3 startup.py --local-backend
```

This starts both:
- Backend (Flask) on http://127.0.0.1:5001
- Frontend (React) on http://127.0.0.1:3000
- Uses local SQLite database

---

### 📋 Manual Setup (Advanced)

#### Backend Only
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Backend API: **http://127.0.0.1:5001/api**

#### Frontend Only (AWS Live Backend)
```bash
cd frontend
npm install
npm run dev
```
Frontend: **http://127.0.0.1:3000**  
Backend: Uses AWS live API (from `.env.local`)

---

### ☁️ AWS Backend Endpoint

**Production API**: https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com/api

The frontend connects to this by default. No local backend needed for demos.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard summary numbers |
| GET | `/api/logs` | All cloud logs |
| GET | `/api/logs/timeline/<scenario_id>` | Log timeline for a scenario |
| POST | `/api/logs/ingest` | Ingest CloudTrail logs from Lambda |
| GET | `/api/logs/stream/status` | WebSocket streaming status |
| GET | `/api/alerts` | All alerts |
| GET | `/api/alerts/summary` | Alert count by severity |
| PUT | `/api/alerts/<id>/resolve` | Resolve an alert |
| GET | `/api/scenarios` | All 5 attack scenarios |
| POST | `/api/simulate/<id>` | Run attack simulation (1–5) |
| GET | `/api/metrics` | Aggregate detection metrics |
| GET | `/api/mitre` | MITRE ATT&CK mapping |
| POST | `/api/reset` | Reset logs & alerts to a clean state |
| POST | `/api/prowler/scan` | **One-click Prowler scan** — runs scan + auto-ingests results |
| POST | `/api/prowler/ingest` | Ingest a Prowler scan result file |
| GET | `/api/prowler/summary` | Summary of ingested Prowler findings |
| GET | `/api/prowler/scan/log` | Get stdout/stderr from last scan |
| GET | `/api/practices` | Best Practice guide content for simulation pages |
| WebSocket | `/logs` | Real-time log and alert streaming (polling-first)

---

## 🎯 5 Attack Scenarios

| ID | Name | Best Practice | Key Attack Vector |
|----|------|--------------|-------------------|
| 1 | Cross-Domain Attack | Threat Intelligence | Endpoint → Identity → Cloud |
| 2 | IAM Privilege Escalation | Control Plane Context | API Abuse + IAM Manipulation |
| 3 | Fileless Malware | Runtime Protection | In-Memory Container Execution |
| 4 | Unusual Login + Exfiltration | Cloud Expertise | Valid Account Abuse |
| 5 | Multi-Cloud Lateral Movement | Automation | Token Theft across AWS/Azure/GCP |

---

## 📚 Whitepaper Mapping

This project directly implements concepts from:
> **"Cloud Detection and Response Survival Guide for the SOC"** — CrowdStrike White Paper

| Feature | Whitepaper Section |
|---------|-------------------|
| Attack Surface Visualizer | "Why Is the Cloud a Prime Target?" |
| Threat Stats Panel | CrowdStrike 2025 Global Threat Report data |
| Cloud vs Endpoint Compare | "From Endpoints to Cloud: Recognizing the New Attack Surface" |
| BP1 Threat Intelligence Simulator | "Build a Foundation on Threat Intelligence" |
| BP2 Log Correlation Workbench | "Enrich Investigations with Cloud Control Plane Context" |
| BP3 Fileless Malware Demo | "Complement Detection and Response with Runtime Workload Protection" |
| BP4 Alert Triage Comparison | "Leverage Cloud Expertise to Bridge Knowledge Gaps" |
| BP5 Automated Playbook | "Automate and Scale Response Actions Across Multi-Cloud Environments" |
| IOA / IOM Detection Engine | "Cloud IOAs and IOMs" — Falcon Cloud Security |

---

## 🎬 Demo Checklist for Reviewers

### Pre-Demo Setup
1. ✅ Run `./start.sh` (opens browser automatically)
2. ✅ Verify dashboard loads with live stats
3. ✅ Check "Go Live" status shows "Connected"

### Simulation Demo Flow
1. **Navigate to BP2 · IAM Escalation** (or any Best Practice page)
2. **Click "Run Simulation"**
   - Watch logs populate in real-time
   - See attack chain unfold
3. **Go to Alerts page**
   - Critical alerts appear immediately
   - Show severity, type, status
4. **Go to Attack Timeline**
   - See chronological attack sequence
   - Explain the attacker's path
5. **Go to MITRE ATT&CK**
   - Show technique mapping
   - Explain T1078, T1484, T1562, etc.
6. **Go to Logs page**
   - Click "🟢 Go Live"
   - Show real CloudTrail events streaming
   - Search/filter logs

### Prowler Scan Demo
1. **Navigate to Prowler Findings**
2. **Click "🔍 Run Prowler Scan"**
   - Wait for scan to complete (30s - 2min)
   - Show scan log output
3. **Review findings**
   - Severity breakdown
   - Resource and region info
   - Remediation guidance
4. **Toggle "Show scan log"**
   - Show raw Prowler CLI output
   - Explain compliance checks

### Key Talking Points
- **Dual data sources**: CloudTrail (runtime IOA) + Prowler (configuration IOM)
- **Real-time detection**: Sub-second alert generation from live events
- **MITRE mapping**: Industry-standard attack technique classification
- **Production architecture**: Fully deployed on AWS with private networking
- **One-click demos**: No manual setup needed for reviewers

---

## 🔧 Technical Stack

### Backend
- **Framework**: Flask 3.0 (Python 3.9)
- **Database**: PostgreSQL (production) / SQLite (local dev)
- **Real-time**: Flask-SocketIO with Eventlet
- **Cloud SDK**: boto3 (AWS), Prowler 5.12.2 (CSPM)
- **Deployment**: Docker → ECR → ECS Fargate (ARM64)

### Frontend
- **Framework**: React 18.2
- **Build Tool**: Vite 4.4
- **Real-time**: Socket.IO client
- **Styling**: Inline CSS (dark theme)

### AWS Services
- **Compute**: ECS Fargate (ARM64 Graviton)
- **API**: API Gateway (HTTP API + VPC Link)
- **Network**: Internal ALB, private subnets
- **Database**: RDS PostgreSQL
- **Storage**: S3 (CloudTrail logs)
- **Serverless**: Lambda (log parser)
- **Secrets**: Secrets Manager (DB credentials, API keys)
- **Monitoring**: CloudWatch Logs

---

## 📊 Current Metrics (as of Sep 4, 2026)

- **Total CloudTrail logs ingested**: 6,800+ (growing in real-time)
- **Attack scenarios**: 5 distinct scenarios
- **Detection rules**: 15+ IOA patterns
- **MITRE techniques mapped**: 20+
- **Prowler checks**: 1,000+ available (on-demand scanning)
- **API uptime**: 99.9% (ECS health checks)

---

## 🐛 Known Issues & Limitations

1. **WebSocket Transport**: API Gateway HTTP API doesn't support raw WebSocket upgrades. Frontend uses HTTP long-polling with opportunistic upgrade.
2. **Scan Duration**: Full Prowler scans (1000+ checks) can take 10-30 minutes. Use selective checks for faster demos.
3. **Docker Desktop**: Local Docker builds may experience DNS flakiness. Use `crane` for ECR pushes as workaround.
4. **TLS Interception**: Some corporate networks intercept TLS. Set `AWS_CA_BUNDLE=/tmp/combined-ca-bundle.pem` if needed.

---

## 🚧 Future Enhancements

- [ ] Public frontend hosting (S3 + CloudFront)
- [ ] Multi-account CloudTrail aggregation
- [ ] Slack/PagerDuty alert notifications
- [ ] Custom detection rule editor
- [ ] Historical trend analysis
- [ ] Automated remediation playbooks
- [ ] Integration with SIEM platforms

---

## 📝 Handoff Notes

### For Next Developer

**State of the Project**:
- Core ingestion pipeline is stable and production-ready
- All major bugs fixed (schema, metrics, WebSocket, MITRE)
- Prowler integration complete with one-click UX
- Documentation is up-to-date

**What to Watch**:
- Docker builds are slow due to Prowler's heavy dependencies (~200MB)
- Network flakiness on this machine requires `AWS_CA_BUNDLE` workaround
- ECS task definition is currently at revision 8 (includes Prowler)

**Quick Commands**:
```bash
# Start app (AWS live mode)
./start.sh

# Start app (local backend mode)
python3 startup.py --local-backend

# Test live backend
curl https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com/api/stats

# Run Prowler scan via API
curl -X POST https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com/api/prowler/scan \
  -H 'Content-Type: application/json' \
  -d '{"checks":["iam_root_mfa_enabled"]}'

# Rebuild and deploy backend
cd backend
docker build --platform linux/arm64 -t cloudguard-backend:latest .
docker save cloudguard-backend:latest -o /tmp/backend.tar
crane push /tmp/backend.tar <ECR_REPO>:latest
aws ecs update-service --cluster cloudguard-cluster --service cloudguard-backend --force-new-deployment
```

**Database Access**:
- Connection string is in AWS Secrets Manager: `cloudguard/production/database-url`
- Use `psql` or any PostgreSQL client with the DATABASE_URL

**Lambda Deployment**:
- Use `backend/lambda/build_deployment_package.sh` to package
- Upload to S3: `s3://cloudtrail-logs-cloudguard-1788151327/lambda/deployment.zip`
- Update Lambda function via AWS CLI or console

---

**Last Updated**: September 4, 2026  
**Version**: 1.0.0 (Production)  
**Status**: ✅ Operational

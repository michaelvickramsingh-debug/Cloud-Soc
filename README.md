# Cloud Detection and Response — Survival Guide for the SOC
### An Interactive Simulation Tool & Dashboard
> Based on the CrowdStrike Whitepaper: *Cloud Detection and Response Survival Guide for the SOC*

---

## 👥 Team
- **Member 1** — Backend (Python, Flask, Simulation Engine, Detection Rules)
- **Member 2** — Frontend (React, Dashboard, Pages, Charts)

---

## 🏗️ Project Structure

```
cloudguard/
├── backend/
│   ├── app.py                  ← Flask entry point (run this)
│   ├── config.py               ← Central config, loaded from .env
│   ├── requirements.txt        ← Python dependencies
│   ├── conftest.py             ← pytest path setup
│   ├── database/
│   │   ├── database.py         ← Connection, init_db(), reset_db()
│   │   └── schema.sql          ← Table definitions + seed data
│   ├── models/
│   │   ├── alert.py            ← Alert record shape
│   │   └── log.py              ← Log record shape
│   ├── routes/
│   │   ├── api.py              ← Registers all blueprints under /api
│   │   ├── alerts.py
│   │   ├── logs.py
│   │   ├── stats.py
│   │   └── prowler.py
│   ├── services/
│   │   ├── detection.py        ← IOA/IOM detection rules
│   │   ├── simulation.py       ← Log generator / attack scenarios
│   │   └── prowler.py          ← Prowler scan ingestion
│   ├── utils/
│   │   ├── helpers.py
│   │   └── logger.py
│   ├── tests/                  ← pytest suite
│   └── data/                   ← Runtime output (e.g. prowler_output.json)
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx             ← Routing & layout
        ├── components/
        │   └── layout/
        │       └── Sidebar.jsx ← Navigation sidebar
        ├── utils/
        │   └── api.js          ← Shared fetch helper
        └── pages/
            ├── Home.jsx        ← Overview dashboard + stats
            ├── WhyCloud.jsx    ← Section 1: Attack surface + stats
            ├── BestPractice.jsx← Section 2: BP explainer + simulator
            ├── Alerts.jsx      ← Live alerts with filters + resolve
            ├── Logs.jsx        ← Cloud log viewer with search
            └── Prowler.jsx     ← Prowler scan results view
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

## 🚀 HOW TO RUN

### 🎯 Quick Start (Recommended) — One Click!
```bash
python startup.py
```
This launches everything automatically:
- ✅ Starts backend (Flask) on http://127.0.0.1:5001
- ✅ Starts frontend (React) on http://127.0.0.1:3000
- ✅ Opens dashboard in your browser
- ✅ Shows service status

**See [QUICKSTART.md](QUICKSTART.md) for full details & troubleshooting**

---

### 📋 Manual Setup (for development)

#### Step 1 — Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Backend API: **http://127.0.0.1:5001/api**

#### Step 2 — Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend: **http://127.0.0.1:3000**

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
| POST | `/api/prowler/ingest` | Ingest a Prowler scan result |
| GET | `/api/prowler/summary` | Summary of ingested Prowler findings |
| WebSocket | `/logs` | Real-time log and alert streaming

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

# CloudGuard — Cloud Detection and Response Simulation Platform

> A full-stack CDR simulation platform built for the SOC.  
> Based on the CrowdStrike *Cloud Detection and Response Survival Guide for the SOC* white paper.

---

## 👥 Team

| Role | Responsibility |
|------|---------------|
| Member 1 | Backend — Python, Flask, Simulation Engine, Detection Rules, Database |
| Member 2 | Frontend — React, SOC Dashboard, Pages, Charts |

---

## 🏗️ Project Structure

```
Cloud-Soc/
│
├── backend/
│   ├── app.py                        ← Flask entry point — run this
│   ├── config.py                     ← All settings loaded from .env
│   ├── requirements.txt              ← Python dependencies
│   ├── .env                          ← Environment variables (never committed)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py               ← get_db(), init_db(), reset_db()
│   │   └── schema.sql                ← SQL table definitions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── log.py                    ← Log dataclass (one cloud event)
│   │   └── alert.py                  ← Alert dataclass (one detection result)
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py                    ← Master blueprint — registers all routes
│   │   ├── logs.py                   ← GET /api/logs, GET /api/logs/timeline/<id>
│   │   ├── alerts.py                 ← GET /api/alerts, PUT /api/alerts/<id>/resolve
│   │   └── stats.py                  ← stats, metrics, simulate, mitre, reset
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── simulation.py             ← Attack scenario generators (red team)
│   │   ├── detection.py              ← IOA/IOM rule engine (blue team)
│   │   └── prowler.py                ← Prowler CSPM findings ingestion [coming soon]
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                 ← Centralised logging
│   │   └── helpers.py                ← Shared utilities (timestamps, safe_divide)
│   │
│   └── tests/
│       ├── __init__.py
│       └── test_simulation.py        ← 40 pytest tests — all passing
│
├── frontend/                         ← React + Vite [in progress]
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       └── pages/
│
├── .gitignore
└── README.md
```

---

## 🚀 How to Run

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend runs at: **http://localhost:5000**

### Frontend (coming soon)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: **http://localhost:3000**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard summary numbers |
| GET | `/api/logs` | All cloud logs, newest first |
| GET | `/api/logs/timeline/<id>` | Chronological attack sequence with time deltas |
| GET | `/api/alerts` | All alerts |
| GET | `/api/alerts/summary` | Alert count grouped by severity |
| PUT | `/api/alerts/<id>/resolve` | Mark one alert as Resolved |
| GET | `/api/scenarios` | All 5 attack scenario definitions |
| POST | `/api/simulate/<id>` | Run attack simulation (1–5) |
| GET | `/api/metrics` | Detection rate, FPR, per-scenario breakdown |
| GET | `/api/mitre` | Scenario → MITRE ATT&CK technique mapping |
| POST | `/api/reset` | Wipe logs and alerts (keep scenarios) |

---

## 🎯 5 Attack Scenarios

| ID | Name | MITRE Tactic Chain | Best Practice |
|----|------|--------------------|---------------|
| 1 | Cross-Domain Attack | Initial Access → Credential Access → Exfiltration | BP1: Adversary-Led Approach |
| 2 | IAM Privilege Escalation | Initial Access → Privilege Escalation → Defense Evasion → Persistence | BP2: Real-Time Detections |
| 3 | Fileless Malware in Container | Execution → Defense Evasion | BP3: Unified Cloud Context |
| 4 | Unusual Login + Data Exfiltration | Initial Access → Discovery → Exfiltration | BP4: Automate Response |
| 5 | Multi-Cloud Lateral Movement | Credential Access → Lateral Movement → Impact | BP5: Cloud Expertise |

---

## 🔍 Detection Engine

### IOA Rules (Indicators of Attack) — 16 rules
Runtime behavioural signals that fire when an attacker action is detected in a log entry.

| Rule | Trigger Keyword | Severity | MITRE Technique |
|------|----------------|----------|-----------------|
| Cloud Token Theft | `stolen token` | Critical | T1528 |
| CloudTrail Disabled | `logging disabled` | Critical | T1562.008 |
| Backdoor Account Created | `backdoor` | Critical | T1098.001 |
| Admin Policy Attached | `administratoraccess` | Critical | T1484.001 |
| Reverse Shell Detected | `reverse shell` | Critical | T1059.004 |
| Fileless Malware | `in-memory payload` | Critical | T1620 |
| Unusual Region Login | `unusual region` | High | T1078.004 |
| Cross-Cloud Pivot | `pivot` | Critical | T1550.001 |
| Abnormal Data Volume | `45 gb` | Critical | T1537 |
| MFA Bypass | `mfa challenge bypassed` | Critical | T1078.004 |
| Malware on Endpoint | `malware execution` | High | T1566 |
| Credential Dumping | `credential dumping` | Critical | T1528 |
| Pipe Execution in Container | `curl \| bash` | Critical | T1059.004 |
| Cryptominer Deployed | `cryptomining` | Critical | T1496 |
| Unauthenticated API Access | `unauthenticated access` | High | T1190 |
| Federated Token Abuse | `federated trust` | Critical | T1550.001 |

### IOM Rules (Indicators of Misconfiguration) — 3 rules
Posture signals that surface the misconfigurations attackers exploit.

| Rule | Trigger Keyword | Severity |
|------|----------------|----------|
| Container from Unverified Registry | `unverified external registry` | Medium |
| Secrets in Environment Variables | `environment variables` | High |
| Unauthenticated Endpoint Exposed | `unauthenticated` | High |

---

## 🗄️ Database Schema

### Tables
| Table | Purpose |
|-------|---------|
| `cloud_logs` | Simulated CloudTrail-style events — malicious and benign |
| `alerts` | IOA/IOM detection results with MITRE mapping |
| `attack_scenarios` | Seed data for all 5 scenarios |

### Key Fields
- `cloud_logs.is_malicious` — 1 = attacker action, 0 = benign background traffic
- `cloud_logs.mitre_technique` — e.g. T1484.001
- `alerts.type` — IOA (runtime) or IOM (misconfiguration)
- `alerts.related_log_id` — FK linking every alert back to the log that triggered it

---

## 🔗 Prowler Integration (In Progress)

CloudGuard integrates with **Prowler** — an open-source CSPM tool that runs 1,000+ security checks against real AWS accounts.

| | CloudGuard | Prowler |
|-|-----------|---------|
| Finding type | IOA (runtime attack simulation) | IOM (real AWS misconfigurations) |
| Data source | Synthetic CloudTrail-style logs | Real AWS account scan |
| Output | Alerts in SQLite DB | JSON-OCSF findings |
| Integration | `services/prowler.py` ingests Prowler JSON → IOM alerts |

---

## 📚 Whitepaper Mapping

> Based on: **"Cloud Detection and Response Survival Guide for the SOC"** — CrowdStrike (2026)

| CloudGuard Feature | White Paper Section |
|--------------------|---------------------|
| 5 attack scenarios | "Attackers Are Zeroing In on the Cloud" |
| IOA detection engine | "Implement Real-Time, Cloud-Native Detections" |
| Timeline endpoint | "Accelerate Investigations with Unified Cloud Context" |
| SOAR-style reset + resolve | "Automate and Scale Response Across Cloud Environments" |
| Prowler integration | "Security Posture Management" — IOM gap |
| `/api/metrics` detection rate | Original research contribution — reproducible CDR benchmark |
| MITRE ATT&CK mapping | All 10 cloud tactics across 5 scenarios |

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

Expected output: **40 passed** across scenario tests, detection tests, reset test, and edge case tests.

---

## 🗓️ Development Roadmap

| Phase | Focus | Timeline | Status |
|-------|-------|----------|--------|
| A | Backend scaffold — DB, models, services, routes, tests | Jul 2026 | ✅ Complete |
| B | Prowler integration + industry expert tweaks | Jul 2026 | 🔄 In Progress |
| C | React frontend — all SOC dashboard pages | Aug 2026 | ⏳ Upcoming |
| D | AWS free tier labs + real Prowler scan | Aug–Sep 2026 | ⏳ Upcoming |
| E | Research paper writing | Sep–Oct 2026 | ⏳ Upcoming |
| F | Final review + university submission | Oct 2026 | ⏳ Upcoming |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.0.0, Flask-CORS 4.0.0 |
| Database | SQLite 3 (via Python standard library) |
| Config | python-dotenv 1.0.0 |
| Testing | pytest |
| Frontend | React 18, Vite 5 |
| CSPM Integration | Prowler (open-source) |
| Framework | MITRE ATT&CK for Cloud (IaaS) |
| Reference | CrowdStrike CDR Survival Guide for the SOC (2026) |

---

*Master of Artificial Intelligence and Cyber Security — CHRIST (Deemed to be University), Bangalore Yeshwanthpur Campus — Academic Year 2025–2026*

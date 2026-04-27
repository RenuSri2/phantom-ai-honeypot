# 🕵️ PHANTOM — AI-Powered Honeypot Deception System

[![PHANTOM](https://img.shields.io/badge/PHANTOM-AI%20Honeypot%20System-red?style=for-the-badge&logo=ghost&logoColor=white)](https://phantom-hack2skill.web.app)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run%20%7C%20Vertex%20AI-4285F4?style=flat-square&logo=googlecloud&logoColor=white)](https://cloud.google.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI%20Powered-8E44AD?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org/)
[![Firebase](https://img.shields.io/badge/Firebase-Realtime%20DB-FFCA28?style=flat-square&logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=flat-square&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

> **PHANTOM doesn't just detect cyberattacks — it traps, deceives, and studies them.**

A 5-layer cloud-native AI deception platform that lures attackers into a fully AI-generated fake corporate environment, uses Reinforcement Learning to keep them engaged, and automatically produces professional MITRE ATT&CK threat intelligence reports.

---

## 🧠 The Problem We Solve

Traditional cybersecurity tools **block** attackers. PHANTOM does something smarter — it **welcomes** them into a convincing trap, studies everything they do, and turns their attack into actionable intelligence.

Most honeypots are static and easy to fingerprint. PHANTOM is **dynamic** — every attacker gets a unique, AI-generated fake company with realistic employees, databases, fake AWS credentials, and git histories. The attacker thinks they're winning. They're not. They're teaching us.

---

## 🎯 Key Highlights

- 🤖 **Gemini-Powered Deception** — Vertex AI Gemini generates a fully coherent fake corporate identity in real-time (staff profiles, internal databases, fake secrets)
- 🧬 **Reinforcement Learning Defense** — A sub-100ms RL agent decides what fake data to feed the attacker at every step to maximize engagement time
- 🌍 **Real-Time Attack Visualization** — React dashboard with live world map, threat score, and attack timeline
- 📄 **MITRE ATT&CK Mapped Reports** — Auto-generated PDF threat intelligence reports with Gemini-written executive summaries
- ☁️ **Fully Cloud-Native** — Deployed on Google Cloud Run with Terraform IaC, Firebase Realtime DB, and Cloud Pub/Sub
- 🔬 **Behavioral Profiling** — Classifies attackers as Script Kiddie, APT, Opportunist, or Insider Threat

---

## 🏗️ Architecture

PHANTOM is built as a **5-layer microservices pipeline**, each deployed as an independent Google Cloud Run service:

```
                    ┌─────────────────────────────┐
                    │      Attacker (Internet)     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  LAYER 1: Honeypot & Trap   │
                    │  Flask app — fake vulnerable │
                    │  APIs + Isolation Forest     │
                    │  anomaly detection           │
                    │  Emits events to Pub/Sub     │
                    └──────────────┬──────────────┘
                                   │
          ┌────────────────────────┼──────────────────────┐
          │                        │                       │
┌─────────▼────────┐   ┌──────────▼──────────┐  ┌────────▼────────┐
│  LAYER 2:        │   │  LAYER 3: RL Agent  │  │  LAYER 4:       │
│  Company Bible   │   │  Sub-100ms decisions│  │  Behavioral     │
│  Gemini generates│   │  Adaptive deception │  │  Analysis       │
│  fake corporate  │   │  strategy per action│  │  Intent + Skill │
│  identity        │   │                     │  │  classification │
└──────────────────┘   └─────────────────────┘  └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────▼────────┐
                    │  LAYER 5: Threat Intelligence Reports         │
                    │  ReportLab PDF + Gemini executive summary     │
                    │  MITRE ATT&CK framework mapping               │
                    └─────────────────────────────────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────▼────────┐
                    │  FRONTEND: React + Firebase                   │
                    │  Real-time attack feed, world map,            │
                    │  threat score meter, RL agent panel,          │
                    │  one-click PDF report download                │
                    └──────────────────────────────────────────────┘
```

### Layer Breakdown

| Layer | Service | Technology | Purpose |
|-------|---------|------------|---------|
| 1 | Honeypot & Trap | Flask, Isolation Forest | Exposes fake vulnerable endpoints, detects anomalies |
| 2 | Company Bible | Vertex AI Gemini | Generates a coherent fake corporate identity on demand |
| 3 | RL Decision Agent | Python, Rule-based RL | Decides what fake data to serve in under 100ms |
| 4 | Behavioral Analysis | Vertex AI Gemini | Classifies attacker intent and skill level |
| 5 | Report Generator | ReportLab, Gemini | Produces MITRE ATT&CK-mapped PDF threat intel reports |
| — | Frontend | React, Vite, Firebase | Real-time dashboard for live attack visualization |
| — | Infrastructure | Terraform, GCP | Cloud Run, Pub/Sub, Cloud Storage, Firebase RTDB |

---

## ✨ Features

### 🎭 Dynamic Deception Engine
- Every session generates a **unique fake company** with a believable identity
- Fake employee directories, org charts, internal memos, and database schemas
- Convincing fake credentials (AWS keys, SSH keys, git tokens) that go nowhere
- AI-generated content means no two honeypots ever look the same

### 🤖 Reinforcement Learning Defense
- Rule-based RL policy makes real-time decisions on what to serve the attacker
- Adapts deception strategy based on attacker behavior patterns
- Maximizes attacker engagement time — more time means better intelligence gathered
- Sub-100ms decision latency keeps the attacker completely unaware

### 🔍 Attacker Profiling
- **Intent Classification**: Data Theft, Sabotage, Ransomware, Reconnaissance, Insider Threat
- **Skill Level Assessment**: Script Kiddie → Opportunist → Skilled Attacker → APT
- **Geolocation tracking** with IP reputation lookup via AbuseIPDB
- Behavioral fingerprinting across the entire session

### 📊 Real-Time Dashboard
- **Live Attack Feed** — every malicious action streamed in real-time via Firebase
- **World Map** — geographic visualization of attacker origin
- **Threat Score Meter** — dynamic risk score updated live throughout the session
- **RL Agent Panel** — shows the agent's decision reasoning in real-time
- **Attacker Profile Card** — intent, skill level, and full session metadata

### 📄 Threat Intelligence Reports
- Professional dark-themed PDF reports generated automatically per session
- **Executive Summary** written by Gemini AI
- **Full MITRE ATT&CK framework mapping** of observed TTPs
- Complete attack timeline with timestamped events
- One-click download directly from the dashboard

### ☁️ Cloud-Native Infrastructure
- All services containerized and deployed on **Google Cloud Run** (auto-scaling, serverless)
- **Cloud Pub/Sub** for reliable inter-service event streaming
- **Firebase Realtime Database** for sub-second frontend updates
- **Cloud Storage** for report persistence
- **Terraform** for reproducible, one-command infrastructure deployment

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| AI / ML | Vertex AI Gemini 1.5 Pro, scikit-learn (Isolation Forest) |
| Backend | Python 3.11, Flask, Google Cloud Pub/Sub |
| Frontend | React 18, Vite, Firebase Realtime Database |
| Infrastructure | Google Cloud Run, Cloud Storage, Terraform |
| PDF Generation | ReportLab |
| Hosting | Firebase Hosting |
| Security Intel | MITRE ATT&CK Framework, AbuseIPDB |

---

## ⚙️ Setup & Deployment

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Google Cloud SDK | Latest | [Install](https://cloud.google.com/sdk/docs/install) |
| Terraform | >= 1.5.0 | [Install](https://developer.hashicorp.com/terraform/install) |
| Node.js | >= 18 | [Install](https://nodejs.org/) |
| Firebase CLI | Latest | `npm install -g firebase-tools` |

### Step 1 — Google Cloud Authentication

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project phantom-hack2skill
```

### Step 2 — Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

Note the output URLs — you will need them for environment variables.

### Step 3 — Configure Environment Variables

Copy `.env.example` to `.env` and fill in the values from Terraform output:

```env
GCP_PROJECT_ID=phantom-hack2skill
GCP_REGION=us-central1
REPORTS_BUCKET=<from terraform output>
LAYER1_URL=<from terraform output>
ABUSEIPDB_API_KEY=<optional, get free key at abuseipdb.com>
```

Create `frontend/.env`:

```env
VITE_FIREBASE_API_KEY=your_key
VITE_FIREBASE_AUTH_DOMAIN=phantom-hack2skill.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://phantom-hack2skill-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=phantom-hack2skill
VITE_FIREBASE_STORAGE_BUCKET=phantom-hack2skill.appspot.com
VITE_FIREBASE_APP_ID=your_app_id
VITE_LAYER1_URL=<layer1 cloud run url>
VITE_LAYER5_URL=<layer5 cloud run url>
```

### Step 4 — Deploy Backend Services

```bash
gcloud builds submit --config cloudbuild.yaml .
```

### Step 5 — Deploy Frontend

```bash
cd frontend
npm install
npm run build
firebase deploy --only hosting
```

### Step 6 — Test the Demo

1. Navigate to your Firebase Hosting URL
2. In the **Attack Simulation** panel, select an attack type and difficulty
3. Click **Launch Attack Demo**
4. Watch the Live Attack Feed, Threat Score Meter, and RL Agent Panel update live
5. Click the download button to get the generated **Threat Intelligence PDF**

---

## 🎮 Attack Simulation Mode

PHANTOM ships with a built-in simulation — no real attacker needed:

- Choose attack type: Ransomware, Data Exfiltration, SQL Injection, Brute Force, Recon
- Choose difficulty: Script Kiddie, Skilled Attacker, APT
- Watch everything unfold in real-time on the dashboard
- Download the auto-generated threat intelligence PDF at the end

---

## 📁 Project Structure

```
phantom/
├── layer1_honeypot/          # Flask honeypot service
│   ├── layer1_flask_trap.py
│   ├── Dockerfile
│   └── requirements.txt
├── layer2_bible/             # AI company generator
│   ├── layer2_company_bible.py
│   ├── Dockerfile
│   └── requirements.txt
├── layer3_rl/                # RL decision agent
│   ├── layer3_rl_agent.py
│   ├── Dockerfile
│   └── requirements.txt
├── layer4_analysis/          # Behavioral analysis
│   ├── layer4_analysis.py
│   ├── Dockerfile
│   └── requirements.txt
├── layer5_reports/           # Threat intelligence reports
│   ├── layer5_report_gen.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── AttackerProfile.jsx
│   │   │   ├── LiveAttackFeed.jsx
│   │   │   ├── RLAgentPanel.jsx
│   │   │   ├── SimulationPanel.jsx
│   │   │   ├── ThreatScoreMeter.jsx
│   │   │   └── WorldMap.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── firebase.json
│   └── package.json
├── infrastructure/           # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── shared/                   # Shared utilities
├── cloudbuild.yaml           # CI/CD pipeline
├── .env.example              # Environment variable template
├── README.md
└── SETUP.md
```

---

## 🗺️ Roadmap

- [ ] GPT-4o as an alternative LLM backend
- [ ] Kubernetes deployment for on-premise use
- [ ] SIEM integration (Splunk, Elastic) for enterprise export
- [ ] Multi-tenant support for SOC teams
- [ ] Automated attacker attribution using graph ML
- [ ] Email alerting for high-threat-score sessions

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss major changes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🙏 Acknowledgements

- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai) for Gemini API
- [Firebase](https://firebase.google.com/) for real-time data sync
- [MITRE ATT&CK](https://attack.mitre.org/) for the threat classification framework
- [AbuseIPDB](https://www.abuseipdb.com/) for IP reputation data
- [ReportLab](https://www.reportlab.com/) for PDF generation

---

**PHANTOM** — *Because the best defense is a perfect illusion.* 🕵️

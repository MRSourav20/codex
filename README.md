# Coadex 2.0: AI-Powered Behavioral Interview Integrity

**Coadex 2.0** is a next-generation integrity platform designed to detect AI-assisted cheating during remote technical interviews. By monitoring multi-layer behavioral signals through a secure AWS EC2 gateway, Coadex identifies suspicious patterns (like ChatGPT usage, browser switching, and rapid query bursts) without invasive deep packet inspection.

---

## 🚀 The Mission
Modern remote interviews are plagued by AI-overlay tools and "proxy" interviewers. Coadex solves this by creating a **Behavioral Intelligence Fingerprint** of the candidate, ensuring the person being interviewed is the one providing the answers.

---

## 🏗️ System Architecture

### 1. **Candidate Client (Desktop App)**
*   **Electron-based**: A secure desktop environment that manages the session.
*   **Hardware Isolation**: Monitors OS-level events (clipboard, tab switches, process blacklists) that browser-only solutions cannot see.

### 2. **Backend Intelligence Gateway (AWS EC2)**
*   **Traffic Interception**: Uses a high-performance `FastAPI` gateway.
*   **DNS/SNI Analysis**: Leverages `PyShark`/`TShark` to capture network metadata in real-time.
*   **Enrichment Pipeline**: 
    1.  **Rule-based**: Instant classification of common domains.
    2.  **Intelligence DB**: SQLite-backed local cache for rapid lookups.
    3.  **AI Enrichment**: Deep categorization using the **Sarvam AI** model for unknown/suspicious traffic.

### 3. **Anomaly Engine**
*   **EMA Bursts**: Detects rapid, non-human query patterns using Exponential Moving Averages.
*   **Behavioral Correlation**: Flags suspicious overlaps (e.g., a tab switch followed by a massive clipboard paste).

---

## 🛠️ Tech Stack
*   **Core**: Python 3.12, FastAPI
*   **Networking**: WireGuard (Session Tunnels), PyShark, TShark
*   **AI/ML**: Sarvam-m (LLM Enrichment), Scikit-Learn (Anomaly Detection)
*   **Database**: SQLite (Encrypted Event Storage)
*   **Infrastructure**: AWS EC2 (Ubuntu 22.04), t3.micro

---

## 📂 Repository Structure
*   `backend/api/`: FastAPI endpoints for session lifecycle.
*   `backend/dns_monitor/`: Robust packet capture and field-introspection logic.
*   `backend/enrichment/`: AI-powered domain classification and Sarvam integration.
*   `backend/intelligence/`: Persistent intelligence database and historical logging.
*   `backend/anomaly_engine/`: Statistical behavioral analysis modules.

---

## 🏁 Quick Start (Judges)

### 1. Requirements
*   Ubuntu 22.04 (Recommended)
*   Python 3.10+
*   TShark (`sudo apt install tshark`)

### 2. Live Monitoring Setup
```bash
# 1. Install Dependencies
chmod +x setup.sh
./setup.sh

# 2. Configure Environment
cp .env.example .env
# Add your SARVAM_API_KEY and WireGuard keys

# 3. Start the Enhanced Orchestrator
# This starts the Capture -> Categorizer -> AI Enrichment pipeline
sudo venv/bin/python3 backend/monitor_v3.py
```

---

## 📈 Roadmap
- [x] **Phase 1**: AWS Infrastructure & WireGuard Tunneling
- [x] **Phase 2**: Multi-version Robust DNS Capture (PyShark Fixes)
- [x] **Phase 3**: AI Enrichment Pipeline with Sarvam AI
- [ ] **Phase 4**: Electron Desktop App Integration
- [ ] **Phase 5**: Reviewer Interactive Dashboard

---
*Built for the next generation of honest hiring.*

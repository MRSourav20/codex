# Coadex 2.0 - Behavioral Interview Integrity Platform

Coadex 2.0 is a lightweight behavioral intelligence platform designed to detect AI-assisted cheating during remote technical interviews. Unlike traditional proctoring, it focuses on metadata-level network monitoring and gaze zone detection.

## Architecture

- **Candidate Client**: Electron-based desktop app for session management and OS-level monitoring.
- **Backend (Gateway)**: FastAPI-based gateway on AWS EC2 managing WireGuard tunnels and metadata collection.
- **Enrichment Pipeline**: Multi-stage classification (Rule-based -> SQLite Cache -> Sarvam-2B AI).
- **Anomaly Engine**: Statistical behavioral analysis (EMA-based bursts, rapid query detection).

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLite
- **Networking**: WireGuard, PyShark/TShark
- **AI**: Sarvam-2B (Adaptive Domain Classification)
- **Deployment**: AWS EC2 (t3.micro)

## Setup & Deployment

1. **Clone and Configure**:
   ```bash
   git clone <repo-url>
   cd Coadex-2.0
   cp .env.example .env
   # Edit .env with your keys
   ```

2. **Automated Setup (Ubuntu 22.04)**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Run Backend**:
   ```bash
   source venv/bin/activate
   python3 backend/api/main.py
   ```

4. **Run DNS Monitor**:
   ```bash
   sudo venv/bin/python3 backend/monitor_v3.py
   ```

## Repository Structure
- `backend/`: Core logic, API, and monitoring modules.
- `docs/`: Architecture, implementation, and research notes.
- `tests/`: Unit and integration tests.
- `requirements.txt`: Python dependencies.
- `setup.sh`: Deployment automation.

## Roadmap
- [x] Chunk 1: Infrastructure & Tunnel Setup
- [x] Chunk 2: Network Monitoring & Logging
- [x] Chunk 3: Intelligent Domain Enrichment
- [ ] Chunk 4: Behavioral Anomaly Engine
- [ ] Chunk 5: Electron Desktop Client
- [ ] Chunk 6: Reviewer Dashboard

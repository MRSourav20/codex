# EC2 Deployment & Reproducibility Guide

This document captures all configurations and setup steps performed on the Optimus EC2 instance (`3.235.42.166`). Save this file locally to recreate the environment on a new instance.

## 1. System Requirements (Ubuntu 22.04+)

The following system packages must be installed for network monitoring and Python environment management:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv tshark libpcap-dev
```

**Security Note:** `tshark` normally requires root privileges. Ensure the user is in the `wireshark` group or run the platform with `sudo`.

## 2. Project Initialization

Clone the project and set up the virtual environment:

```bash
mkdir ~/Coadex-2.0
cd ~/Coadex-2.0
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Environment Configuration (.env)

Create a `.env` file in `~/Coadex-2.0/` with the following structure:

```env
# AI Enrichment
SARVAM_API_KEY=sk_ge1o4kdw_UU0k85bLN9Qb8rtYUWaqWp85

# Project Paths
LOG_DIR=./dns_logs
DB_PATH=./dns_logs/domain_intelligence.db

# SMTP Alerting (Server-Side)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=nothing4alllll@gmail.com
SMTP_PASS=qccs jkmd wvvg butl
SMTP_TO=mohapatrasourav2000@gmail.com

# Legacy / WireGuard (If still required for specific modules)
WG_INTERFACE=wg0
WG_SERVER_IP=3.235.42.166
WG_SERVER_PUBKEY=8T9SWJzxG4euKU5zY3NozGytS1MU
```

## 4. Python Dependencies (Lock)

The following versions were verified on the active EC2 instance:

| Package | Version |
|---------|---------|
| fastapi | 0.109.0 |
| pydantic | 2.5.3 |
| pyshark | 0.6 |
| rich | 15.0.0 |
| requests | 2.31.0 |
| python-dotenv | 1.0.0 |
| uvicorn | 0.27.0 |
| textual | 8.2.7 |

## 5. Execution Command

Always run with the virtual environment's Python to ensure dependencies are loaded, and use `sudo` for packet capture:

```bash
sudo ~/Coadex-2.0/venv/bin/python3 optimus.py
```

## 6. Directory Map

Expected structure on EC2:
- `~/Coadex-2.0/`
    - `optimus.py` (Entrypoint)
    - `.env` (Config)
    - `backend/` (Core Logic)
    - `reports/` (Generated on exit)
    - `dns_logs/` (SQLite databases)
    - `venv/` (Python Environment)

# GitHub & EC2 Deployment Policy

This folder contains the complete refactored logic for Coadex 2.0. To ensure a smooth deployment, follow these rules regarding GitHub and AWS EC2.

## 1. What to Upload to GitHub
You should upload the **entire folder** to GitHub, but you MUST exclude sensitive credentials.

### ✅ Upload
- `backend/` (All logic, including `api/`, `dns_monitor/`, `enrichment/`, etc.)
- `docs/` (Architecture and research)
- `tests/`
- `README.md`
- `requirements.txt`
- `setup.sh`
- `.gitignore` (Critical - see below)

### ❌ DO NOT Upload (Security Risk)
- `.env` (Contains your Sarvam API Key and WireGuard keys)
- `key/adk92.pem` (Your AWS Access Key)
- `dns_logs/` (Local interview data)
- `backend/api/sessions.db` (Local database)

---

## 2. Automated .gitignore
I have created a `.gitignore` file for you. Ensure it is in the root directory before you `git push`.

```text
# Security
.env
*.pem
key/

# Databases
*.db
backend/api/*.db
dns_logs/*.db

# Logs & Storage
dns_logs/
logs/
*.jsonl

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
```

---

## 3. Deployment via GitHub (The "Agentic" Pull)
Once you push your code to a GitHub repository, I can help you pull it onto the EC2 instance.

### Prerequisites:
1.  **Security Group**: Ensure Port 22 (SSH) is open for your IP in AWS. (I currently cannot reach the server, likely due to AWS firewall).
2.  **Git on EC2**: The `setup.sh` script installs git.

### Step-by-Step:
1.  **Push**: `git push origin main` from your local machine.
2.  **Pull**: I will log in via SSH (once you open the port) and run:
    ```bash
    cd ~/Coadex-2.0
    git pull origin main
    ./setup.sh
    ```

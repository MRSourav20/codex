#!/bin/bash
set -e
cd ~/Coadex-2.0

# Clean stale DB and reports
sudo rm -f backend/sessions.db
sudo rm -rf reports/*
sudo chown -R ubuntu:ubuntu .
mkdir -p reports

echo "=== IMPORT TEST ==="
~/Coadex-2.0/venv/bin/python3 -c "
from backend.dns_monitor.dns_logger import DNSLogger
from backend.session_manager import SessionManager
from backend.reporting.report_generator import ReportGenerator
print('ALL IMPORTS OK')
"

echo "=== RUNNING OPTIMUS (8 seconds) ==="
sudo ~/Coadex-2.0/venv/bin/python3 optimus.py &
PID=$!
sleep 8
sudo kill -INT $PID || true
sleep 4

echo "=== REPORTS ==="
ls -la reports/
echo "=== TXT ==="
cat reports/*.txt 2>/dev/null || echo "No TXT"
echo "=== JSON HEAD ==="
head -20 reports/*.json 2>/dev/null || echo "No JSON"
echo "=== DONE ==="

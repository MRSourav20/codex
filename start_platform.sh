#!/bin/bash
echo "=========================================="
echo "    OPTIMUS IDENTITY GATEWAY LAUNCHER"
echo "=========================================="

echo "[*] Starting FastAPI Backend on port 8080 (Background)..."
cd backend || exit
nohup uvicorn api.main:app --host 0.0.0.0 --port 8080 > ../api.log 2>&1 &
API_PID=$!
echo "[+] API Server running (PID: $API_PID)"

echo "[*] Starting DNS Capture Engine (Background)..."
nohup sudo python3 monitor_v3.py --interface wg0 > ../dns_capture.log 2>&1 &
MONITOR_PID=$!
echo "[+] DNS Capture Engine running (PID: $MONITOR_PID)"

echo ""
echo "[✓] Platform Services Started Successfully."
echo "Use 'python3 backend/dashboard/dashboard.py <SESSION_ID>' to view live session metrics."
echo "To stop services, run: kill $API_PID && sudo kill $MONITOR_PID"

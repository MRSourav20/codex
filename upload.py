import subprocess
import base64

with open('backend/dns_monitor/dns_logger.py', 'rb') as f:
    code = f.read()
b = base64.b64encode(code).decode('ascii')

cmd = f'echo "{b}" | base64 -d | sudo tee ~/Coadex-2.0/backend/dns_monitor/dns_logger.py > /dev/null'

print("Uploading...")
subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', '-i', 'Server_EC2/adk92.pem', 'ubuntu@3.235.42.166', cmd])
print("Done uploading dns_logger.py")

# Now run the test
print("Running test on EC2...")
test_cmd = """cd ~/Coadex-2.0 && rm -rf reports/* && sudo ~/Coadex-2.0/venv/bin/python3 optimus.py > execution.log 2>&1 & PID=$!; sleep 10; sudo kill -INT $PID; sleep 5; echo '--- REPORTS ---'; ls -la reports/; echo '--- TXT CONTENT ---'; cat reports/*.txt 2>/dev/null || echo 'No TXT file'; echo '--- JSON CONTENT ---'; head -n 25 reports/*.json"""

subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', '-i', 'Server_EC2/adk92.pem', 'ubuntu@3.235.42.166', test_cmd])

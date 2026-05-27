#!/bin/bash

# Coadex 2.0 EC2 Deployment Script
# Target: Ubuntu 22.04 LTS

echo "--- Initializing Coadex 2.0 Deployment ---"

# Update and install system dependencies
sudo apt-get update
sudo apt-get install -y wireshark tshark wireguard python3-pip python3-venv

# Set up non-interactive tshark
echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections
sudo dpkg-reconfigure -f noninteractive wireshark-common

# Add current user to wireshark group
sudo usermod -a -G wireshark $USER

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs intelligence dns_logs

# Optional: Add 1GB swap for t3.micro (1GB RAM is tight for pyshark)
if [ ! -f /swapfile ]; then
    echo "Creating 1GB swap file for stability..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "--- Setup Complete ---"
echo "To start the backend, run: source venv/bin/activate && python3 backend/api/main.py"
echo "To start the monitoring orchestrator, run: sudo venv/bin/python3 backend/monitor_v3.py"

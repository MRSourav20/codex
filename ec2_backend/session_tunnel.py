import subprocess
import os
import secrets

def generate_key_pair():
    """Generates a WireGuard private and public key pair."""
    privkey = subprocess.check_output(["wg", "genkey"]).decode("utf-8").strip()
    pubkey = subprocess.check_output(["wg", "pubkey"], input=privkey.encode("utf-8")).decode("utf-8").strip()
    return privkey, pubkey

def get_client_config(session_id, client_privkey, server_pubkey, server_endpoint, client_address):
    """Generates a standard WireGuard client configuration string."""
    config = f"""[Interface]
PrivateKey = {client_privkey}
Address = {client_address}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pubkey}
Endpoint = {server_endpoint}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return config

def add_peer(interface, client_pubkey, allowed_ip):
    """Adds a peer to the WireGuard interface using the 'wg' command."""
    try:
        subprocess.run(["sudo", "wg", "set", interface, "peer", client_pubkey, "allowed-ips", f"{allowed_ip}/32"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error adding peer: {e}")
        return False

def remove_peer(interface, client_pubkey):
    """Removes a peer from the WireGuard interface."""
    try:
        subprocess.run(["sudo", "wg", "set", interface, "peer", client_pubkey, "remove"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error removing peer: {e}")
        return False

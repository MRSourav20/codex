import subprocess
import os
import secrets
from typing import Tuple

class WireGuardTunnel:
    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        privkey = subprocess.check_output(['wg', 'genkey']).decode('utf-8').strip()
        pubkey = subprocess.check_output(['wg', 'pubkey'], input=privkey.encode('utf-8')).decode('utf-8').strip()
        return privkey, pubkey

    @staticmethod
    def add_peer(interface: str, client_pubkey: str, client_address: str) -> bool:
        try:
            subprocess.run(['sudo', 'wg', 'set', interface, 'peer', client_pubkey, 'allowed-ips', f'{client_address}/32'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f'Error adding peer: {e}')
            return False

    @staticmethod
    def remove_peer(interface: str, client_pubkey: str) -> bool:
        try:
            subprocess.run(['sudo', 'wg', 'set', interface, 'peer', client_pubkey, 'remove'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f'Error removing peer: {e}')
            return False

    @staticmethod
    def generate_client_config(session_id: str, client_privkey: str, server_pubkey: str, server_endpoint: str, client_address: str) -> str:
        config = f'''[Interface]
PrivateKey = {client_privkey}
Address = {client_address}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pubkey}
Endpoint = {server_endpoint}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
'''
        return config

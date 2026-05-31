# EC2 WireGuard Routing/NAT Checklist (wg0 full-tunnel)

This project uses a **full-tunnel** client config (`AllowedIPs = 0.0.0.0/0, ::/0`). For traffic to actually egress from the EC2 instance, the EC2 host must have **IP forwarding** enabled and **NAT masquerading** set up.

## 1) Confirm WireGuard is running

On EC2:

`sudo wg`

- You should see interface `wg0` with peers.
- When a client connects, `latest handshake` should become recent (not `never`).
- `transfer: ... received, ... sent` should increase after client generates traffic.

## 2) Enable IPv4 forwarding (required)

On EC2:

`sudo sysctl -w net.ipv4.ip_forward=1`

Persist across reboots:

`sudo sh -c "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf"`

## 3) Add NAT masquerade + forwarding rules (required)

Find the EC2 WAN interface name (often `eth0`):

`ip route get 1.1.1.1`

Add rules (replace `eth0` if different):

`sudo iptables -A FORWARD -i wg0 -o eth0 -j ACCEPT`

`sudo iptables -A FORWARD -i eth0 -o wg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT`

`sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE`

Validate counters:

`sudo iptables -t nat -L POSTROUTING -v -n`

## 4) Make it survive reboot (recommended)

Install persistent rules:

`sudo apt-get update && sudo apt-get install -y iptables-persistent`

Then:

`sudo netfilter-persistent save`

## 5) Common failure mapping (root-cause layers)

- **Handshake layer**: `latest handshake: never` on EC2 and client → peer not added, wrong keys, UDP/51820 blocked, wrong endpoint.
- **Routing layer**: handshake exists but client DNS/public IP still local → client `AllowedIPs` not `0.0.0.0/0`, routes not applied, or WireGuard not actually enabled.
- **NAT layer**: handshake exists and client TX increases, but internet/DNS via tunnel fails → EC2 `ip_forward`/iptables masquerade missing.


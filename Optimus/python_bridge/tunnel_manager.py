import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("WireGuardTunnel")


def _run(cmd: list[str], *, check: bool = True, timeout_s: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _tunnel_name_from_conf(conf_path: str) -> str:
    return Path(conf_path).name.rsplit(".", 1)[0]


def _find_windows_wireguard_tools() -> Tuple[str, str]:
    wireguard_exe = os.getenv("WIREGUARD_EXE", "").strip()
    wg_exe = os.getenv("WG_EXE", "").strip()

    if wireguard_exe and wg_exe and os.path.exists(wireguard_exe) and os.path.exists(wg_exe):
        return wireguard_exe, wg_exe

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    base = os.path.join(program_files, "WireGuard")
    wg_default = os.path.join(base, "wg.exe")
    wireguard_default = os.path.join(base, "wireguard.exe")

    if not os.path.exists(wireguard_default):
        raise FileNotFoundError(
            "WireGuard for Windows not found. Install WireGuard, or set WIREGUARD_EXE/WG_EXE env vars."
        )
    if not os.path.exists(wg_default):
        raise FileNotFoundError("wg.exe not found next to wireguard.exe. Reinstall WireGuard, or set WG_EXE.")

    return wireguard_default, wg_default


def _which(name: str) -> Optional[str]:
    try:
        out = _run(["which", name], check=False)
        path = out.stdout.strip()
        return path if path else None
    except Exception:
        return None


_RE_LATEST_HANDSHAKE = re.compile(r"latest handshake:\s*(.+)$", re.MULTILINE)
_RE_TRANSFER = re.compile(r"transfer:\s*([0-9.]+)\s*([A-Za-z]+)\s*received,\s*([0-9.]+)\s*([A-Za-z]+)\s*sent", re.MULTILINE)


def _size_to_bytes(value: float, unit: str) -> int:
    unit_l = unit.lower()
    if unit_l in {"b", "bytes"}:
        return int(value)
    if unit_l in {"kb", "kib"}:
        return int(value * 1024)
    if unit_l in {"mb", "mib"}:
        return int(value * 1024 * 1024)
    if unit_l in {"gb", "gib"}:
        return int(value * 1024 * 1024 * 1024)
    return int(value)


@dataclass(frozen=True)
class WgStats:
    latest_handshake: Optional[str]
    rx_bytes: int
    tx_bytes: int


def _parse_wg_show(output: str) -> WgStats:
    latest = None
    m_hs = _RE_LATEST_HANDSHAKE.search(output)
    if m_hs:
        latest = m_hs.group(1).strip()

    rx_bytes = 0
    tx_bytes = 0
    m_tr = _RE_TRANSFER.search(output)
    if m_tr:
        rx_bytes = _size_to_bytes(float(m_tr.group(1)), m_tr.group(2))
        tx_bytes = _size_to_bytes(float(m_tr.group(3)), m_tr.group(4))

    return WgStats(latest_handshake=latest, rx_bytes=rx_bytes, tx_bytes=tx_bytes)


def _wg_show(interface: str) -> str:
    if sys.platform == "win32":
        _, wg_exe = _find_windows_wireguard_tools()
        proc = _run([wg_exe, "show", interface], check=False)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "wg show failed")
        return proc.stdout

    wg_path = _which("wg")
    if not wg_path:
        raise FileNotFoundError("wg not found. Install WireGuard tools.")

    proc = _run([wg_path, "show", interface], check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "wg show failed")
    return proc.stdout


def _generate_probe_traffic(timeout_s: int = 2) -> None:
    py = sys.executable
    code = r"""
import socket, time
dsts = [("1.1.1.1", 53), ("8.8.8.8", 53)]
for host, port in dsts:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.sendto(b"\x00\x00", (host, port))
        s.close()
    except Exception:
        pass
time.sleep(0.2)
"""
    _run([py, "-c", code], check=False, timeout_s=timeout_s)


def _is_recent_handshake(latest_handshake: Optional[str]) -> bool:
    if not latest_handshake:
        return False
    if latest_handshake.lower().startswith("never"):
        return False
    return True


def _validate_tunnel(interface: str, *, wait_s: int = 20, min_tx_delta_bytes: int = 256) -> dict:
    deadline = time.time() + max(1, wait_s)

    last_error = None
    initial: Optional[WgStats] = None
    while time.time() < deadline:
        try:
            stats = _parse_wg_show(_wg_show(interface))
            if initial is None:
                initial = stats

            if _is_recent_handshake(stats.latest_handshake):
                before = stats
                _generate_probe_traffic()
                after = _parse_wg_show(_wg_show(interface))
                tx_delta = after.tx_bytes - before.tx_bytes
                rx_delta = after.rx_bytes - before.rx_bytes

                if tx_delta >= min_tx_delta_bytes or rx_delta >= min_tx_delta_bytes:
                    return {
                        "connected": True,
                        "latest_handshake": after.latest_handshake,
                        "rx_bytes": after.rx_bytes,
                        "tx_bytes": after.tx_bytes,
                        "rx_delta": rx_delta,
                        "tx_delta": tx_delta,
                    }

                last_error = (
                    "WireGuard handshake exists, but no tunnel traffic observed (RX/TX did not increase). "
                    "Root-cause layer: routing (AllowedIPs/default route) or server NAT/forwarding."
                )
            else:
                last_error = (
                    "No WireGuard handshake yet. Root-cause layer: handshake (peer not registered, endpoint/keys/port)."
                )
        except Exception as e:
            last_error = str(e)

        time.sleep(1)

    return {
        "connected": False,
        "error": last_error or "Validation timed out",
        "root_cause_layer": (
            "handshake"
            if (last_error and "handshake" in last_error.lower())
            else "routing_or_nat_or_dns"
        ),
    }


def bring_up(conf_path: str) -> str:
    if not os.path.exists(conf_path):
        raise FileNotFoundError(f"Config not found: {conf_path}")

    if sys.platform == "win32":
        wireguard_exe, _ = _find_windows_wireguard_tools()
        proc = _run([wireguard_exe, "/installtunnelservice", conf_path], check=False, timeout_s=60)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "WireGuard service install failed")
        return _tunnel_name_from_conf(conf_path)

    wg_quick = _which("wg-quick")
    if not wg_quick:
        raise FileNotFoundError("wg-quick not found. Install wireguard-tools.")

    proc = _run(["sudo", wg_quick, "up", conf_path], check=False, timeout_s=60)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "wg-quick up failed")
    return _tunnel_name_from_conf(conf_path)


def bring_down(conf_path: str) -> None:
    tunnel_name = _tunnel_name_from_conf(conf_path)

    if sys.platform == "win32":
        wireguard_exe, _ = _find_windows_wireguard_tools()
        proc = _run([wireguard_exe, "/uninstalltunnelservice", tunnel_name], check=False, timeout_s=60)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(msg or "WireGuard service uninstall failed")
        return

    wg_quick = _which("wg-quick")
    if not wg_quick:
        raise FileNotFoundError("wg-quick not found. Install wireguard-tools.")

    proc = _run(["sudo", wg_quick, "down", conf_path], check=False, timeout_s=60)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(msg or "wg-quick down failed")


def is_active(interface: str) -> bool:
    try:
        out = _wg_show(interface)
        stats = _parse_wg_show(out)
        return _is_recent_handshake(stats.latest_handshake) or (stats.rx_bytes > 0 or stats.tx_bytes > 0)
    except Exception:
        return False


if __name__ == "__main__":
    args = sys.argv[1:]
    try:
        if "--up" in args:
            idx = args.index("--up")
            conf_path = args[idx + 1]
            tunnel_name = bring_up(conf_path)
            validation = _validate_tunnel(tunnel_name, wait_s=int(os.getenv("WG_VALIDATE_WAIT_S", "20")))
            if not validation.get("connected"):
                raise RuntimeError(validation.get("error") or "Tunnel validation failed")
            print(json.dumps({"success": True, "conf_path": conf_path, "interface": tunnel_name, **validation}))

        elif "--down" in args:
            idx = args.index("--down")
            conf_path = args[idx + 1]
            bring_down(conf_path)
            print(json.dumps({"success": True, "deactivated": True}))

        elif "--status" in args:
            interface = os.getenv("WG_INTERFACE_NAME", "").strip()
            if not interface:
                print(json.dumps({"active": False, "error": "WG_INTERFACE_NAME not set"}))
            else:
                print(json.dumps({"active": is_active(interface)}))

        elif "--validate" in args:
            idx = args.index("--validate")
            interface = args[idx + 1]
            print(json.dumps(_validate_tunnel(interface, wait_s=int(os.getenv("WG_VALIDATE_WAIT_S", "20")))))

        else:
            print(json.dumps({"error": "Invalid command"}))
            sys.exit(2)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


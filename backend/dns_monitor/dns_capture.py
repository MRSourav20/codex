#!/usr/bin/env python3
"""
DNS Packet Capture Module - FIXED VERSION
Captures live DNS packets on AWS EC2 gateway using pyshark/tshark.
FIXED: Handles multiple pyshark/tshark versions with different DNS field names.
"""

import pyshark
import signal
import sys
import time
from datetime import datetime
from collections import deque
from typing import Optional, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DNSCapture")


class DNSPacketCapture:
    """
    Captures DNS packets on EC2 gateway.
    Provides:
    - Real-time DNS domain extraction
    - Timestamp logging
    - Packet counting
    - Duplicate filtering
    - Graceful shutdown support
    - Multi-version pyshark support
    """
    
    def __init__(
        self,
        interface: str = 'any',
        duplicate_window_seconds: int = 5,
        debug: bool = False
    ):
        """
        Initialize DNS packet capture.
        
        Args:
            interface: Network interface to monitor ('any' for all)
            duplicate_window_seconds: Time window for duplicate filtering
            debug: Enable debug logging for DNS field inspection
        """
        self.interface = interface
        self.duplicate_window_seconds = duplicate_window_seconds
        self.debug = debug
        
        # Tracking
        self.packet_count = 0
        self.domain_count = 0
        self.start_time = datetime.now()
        self.running = True
        self.recent_domains: deque = deque(maxlen=1000)
        
        # For duplicate filtering
        self.domain_timestamps: dict = {}
        
        # Statistics
        self.error_count = 0
        self.malformed_count = 0
        
        # DNS field detection
        self.detected_dns_field = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info(f"DNSCapture initialized - Interface: {interface}, Debug: {debug}")
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        logger.info("\n\nShutdown signal received. Cleaning up...")
        self.running = False
        # Do NOT call sys.exit() here — it causes SystemExit inside asyncio event loop,
        # producing EOFError tracebacks. Let start_capture() detect self.running=False and exit cleanly.
    
    def _is_duplicate(self, domain: str) -> bool:
        """
        Check if domain was recently seen (within duplicate_window_seconds).
        
        Args:
            domain: Domain name to check
            
        Returns:
            True if domain is recent duplicate, False otherwise
        """
        now = time.time()
        
        if domain in self.domain_timestamps:
            last_seen = self.domain_timestamps[domain]
            if (now - last_seen) < self.duplicate_window_seconds:
                return True
        
        self.domain_timestamps[domain] = now
        return False
    
    def _sanitize_domain(self, domain: str) -> Optional[str]:
        """
        Sanitize and validate domain name.
        
        Args:
            domain: Raw domain from packet
            
        Returns:
            Cleaned domain or None if invalid
        """
        if not domain:
            return None
        
        # Convert to string if needed
        domain = str(domain)
        
        # Remove trailing dots from FQDN
        domain = domain.rstrip('.')
        
        # Skip empty or localhost queries
        if not domain or domain == 'localhost':
            return None
        
        # Skip multicast/mDNS queries
        if domain.endswith('.local') or domain.endswith('.arpa'):
            return None
        
        return domain.lower()
    
    def _get_all_dns_fields(self, dns_layer) -> dict:
        """
        Get all raw DNS fields from pyshark's internal field dict.
        pyshark stores parsed fields in dns_layer._all_fields, NOT as Python
        attributes — so dir() / hasattr() / getattr() don't find them.
        
        Returns:
            Dict of {field_key: field_value_str}
        """
        raw = {}
        try:
            # Primary source: pyshark's internal field store
            if hasattr(dns_layer, '_all_fields'):
                raw = {k.lower(): str(v) for k, v in dns_layer._all_fields.items()}
        except Exception:
            pass
        return raw

    def _detect_dns_field(self, dns_layer) -> str:
        """
        Auto-detect the correct DNS query name field key for this tshark version.
        Searches dns_layer._all_fields (the real field store) for known key patterns.
        
        Returns:
            Detected field key string, or empty string if not found.
        """
        raw = self._get_all_dns_fields(dns_layer)
        if not raw:
            logger.warning("DNS layer has no _all_fields — cannot detect field.")
            return ''

        # Priority-ordered candidate keys (all lowercase for comparison)
        candidates = [
            'dns.qry.name',
            'dns.query.name',
            'dns.resp.name',
            ' queries', # Note the space if tshark provides it that way in some versions
            'queries',
            'qry_name',
            'query_name',
            'dns_qry_name',
        ]

        # First check the prioritized list
        for candidate in candidates:
            c_clean = candidate.strip()
            if c_clean in raw:
                logger.info(f"✓ Detected DNS query field key: '{c_clean}'")
                return c_clean

        # Fallback: search raw keys for 'qry' or 'query' or 'name' or exactly 'queries'
        for key in raw:
            k_low = key.lower()
            if 'qry.name' in k_low or ('query' in k_low and 'name' in k_low) or k_low == 'queries':
                logger.info(f"✓ Auto-detected DNS field key: '{key}'")
                return key

        logger.warning(f"Could not find query field. Available DNS keys: {list(raw.keys())[:20]}")
        return ''
    
    def _extract_dns_domains(self, packet) -> list:
        """
        Extract DNS queried domains from packet.
        Uses dns_layer._all_fields (pyshark's internal dict) for robust,
        version-independent extraction.
        
        Args:
            packet: pyshark packet object
            
        Returns:
            List of domain names
        """
        domains = []
        
        try:
            if 'DNS' not in [l.layer_name.upper() for l in packet.layers]:
                return domains

            dns_layer = packet.dns
            raw = self._get_all_dns_fields(dns_layer)

            if not raw:
                self.malformed_count += 1
                return domains

            # Detect query field key once, then reuse
            if self.detected_dns_field is None:
                self.detected_dns_field = self._detect_dns_field(dns_layer)

            if not self.detected_dns_field:
                return domains

            # Pull values from the raw dict. 
            # On some pyshark versions, 'queries' is a nested object and the actual 
            # names are in keys like 'dns.qry.name', 'dns.qry.name_0', etc.
            # We iterate through all fields and find any that match our detected key pattern.
            search_prefix = self.detected_dns_field
            
            for key, val in raw.items():
                # Match exact key or indexed keys like dns.qry.name_0
                if key == search_prefix or key.startswith(f"{search_prefix}."):
                    if val and '.' in val: # Basic domain check
                        sanitized = self._sanitize_domain(str(val))
                        if sanitized:
                            domains.append(sanitized)
                            if self.debug:
                                logger.debug(f"Extracted domain from {key}: {sanitized}")
            
            # Fallback check for any field containing 'qry.name' if domains still empty
            if not domains:
                for key, val in raw.items():
                    if 'qry.name' in key and val and '.' in val:
                        sanitized = self._sanitize_domain(str(val))
                        if sanitized:
                            domains.append(sanitized)

        except AttributeError as e:
            self.malformed_count += 1
            logger.debug(f"Malformed DNS packet: {str(e)}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error extracting DNS domain: {str(e)}")
        
        return domains
    
    def _print_packet_info(self, domain: str, timestamp: str):
        """
        Print captured domain in real-time format.
        
        Args:
            domain: Domain name
            timestamp: ISO format timestamp
        """
        time_str = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
        print(f"[{time_str}] {domain}")
    
    def _print_statistics(self):
        """Print session statistics."""
        elapsed = datetime.now() - self.start_time
        print("\n" + "="*60)
        print("DNS CAPTURE SESSION STATISTICS")
        print("="*60)
        print(f"Duration: {elapsed}")
        print(f"Total Packets Processed: {self.packet_count}")
        print(f"Unique Domains Captured: {self.domain_count}")
        print(f"Malformed Packets: {self.malformed_count}")
        print(f"Errors: {self.error_count}")
        if self.detected_dns_field:
            print(f"Detected DNS Field: {self.detected_dns_field}")
        if self.packet_count > 0:
            print(f"Avg Packets/sec: {self.packet_count / elapsed.total_seconds():.2f}")
        print("="*60)
    
    def start_capture(self):
        """
        Start live DNS packet capture.
        Runs continuously until shutdown signal received.
        """
        print("\n" + "="*60)
        print("DNS PACKET CAPTURE - CHUNK 2 (FIXED VERSION)")
        print("="*60)
        print(f"Interface: {self.interface}")
        print(f"Display Filter: dns")
        print(f"Duplicate Window: {self.duplicate_window_seconds}s")
        print(f"Debug Mode: {self.debug}")
        print("Listening for DNS traffic (Ctrl+C to stop)...\n")
        
        try:
            capture = pyshark.LiveCapture(
                interface=self.interface,
                display_filter='dns'
            )
            
            for packet in capture.sniff_continuously():
                if not self.running:
                    break
                
                self.packet_count += 1
                
                # Extract domains from this packet
                domains = self._extract_dns_domains(packet)
                
                for domain in domains:
                    # Skip duplicates
                    if self._is_duplicate(domain):
                        continue
                    
                    self.domain_count += 1
                    timestamp = datetime.now().isoformat()
                    
                    # Store in memory
                    self.recent_domains.append({
                        'domain': domain,
                        'timestamp': timestamp
                    })
                    
                    # Print real-time
                    self._print_packet_info(domain, timestamp)
        
        except PermissionError:
            logger.error("ERROR: This script requires root/sudo privileges to capture packets.")
            logger.error("Run with: sudo python3 dns_capture.py")
            sys.exit(1)
        except (KeyboardInterrupt, SystemExit):
            pass  # Graceful exit — statistics already printed via _handle_shutdown
        except Exception as e:
            logger.error(f"Fatal error in packet capture: {str(e)}")
        finally:
            self._print_statistics()
    
    def get_recent_domains(self, limit: int = 100) -> list:
        """
        Get recently captured domains.
        
        Args:
            limit: Maximum number of domains to return
            
        Returns:
            List of domain metadata dicts
        """
        return list(self.recent_domains)[-limit:]


if __name__ == "__main__":
    # Main entry point
    # Use --debug flag for detailed field inspection
    import sys
    debug = '--debug' in sys.argv
    
    capture = DNSPacketCapture(interface='any', debug=debug)
    capture.start_capture()
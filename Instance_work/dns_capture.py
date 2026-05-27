#!/usr/bin/env python3
"""
DNS Packet Capture Module - Chunk 2 Implementation
Captures live DNS packets on AWS EC2 gateway using pyshark/tshark.
Runs independently to verify metadata observation works.
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
    """
    
    def __init__(
        self,
        interface: str = 'any',
        duplicate_window_seconds: int = 5
    ):
        """
        Initialize DNS packet capture.
        
        Args:
            interface: Network interface to monitor ('any' for all)
            duplicate_window_seconds: Time window for duplicate filtering
        """
        self.interface = interface
        self.duplicate_window_seconds = duplicate_window_seconds
        
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
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info(f"DNSCapture initialized - Interface: {interface}")
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        logger.info("\n\nShutdown signal received. Cleaning up...")
        self.running = False
        self._print_statistics()
        sys.exit(0)
    
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
        
        # Remove trailing dots from FQDN
        domain = domain.rstrip('.')
        
        # Skip empty or localhost queries
        if not domain or domain == 'localhost':
            return None
        
        # Skip multicast/mDNS queries
        if domain.endswith('.local') or domain.endswith('.arpa'):
            return None
        
        return domain.lower()
    
    def _extract_dns_domains(self, packet) -> list:
        """
        Extract DNS queried domains from packet.
        Handles malformed packets gracefully.
        
        Args:
            packet: pyshark packet object
            
        Returns:
            List of domain names
        """
        domains = []
        
        try:
            if hasattr(packet, 'dns'):
                dns_layer = packet.dns
                
                # Access DNS query names
                if hasattr(dns_layer, 'qry_name'):
                    # Single query or list of queries
                    qry_names = dns_layer.qry_name
                    
                    if isinstance(qry_names, str):
                        qry_names = [qry_names]
                    
                    for name in qry_names:
                        sanitized = self._sanitize_domain(name)
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
        if self.packet_count > 0:
            print(f"Avg Packets/sec: {self.packet_count / elapsed.total_seconds():.2f}")
        print("="*60)
    
    def start_capture(self):
        """
        Start live DNS packet capture.
        Runs continuously until shutdown signal received.
        """
        print("\n" + "="*60)
        print("DNS PACKET CAPTURE - CHUNK 2 MVP")
        print("="*60)
        print(f"Interface: {self.interface}")
        print(f"Display Filter: dns")
        print(f"Duplicate Window: {self.duplicate_window_seconds}s")
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
        except KeyboardInterrupt:
            self._handle_shutdown(None, None)
        except Exception as e:
            logger.error(f"Fatal error in packet capture: {str(e)}")
            self._print_statistics()
            sys.exit(1)
    
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
    capture = DNSPacketCapture(interface='any')
    capture.start_capture()

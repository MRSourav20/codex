#!/usr/bin/env python3
"""
Enhanced Monitoring Orchestrator - Chunk 3 Integration
Coordinates DNS capture, intelligent categorization, enrichment, and logging.
Pipeline: Rule-based → Local DB → Sarvam API → Store result
"""

import logging
import sys
import os
from datetime import datetime
import threading
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.dns_monitor.dns_capture import DNSPacketCapture
from backend.dns_monitor.dns_logger import DNSLogger
from backend.enrichment.dns_categorizer_v2 import DomainCategorizer
from backend.anomaly_engine.dns_event_detector import SuspiciousEventDetector
from backend.intelligence.domain_intelligence_db import DomainIntelligenceDB
from backend.enrichment.Sarvam_enrichment import SarvamEnrichment, EnrichmentPipeline
from backend.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('./dns_logs/monitor_v3.log')
    ]
)
logger = logging.getLogger("MonitorOrchestratorV3")


class EnhancedMonitoringOrchestrator:
    """
    Enhanced orchestrator with intelligent domain enrichment.
    
    Pipeline:
    1. Capture DNS packet (tshark)
    2. Extract domain
    3. Rule-based categorization
    4. Check local intelligence DB
    5. If unknown: call Sarvam API
    6. Store result locally
    7. Log to database
    8. Generate events
    """
    
    def __init__(
        self,
        interface: str = 'any',
        enable_enrichment: bool = True,
        enrichment_threshold: float = 0.0
    ):
        """
        Initialize enhanced monitoring orchestrator.
        
        Args:
            interface: Network interface to monitor
            enable_enrichment: Enable Sarvam enrichment
            enrichment_threshold: Min confidence before API call (0.0-1.0)
        """
        self.interface = interface
        self.enrichment_threshold = enrichment_threshold
        self.running = True
        
        logger.info("Initializing enhanced monitoring components...")
        
        # Core components
        self.capture = DNSPacketCapture(interface=interface)
        self.logger = DNSLogger()
        self.categorizer = DomainCategorizer()
        self.intelligence_db = DomainIntelligenceDB()
        self.sarvam = SarvamEnrichment() if enable_enrichment else None
        self.session_manager = SessionManager()
        
        # Create enrichment pipeline
        self.enrichment_pipeline = EnrichmentPipeline(
            self.categorizer,
            self.intelligence_db,
            self.sarvam
        )
        
        # Event detector
        self.event_detector = SuspiciousEventDetector(
            ai_domains=self.categorizer.get_ai_domains(),
            burst_threshold=3,
            burst_window_seconds=10
        )
        
        # Statistics
        self.stats = {
            'total_domains': 0,
            'rule_based_categorized': 0,
            'cached_hits': 0,
            'api_enriched': 0,
            'unknown_domains': 0,
            'events_generated': 0
        }
        
        logger.info("Enhanced orchestrator initialized successfully")
    
    def _process_domain(self, domain: str, timestamp: str, src_ip: Optional[str] = None):
        """
        Process domain through complete enrichment pipeline.
        
        Args:
            domain: Domain name
            timestamp: ISO format timestamp
            src_ip: Source IP for session mapping
        """
        # Session mapping
        session_id = None
        if src_ip:
            session = self.session_manager.get_session_by_ip(src_ip)
            if session:
                session_id = session[0]
                
        # Enrich through pipeline
        category, confidence, source = self.enrichment_pipeline.enrich(domain)
        
        # Update statistics
        self.stats['total_domains'] += 1
        if source == 'rule-based':
            self.stats['rule_based_categorized'] += 1
        elif source == 'sarvam-2b':
            self.stats['api_enriched'] += 1
        elif category == 'Unknown':
            self.stats['unknown_domains'] += 1
        else:
            self.stats['cached_hits'] += 1
        
        # Log to main database
        self.logger.log_dns_query(
            domain=domain,
            timestamp=timestamp,
            source_ip=src_ip,
            category=category,
            source=source,
            confidence=confidence,
            session_id=session_id
        )
        
        # Detect events
        events = self.event_detector.detect_events(domain, timestamp)
        
        for event in events:
            self.logger.log_suspicious_event(
                event_type=event['event_type'],
                domain=event.get('domain'),
                count=event.get('count', 1),
                first_seen=timestamp,
                last_seen=timestamp,
                details=event.get('details'),
                session_id=session_id
            )
            
            self.stats['events_generated'] += 1
            
            # Print alert
            severity = event.get('severity', 'INFO')
            print(f"\n⚠️  EVENT: {event['event_type']} ({severity})")
            if event.get('domain'):
                print(f"   Domain: {event['domain']}")
            if event.get('details'):
                print(f"   Details: {event['details'].get('reason', '')}")
            print()
    
    def _run_capture_thread(self):
        """Run packet capture with enrichment pipeline."""
        try:
            import pyshark
            
            print("\n" + "="*70)
            print("DNS MONITORING ORCHESTRATOR - CHUNK 3 (WITH ENRICHMENT)")
            print("="*70)
            print(f"Interface: {self.interface}")
            print(f"Components: Capture, Categorizer, Intelligence DB, Sarvam API, Logger")
            print(f"Enrichment: {'Enabled' if self.sarvam and self.sarvam.enabled else 'Disabled'}")
            print("Listening for DNS traffic (Ctrl+C to stop)...\n")
            
            # Optimize LiveCapture for long-running stability
            # Set a small packet_count to allow periodic cleanup if needed
            capture_obj = pyshark.LiveCapture(
                interface=self.interface,
                display_filter='dns',
                use_json=True,
                include_raw=False
            )
            
            # Use a generator with a timeout check
            for packet in capture_obj.sniff_continuously():
                if not self.running:
                    capture_obj.close()
                    break
                
                self.capture.packet_count += 1
                
                # Extract domains
                extracted_data = self.capture._extract_dns_domains(packet)
                
                for item in extracted_data:
                    domain = item['domain']
                    src_ip = item['src_ip']
                    
                    # Skip duplicates
                    if self.capture._is_duplicate(domain, src_ip):
                        continue
                    
                    self.capture.domain_count += 1
                    timestamp = datetime.now().isoformat()
                    
                    # Enrich domain
                    category, confidence, source = self.enrichment_pipeline.enrich(domain)
                    
                    # Print to console
                    time_str = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
                    source_indicator = {
                        'rule-based': '⚡',
                        'sarvam-2b': '🤖',
                        'Unknown': '❓'
                    }.get(source, '💾')
                    
                    src_ip_str = f"[{src_ip}] " if src_ip else ""
                    print(f"[{time_str}] {src_ip_str}{source_indicator} {domain:40} {category:20} (conf: {confidence:.2f})")
                    
                    # Process through pipeline
                    self._process_domain(domain, timestamp, src_ip)
        
        except PermissionError:
            logger.error("ERROR: Requires root/sudo privileges")
            logger.error("Run with: sudo python3 monitor_v3.py")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Capture thread error: {str(e)}")
    
    def start(self):
        """Start monitoring."""
        try:
            self._run_capture_thread()
        
        except KeyboardInterrupt:
            self._shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            self._shutdown()
    
    def _shutdown(self):
        """Graceful shutdown with reporting."""
        logger.info("Shutting down enhanced orchestrator...")
        self.running = False
        
        # Log session statistics
        self.logger.log_session_statistics(
            session_start=self.capture.start_time.isoformat(),
            session_end=datetime.now().isoformat(),
            total_packets=self.capture.packet_count,
            unique_domains=self.stats['total_domains'],
            malformed_packets=self.capture.malformed_count,
            errors=self.capture.error_count
        )
        
        # Export reports
        main_report = self.logger.export_session_report()
        intelligence_report = self.intelligence_db.export_intelligence()
        
        # Print statistics
        print("\n" + "="*70)
        print("ENHANCED MONITORING SESSION COMPLETE")
        print("="*70)
        
        print(f"\nCapture Statistics:")
        print(f"  Total Packets: {self.capture.packet_count}")
        print(f"  Total Domains: {self.stats['total_domains']}")
        print(f"  Rule-Based Categorized: {self.stats['rule_based_categorized']}")
        print(f"  Cached Hits: {self.stats['cached_hits']}")
        print(f"  API Enriched: {self.stats['api_enriched']}")
        print(f"  Unknown Domains: {self.stats['unknown_domains']}")
        print(f"  Events Generated: {self.stats['events_generated']}")
        
        print(f"\nEnrichment Pipeline Statistics:")
        pipeline_stats = self.enrichment_pipeline.get_statistics()
        print(f"  Total Processed: {pipeline_stats['total_processed']}")
        print(f"  API Calls Made: {pipeline_stats['sarvam_stats']['api_calls_made']}")
        print(f"  Total Tokens Used: {pipeline_stats['sarvam_stats']['total_tokens_used']}")
        
        print(f"\nIntelligence Database Statistics:")
        db_stats = self.intelligence_db.get_statistics()
        print(f"  Total Domains Stored: {db_stats['total_domains']}")
        for category, count in db_stats['by_category'].items():
            print(f"    {category}: {count}")
        
        print(f"\nData Storage:")
        print(f"  Main Report: {main_report}")
        print(f"  Intelligence Report: {intelligence_report}")
        
        logger.info("Enhanced monitoring session ended successfully")
        print("="*70 + "\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='DNS Monitoring Orchestrator - Chunk 3 with Enrichment'
    )
    parser.add_argument(
        '--interface',
        default='any',
        help='Network interface to monitor (default: any)'
    )
    parser.add_argument(
        '--no-enrichment',
        action='store_true',
        help='Disable Sarvam API enrichment'
    )
    parser.add_argument(
        '--enrichment-threshold',
        type=float,
        default=0.0,
        help='Min confidence before API call (0.0-1.0)'
    )
    
    args = parser.parse_args()
    
    orchestrator = EnhancedMonitoringOrchestrator(
        interface=args.interface,
        enable_enrichment=not args.no_enrichment,
        enrichment_threshold=args.enrichment_threshold
    )
    orchestrator.start()


if __name__ == "__main__":
    main()
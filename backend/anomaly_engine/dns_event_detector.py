#!/usr/bin/env python3
"""
Suspicious Event Detection Module - Chunk 2 Implementation
Generates events for suspicious domain patterns (bursts, repeated AI access, etc).
Rule-based detection with NO machine learning.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from enum import Enum

logger = logging.getLogger("SuspiciousEventDetector")


class SuspiciousEventType(Enum):
    """Types of suspicious events."""
    AI_DOMAIN_BURST = "AI_DOMAIN_BURST"
    BROWSING_BURST = "BROWSING_BURST"
    REPEATED_AI_DOMAIN = "REPEATED_AI_DOMAIN"
    SUSPICIOUS_DOMAIN = "SUSPICIOUS_DOMAIN"
    DOMAIN_SWITCHING = "DOMAIN_SWITCHING"
    RAPID_QUERIES = "RAPID_QUERIES"


class SuspiciousEventDetector:
    """
    Detects suspicious patterns in DNS query streams.
    Rule-based, deterministic, no ML.
    """
    
    def __init__(
        self,
        ai_domains: set,
        burst_threshold: int = 3,
        burst_window_seconds: int = 10,
        rapid_query_threshold: int = 10,
        rapid_query_window_seconds: int = 5
    ):
        """
        Initialize event detector with thresholds.
        
        Args:
            ai_domains: Set of known AI assistant domains
            burst_threshold: Min queries to trigger burst event
            burst_window_seconds: Time window for burst detection
            rapid_query_threshold: Min queries for rapid threshold
            rapid_query_window_seconds: Time window for rapid queries
        """
        self.ai_domains = ai_domains
        self.burst_threshold = burst_threshold
        self.burst_window_seconds = burst_window_seconds
        self.rapid_query_threshold = rapid_query_threshold
        self.rapid_query_window_seconds = rapid_query_window_seconds
        
        # Tracking
        self.recent_queries: List[Tuple[str, datetime]] = []
        self.ai_domain_access: Dict[str, List[datetime]] = defaultdict(list)
        self.domain_access_counts: Dict[str, int] = defaultdict(int)
        
        logger.info("SuspiciousEventDetector initialized")
    
    def _is_ai_domain(self, domain: str) -> bool:
        """
        Check if domain is in AI domain set.
        
        Args:
            domain: Domain to check
            
        Returns:
            True if AI domain
        """
        domain_lower = domain.lower()
        
        # Exact match
        if domain_lower in self.ai_domains:
            return True
        
        # Partial match
        for ai_domain in self.ai_domains:
            if domain_lower.endswith('.' + ai_domain) or domain_lower.endswith(ai_domain):
                return True
        
        return False
    
    def _prune_old_entries(self, now: datetime):
        """
        Remove old entries from tracking structures.
        
        Args:
            now: Current datetime
        """
        # Prune recent queries
        cutoff = now - timedelta(seconds=max(
            self.burst_window_seconds,
            self.rapid_query_window_seconds
        ) * 2)
        
        self.recent_queries = [
            (domain, timestamp)
            for domain, timestamp in self.recent_queries
            if timestamp > cutoff
        ]
        
        # Prune AI domain access
        cutoff = now - timedelta(seconds=self.burst_window_seconds * 3)
        for domain in list(self.ai_domain_access.keys()):
            self.ai_domain_access[domain] = [
                timestamp for timestamp in self.ai_domain_access[domain]
                if timestamp > cutoff
            ]
    
    def detect_events(
        self,
        domain: str,
        timestamp: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze a domain query for suspicious patterns.
        Returns list of detected events.
        
        Args:
            domain: Domain being queried
            timestamp: ISO format timestamp (defaults to now)
            
        Returns:
            List of detected event dictionaries
        """
        if timestamp is None:
            now = datetime.now()
        else:
            now = datetime.fromisoformat(timestamp)
        
        events = []
        
        # Prune old entries
        self._prune_old_entries(now)
        
        # Add to recent queries
        self.recent_queries.append((domain, now))
        self.domain_access_counts[domain] += 1
        
        # Check if AI domain
        is_ai = self._is_ai_domain(domain)
        
        if is_ai:
            self.ai_domain_access[domain].append(now)
            
            # Detect: Repeated AI domain access
            ai_access_count = len(self.ai_domain_access[domain])
            if ai_access_count >= 5:
                events.append({
                    'event_type': SuspiciousEventType.REPEATED_AI_DOMAIN.value,
                    'domain': domain,
                    'count': ai_access_count,
                    'severity': 'MEDIUM',
                    'details': {
                        'reason': f'{domain} accessed {ai_access_count} times',
                        'domain_type': 'AI Assistant'
                    }
                })
            
            # Detect: AI domain burst
            ai_burst = self._detect_ai_burst(now)
            if ai_burst:
                events.append(ai_burst)
        
        # Detect: General browsing burst
        burst_event = self._detect_browsing_burst(now)
        if burst_event:
            events.append(burst_event)
        
        # Detect: Rapid queries
        rapid_event = self._detect_rapid_queries(now)
        if rapid_event:
            events.append(rapid_event)
        
        # Detect: Domain switching pattern
        switch_event = self._detect_domain_switching(now)
        if switch_event:
            events.append(switch_event)
        
        return events
    
    def _detect_ai_burst(self, now: datetime) -> Optional[Dict]:
        """
        Detect burst of AI assistant domain access.
        
        Args:
            now: Current datetime
            
        Returns:
            Event dict if detected, None otherwise
        """
        window_start = now - timedelta(seconds=self.burst_window_seconds)
        
        # Count AI domain accesses in window
        ai_count = 0
        for domain in self.ai_domain_access:
            recent = [
                ts for ts in self.ai_domain_access[domain]
                if ts > window_start
            ]
            ai_count += len(recent)
        
        if ai_count >= self.burst_threshold:
            return {
                'event_type': SuspiciousEventType.AI_DOMAIN_BURST.value,
                'count': ai_count,
                'severity': 'HIGH',
                'window_seconds': self.burst_window_seconds,
                'details': {
                    'reason': f'{ai_count} AI domain queries in {self.burst_window_seconds}s',
                    'threshold': self.burst_threshold
                }
            }
        
        return None
    
    def _detect_browsing_burst(self, now: datetime) -> Optional[Dict]:
        """
        Detect general browsing burst (many domains in short time).
        
        Args:
            now: Current datetime
            
        Returns:
            Event dict if detected, None otherwise
        """
        window_start = now - timedelta(seconds=self.burst_window_seconds)
        
        # Count unique domains in window
        domains_in_window = set()
        for domain, timestamp in self.recent_queries:
            if timestamp > window_start:
                domains_in_window.add(domain)
        
        # Burst is many unique domains
        if len(domains_in_window) >= self.burst_threshold * 2:
            return {
                'event_type': SuspiciousEventType.BROWSING_BURST.value,
                'count': len(domains_in_window),
                'severity': 'LOW',
                'window_seconds': self.burst_window_seconds,
                'details': {
                    'reason': f'{len(domains_in_window)} unique domains in {self.burst_window_seconds}s',
                    'domains': list(domains_in_window)[:5]  # First 5
                }
            }
        
        return None
    
    def _detect_rapid_queries(self, now: datetime) -> Optional[Dict]:
        """
        Detect rapid query rate (many queries in very short time).
        
        Args:
            now: Current datetime
            
        Returns:
            Event dict if detected, None otherwise
        """
        window_start = now - timedelta(seconds=self.rapid_query_window_seconds)
        
        # Count queries in rapid window
        rapid_count = sum(
            1 for domain, timestamp in self.recent_queries
            if timestamp > window_start
        )
        
        if rapid_count >= self.rapid_query_threshold:
            return {
                'event_type': SuspiciousEventType.RAPID_QUERIES.value,
                'count': rapid_count,
                'severity': 'MEDIUM',
                'window_seconds': self.rapid_query_window_seconds,
                'details': {
                    'reason': f'{rapid_count} queries in {self.rapid_query_window_seconds}s',
                    'rate_per_second': f'{rapid_count / self.rapid_query_window_seconds:.1f}'
                }
            }
        
        return None
    
    def _detect_domain_switching(self, now: datetime) -> Optional[Dict]:
        """
        Detect rapid switching between different domains.
        
        Args:
            now: Current datetime
            
        Returns:
            Event dict if detected, None otherwise
        """
        window_start = now - timedelta(seconds=self.burst_window_seconds)
        
        # Get recent queries in order
        recent = [
            domain for domain, timestamp in self.recent_queries
            if timestamp > window_start
        ]
        
        if len(recent) < 4:
            return None
        
        # Count domain changes (switching between different domains)
        switches = 0
        for i in range(1, len(recent)):
            if recent[i] != recent[i-1]:
                switches += 1
        
        # High switching ratio indicates alternating between domains
        if len(recent) > 0:
            switch_ratio = switches / len(recent)
            if switch_ratio > 0.6 and switches >= 3:  # High switching activity
                return {
                    'event_type': SuspiciousEventType.DOMAIN_SWITCHING.value,
                    'count': switches,
                    'severity': 'LOW',
                    'window_seconds': self.burst_window_seconds,
                    'details': {
                        'reason': f'Rapid switching between {len(set(recent))} domains',
                        'switch_count': switches,
                        'unique_domains': len(set(recent))
                    }
                }
        
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get detector statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_queries_tracked': len(self.recent_queries),
            'unique_domains_accessed': len(self.domain_access_counts),
            'ai_domains_accessed': len(self.ai_domain_access),
            'most_accessed': self._get_most_accessed(5)
        }
    
    def _get_most_accessed(self, limit: int = 5) -> List[Tuple[str, int]]:
        """
        Get most accessed domains.
        
        Args:
            limit: Number of top domains
            
        Returns:
            List of (domain, count) tuples
        """
        sorted_domains = sorted(
            self.domain_access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_domains[:limit]


if __name__ == "__main__":
    # Test detector
    logging.basicConfig(level=logging.INFO)
    
    ai_domains = {
        'chat.openai.com',
        'openai.com',
        'claude.ai',
        'anthropic.com',
        'gemini.google.com'
    }
    
    detector = SuspiciousEventDetector(
        ai_domains=ai_domains,
        burst_threshold=3,
        burst_window_seconds=10
    )
    
    print("\n" + "="*60)
    print("SUSPICIOUS EVENT DETECTION TEST")
    print("="*60)
    
    # Simulate rapid AI domain access
    now = datetime.now()
    test_queries = [
        ('google.com', now),
        ('chat.openai.com', now),
        ('github.com', now + timedelta(seconds=1)),
        ('chat.openai.com', now + timedelta(seconds=2)),
        ('claude.ai', now + timedelta(seconds=3)),
        ('chat.openai.com', now + timedelta(seconds=4)),
    ]
    
    print("\nSimulating query stream...")
    for domain, timestamp in test_queries:
        events = detector.detect_events(domain, timestamp.isoformat())
        print(f"\n[{timestamp.strftime('%H:%M:%S')}] {domain}")
        if events:
            for event in events:
                print(f"  ⚠️  {event['event_type']} (Severity: {event['severity']})")
        else:
            print(f"  ✓ No events")
    
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

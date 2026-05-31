#!/usr/bin/env python3
"""
DNS Logger Module - Chunk 2 Implementation
Stores captured DNS metadata to JSON and SQLite for persistence and analysis.
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import logging
import threading

logger = logging.getLogger("DNSLogger")


class DNSLogger:
    """
    Logs DNS metadata to both JSON and SQLite.
    Provides lightweight storage without machine learning.
    """
    
    def __init__(
        self,
        log_dir: str = "./dns_logs",
        db_name: str = "dns_capture.db",
        json_name: str = "dns_queries.jsonl"
    ):
        """
        Initialize DNS logger.
        
        Args:
            log_dir: Directory for log files
            db_name: SQLite database filename
            json_name: JSONL log filename
        """
        self.log_dir = Path(log_dir)
        self.db_path = self.log_dir / db_name
        self.json_path = self.log_dir / json_name
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"DNSLogger initialized - Log dir: {self.log_dir}")
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create DNS queries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dns_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    source_ip TEXT,
                    query_type TEXT DEFAULT 'A',
                    protocol TEXT DEFAULT 'UDP',
                    category TEXT,
                    source TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    UNIQUE(timestamp, domain, source_ip)
                )
            ''')
            
            # Create suspicious events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suspicious_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    domain TEXT,
                    count INTEGER,
                    first_seen TEXT,
                    last_seen TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT
                )
            ''')
            
            for table in ['dns_queries', 'suspicious_events']:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN session_id TEXT")
                except sqlite3.OperationalError:
                    pass
            
            # Create statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capture_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_start TEXT NOT NULL,
                    session_end TEXT,
                    total_packets INTEGER,
                    unique_domains INTEGER,
                    malformed_packets INTEGER,
                    errors INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized: {self.db_path}")
        
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def log_dns_query(
        self,
        domain: str,
        timestamp: str,
        source_ip: Optional[str] = None,
        query_type: str = 'A',
        protocol: str = 'UDP',
        category: Optional[str] = None,
        source: Optional[str] = None,
        confidence: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Log a DNS query to database and JSON.
        
        Args:
            domain: Queried domain
            timestamp: ISO format timestamp
            source_ip: Source IP address (if available)
            query_type: DNS query type (A, AAAA, MX, etc.)
            protocol: Transport protocol (UDP, TCP)
            category: Domain category (set by categorizer)
            
        Returns:
            True if logged successfully
        """
        try:
            with self.lock:
                # Log to SQLite
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO dns_queries
                    (timestamp, domain, source_ip, query_type, protocol, category, source, confidence, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, domain, source_ip, query_type, protocol, category, source, confidence, session_id))
                
                conn.commit()
                conn.close()
                
                # Log to JSONL
                record = {
                    'timestamp': timestamp,
                    'domain': domain,
                    'source_ip': source_ip,
                    'query_type': query_type,
                    'protocol': protocol,
                    'category': category,
                    'source': source,
                    'confidence': confidence,
                    'session_id': session_id
                }
                
                with open(self.json_path, 'a') as f:
                    f.write(json.dumps(record) + '\n')
                
                return True
        
        except Exception as e:
            logger.error(f"Error logging DNS query: {str(e)}")
            return False
    
    def log_suspicious_event(
        self,
        event_type: str,
        domain: Optional[str] = None,
        count: int = 1,
        first_seen: Optional[str] = None,
        last_seen: Optional[str] = None,
        details: Optional[dict] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Log a suspicious event.
        
        Args:
            event_type: Type of event (e.g., 'AI_DOMAIN_BURST', 'SUSPICIOUS_DOMAIN')
            domain: Associated domain (if applicable)
            count: Occurrence count
            first_seen: First occurrence timestamp
            last_seen: Last occurrence timestamp
            details: Additional details as dict
            
        Returns:
            True if logged successfully
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                details_json = json.dumps(details) if details else None
                
                cursor.execute('''
                    INSERT INTO suspicious_events
                    (event_type, domain, count, first_seen, last_seen, details, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (event_type, domain, count, first_seen, last_seen, details_json, session_id))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Suspicious event logged: {event_type} - {domain}")
                return True
        
        except Exception as e:
            logger.error(f"Error logging suspicious event: {str(e)}")
            return False
    
    def log_session_statistics(
        self,
        session_start: str,
        total_packets: int,
        unique_domains: int,
        malformed_packets: int = 0,
        errors: int = 0,
        session_end: Optional[str] = None
    ) -> bool:
        """
        Log session statistics.
        
        Args:
            session_start: Session start timestamp
            total_packets: Total packets processed
            unique_domains: Unique domains captured
            malformed_packets: Count of malformed packets
            errors: Count of errors
            session_end: Session end timestamp
            
        Returns:
            True if logged successfully
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                if session_end is None:
                    session_end = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO capture_statistics
                    (session_start, session_end, total_packets, unique_domains,
                     malformed_packets, errors)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_start, session_end, total_packets, unique_domains,
                      malformed_packets, errors))
                
                conn.commit()
                conn.close()
                
                logger.info("Session statistics logged")
                return True
        
        except Exception as e:
            logger.error(f"Error logging session statistics: {str(e)}")
            return False
    
    def get_recent_domains(self, limit: int = 100) -> List[Dict]:
        """
        Get recently captured domains.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of domain query dicts
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, domain, source_ip, query_type, protocol, category
                FROM dns_queries
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': row[0],
                    'domain': row[1],
                    'source_ip': row[2],
                    'query_type': row[3],
                    'protocol': row[4],
                    'category': row[5]
                }
                for row in rows
            ]
        
        except Exception as e:
            logger.error(f"Error retrieving recent domains: {str(e)}")
            return []
    
    def get_domain_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with query and event counts
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute('SELECT COUNT(DISTINCT domain) FROM dns_queries')
            unique_domains = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM dns_queries')
            total_queries = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM suspicious_events')
            suspicious_events = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'unique_domains': unique_domains,
                'total_queries': total_queries,
                'suspicious_events': suspicious_events
            }
        
        except Exception as e:
            logger.error(f"Error retrieving statistics: {str(e)}")
            return {}
    
    def get_suspicious_events(self, limit: int = 50, session_id: Optional[str] = None) -> List[Dict]:
        """
        Get recent suspicious events.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute('''
                    SELECT event_type, domain, count, first_seen, last_seen, details
                    FROM suspicious_events
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (session_id, limit))
            else:
                cursor.execute('''
                    SELECT event_type, domain, count, first_seen, last_seen, details
                    FROM suspicious_events
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
                
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'event_type': row[0],
                    'domain': row[1],
                    'count': row[2],
                    'first_seen': row[3],
                    'last_seen': row[4],
                    'details': json.loads(row[5]) if row[5] else None
                }
                for row in rows
            ]
        
        except Exception as e:
            logger.error(f"Error retrieving suspicious events: {str(e)}")
            return []
    
    def export_session_report(self, output_path: Optional[str] = None) -> str:
        """
        Export complete session report as JSON.
        
        Args:
            output_path: Custom output path (optional)
            
        Returns:
            Path to exported report
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = str(self.log_dir / f"report_{timestamp}.json")
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'statistics': self.get_domain_stats(),
                'recent_domains': self.get_recent_domains(limit=500),
                'suspicious_events': self.get_suspicious_events(limit=100)
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Session report exported: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error exporting session report: {str(e)}")
            return ""


if __name__ == "__main__":
    # Test logger
    logger_instance = DNSLogger()
    
    # Test logging
    logger_instance.log_dns_query(
        domain="google.com",
        timestamp=datetime.now().isoformat(),
        category="Search Engine"
    )
    
    logger_instance.log_suspicious_event(
        event_type="TEST_EVENT",
        domain="test.com",
        details={'reason': 'Test'}
    )
    
    # Print stats
    print(logger_instance.get_domain_stats())

#!/usr/bin/env python3
"""
Domain Intelligence Database - Chunk 3
Maintains local SQLite cache of domain classifications.
Optimizes API usage by reusing cached results.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import threading

logger = logging.getLogger("DomainIntelligenceDB")


class DomainIntelligenceDB:
    """
    Local intelligence database for domain classifications.
    Provides:
    - Caching of known domains
    - Reuse of previous classifications
    - Tracking of enrichment sources
    - Confidence scoring
    """
    
    def __init__(self, db_path: str = "./dns_logs/domain_intelligence.db"):
        """
        Initialize intelligence database.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        
        self._init_database()
        logger.info(f"DomainIntelligenceDB initialized - {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Domains table - stores all discovered domains and their classifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    reasoning TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    times_detected INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for fast lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_domain ON domains(domain)
            ''')
            
            # Enrichment log - tracks API calls and results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enrichment_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    previous_category TEXT,
                    new_category TEXT NOT NULL,
                    api_response TEXT,
                    cost_tokens INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_domains INTEGER,
                    known_domains INTEGER,
                    unknown_domains INTEGER,
                    api_calls_made INTEGER,
                    cached_hits INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
        
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def get_domain(self, domain: str) -> Optional[Dict]:
        """
        Retrieve cached domain classification.
        
        Args:
            domain: Domain name
            
        Returns:
            Domain info dict or None if not found
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT domain, category, confidence, source, reasoning, 
                           first_seen, last_seen, times_detected
                    FROM domains WHERE domain = ?
                ''', (domain.lower(),))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return {
                        'domain': row[0],
                        'category': row[1],
                        'confidence': row[2],
                        'source': row[3],
                        'reasoning': row[4],
                        'first_seen': row[5],
                        'last_seen': row[6],
                        'times_detected': row[7]
                    }
                
                return None
        
        except Exception as e:
            logger.error(f"Error retrieving domain: {str(e)}")
            return None
    
    def store_domain(
        self,
        domain: str,
        category: str,
        confidence: float,
        source: str,
        reasoning: Optional[str] = None
    ) -> bool:
        """
        Store or update domain classification.
        
        Args:
            domain: Domain name
            category: Classification category
            confidence: Confidence score (0.0-1.0)
            source: Source of classification (rule-based, sarvam-2b, etc.)
            reasoning: Explanation for classification
            
        Returns:
            True if successful
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                domain_lower = domain.lower()
                
                # Check if domain exists
                cursor.execute('SELECT id FROM domains WHERE domain = ?', (domain_lower,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing
                    cursor.execute('''
                        UPDATE domains
                        SET category = ?, confidence = ?, source = ?, 
                            reasoning = ?, last_seen = ?, 
                            times_detected = times_detected + 1,
                            updated_at = ?
                        WHERE domain = ?
                    ''', (category, confidence, source, reasoning, now, now, domain_lower))
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO domains
                        (domain, category, confidence, source, reasoning, 
                         first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (domain_lower, category, confidence, source, reasoning, now, now))
                
                conn.commit()
                conn.close()
                return True
        
        except Exception as e:
            logger.error(f"Error storing domain: {str(e)}")
            return False
    
    def log_enrichment(
        self,
        domain: str,
        previous_category: Optional[str],
        new_category: str,
        api_response: Optional[str] = None,
        cost_tokens: int = 0
    ) -> bool:
        """
        Log an enrichment event (API call result).
        
        Args:
            domain: Domain that was enriched
            previous_category: Category before enrichment
            new_category: New category from API
            api_response: Raw API response
            cost_tokens: Token cost of API call
            
        Returns:
            True if successful
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO enrichment_log
                    (domain, previous_category, new_category, api_response, cost_tokens)
                    VALUES (?, ?, ?, ?, ?)
                ''', (domain.lower(), previous_category, new_category, api_response, cost_tokens))
                
                conn.commit()
                conn.close()
                logger.info(f"Enrichment logged: {domain} → {new_category}")
                return True
        
        except Exception as e:
            logger.error(f"Error logging enrichment: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict:
        """
        Get intelligence database statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Total domains
                cursor.execute('SELECT COUNT(*) FROM domains')
                total = cursor.fetchone()[0]
                
                # By category
                cursor.execute('''
                    SELECT category, COUNT(*) FROM domains 
                    GROUP BY category ORDER BY COUNT(*) DESC
                ''')
                by_category = {row[0]: row[1] for row in cursor.fetchall()}
                
                # API enrichments
                cursor.execute('SELECT COUNT(*) FROM enrichment_log')
                api_calls = cursor.fetchone()[0]
                
                # Total tokens used
                cursor.execute('SELECT COALESCE(SUM(cost_tokens), 0) FROM enrichment_log')
                total_tokens = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_domains': total,
                    'by_category': by_category,
                    'api_calls_made': api_calls,
                    'total_tokens_used': total_tokens
                }
        
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    def get_unknown_domains(self, limit: int = 50) -> List[str]:
        """
        Get domains marked as UNKNOWN.
        Useful for batch enrichment.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of unknown domain names
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT domain FROM domains 
                    WHERE category = 'Unknown'
                    ORDER BY last_seen DESC
                    LIMIT ?
                ''', (limit,))
                
                domains = [row[0] for row in cursor.fetchall()]
                conn.close()
                return domains
        
        except Exception as e:
            logger.error(f"Error getting unknown domains: {str(e)}")
            return []
    
    def get_high_confidence_domains(self, min_confidence: float = 0.8) -> List[Dict]:
        """
        Get domains with high confidence classification.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of high-confidence domain dicts
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT domain, category, confidence, source, times_detected
                    FROM domains
                    WHERE confidence >= ?
                    ORDER BY times_detected DESC
                    LIMIT 100
                ''', (min_confidence,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [
                    {
                        'domain': row[0],
                        'category': row[1],
                        'confidence': row[2],
                        'source': row[3],
                        'times_detected': row[4]
                    }
                    for row in rows
                ]
        
        except Exception as e:
            logger.error(f"Error getting high-confidence domains: {str(e)}")
            return []
    
    def get_enrichment_log(self, limit: int = 50) -> List[Dict]:
        """
        Get recent enrichment events.
        
        Args:
            limit: Maximum number of events
            
        Returns:
            List of enrichment event dicts
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT domain, previous_category, new_category, 
                           cost_tokens, created_at
                    FROM enrichment_log
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [
                    {
                        'domain': row[0],
                        'previous_category': row[1],
                        'new_category': row[2],
                        'cost_tokens': row[3],
                        'created_at': row[4]
                    }
                    for row in rows
                ]
        
        except Exception as e:
            logger.error(f"Error getting enrichment log: {str(e)}")
            return []
    
    def export_intelligence(self, output_path: Optional[str] = None) -> str:
        """
        Export complete intelligence database as JSON.
        
        Args:
            output_path: Optional custom output path
            
        Returns:
            Path to exported file
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = str(self.db_path.parent / f"intelligence_export_{timestamp}.json")
            
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Get all domains
                cursor.execute('''
                    SELECT domain, category, confidence, source, times_detected
                    FROM domains ORDER BY times_detected DESC
                ''')
                domains = [
                    {
                        'domain': row[0],
                        'category': row[1],
                        'confidence': row[2],
                        'source': row[3],
                        'times_detected': row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get enrichment history
                cursor.execute('''
                    SELECT domain, previous_category, new_category, cost_tokens
                    FROM enrichment_log ORDER BY created_at DESC
                ''')
                enrichments = [
                    {
                        'domain': row[0],
                        'previous': row[1],
                        'new': row[2],
                        'tokens': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                conn.close()
            
            export = {
                'exported_at': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'domains': domains,
                'enrichments': enrichments
            }
            
            with open(output_path, 'w') as f:
                json.dump(export, f, indent=2)
            
            logger.info(f"Intelligence exported to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error exporting intelligence: {str(e)}")
            return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    db = DomainIntelligenceDB()
    
    # Test storage
    db.store_domain(
        'google.com',
        'Search Engine',
        1.0,
        'rule-based',
        'Hardcoded rule match'
    )
    
    db.store_domain(
        'supergptcoder.ai',
        'AI Assistant',
        0.89,
        'sarvam-2b',
        'Domain name suggests AI coding assistant'
    )
    
    # Test retrieval
    result = db.get_domain('google.com')
    print("Retrieved:", result)
    
    # Test stats
    print("Stats:", db.get_statistics())
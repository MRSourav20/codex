#!/usr/bin/env python3
"""
Sarvam-2B Enrichment Module - Chunk 3
Uses Sarvam-2B API to intelligently classify unknown domains.
Provides adaptive domain enrichment with cost optimization.
"""

import logging
import json
import os
from typing import Optional, Dict, Tuple
from datetime import datetime

logger = logging.getLogger("SarvamEnrichment")


class SarvamEnrichment:
    """
    Uses Sarvam-2B API to enrich unknown domain classifications.
    Provides intelligent categorization for domains not in rule-based lists.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sarvam enrichment.
        
        Args:
            api_key: Sarvam API key (or read from env: SARVAM_API_KEY)
        """
        self.api_key = api_key or os.environ.get('SARVAM_API_KEY')
        
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not found - enrichment disabled")
            self.enabled = False
        else:
            self.enabled = True
        
        self.model = "Sarvam-2B"
        self.base_url = "https://api.sarvam.ai/v1"  # Update with actual Sarvam endpoint
        self.total_tokens_used = 0
        self.total_api_calls = 0
        
        logger.info(f"SarvamEnrichment initialized (enabled: {self.enabled})")
    
    def _build_enrichment_prompt(self, domain: str) -> str:
        """
        Build analysis prompt for Sarvam-2B.
        
        Args:
            domain: Domain to analyze
            
        Returns:
            Prompt string
        """
        return f"""Analyze this domain name: {domain}

Determine:
1. What is the primary purpose/category of this domain?
2. Is it likely an AI assistant or coding helper tool?
3. What is your confidence in this classification?

Respond in JSON format:
{{
    "domain": "{domain}",
    "category": "string (e.g., AI Assistant, Development, Search Engine, Social Media, etc.)",
    "is_ai_related": boolean,
    "is_coding_related": boolean,
    "confidence": float (0.0-1.0),
    "reasoning": "string explaining the classification",
    "keywords": ["list", "of", "relevant", "keywords"]
}}

Be concise but thorough."""
    
    def enrich_domain(self, domain: str) -> Optional[Dict]:
        """
        Enrich unknown domain using Sarvam-2B API.
        
        Args:
            domain: Domain to classify
            
        Returns:
            Dictionary with classification result or None if error
        """
        if not self.enabled:
            logger.warning(f"Enrichment disabled - cannot enrich {domain}")
            return None
        
        try:
            import requests
            
            prompt = self._build_enrichment_prompt(domain)
            
            # Prepare API request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Use Sarvam-2B model
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 500,
                'temperature': 0.3  # Lower temperature for consistency
            }
            
            # Make API call
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # Track token usage
                if 'usage' in result:
                    tokens_used = result['usage'].get('total_tokens', 0)
                    self.total_tokens_used += tokens_used
                
                self.total_api_calls += 1
                
                # Parse JSON response
                try:
                    classification = json.loads(content)
                    classification['source'] = 'sarvam-2b'
                    classification['enriched_at'] = datetime.now().isoformat()
                    return classification
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON response for {domain}")
                    return None
            
            else:
                logger.error(f"Unexpected API response format")
                return None
        
        except ImportError:
            logger.error("requests library not installed - cannot call Sarvam API")
            return None
        except Exception as e:
            logger.error(f"Error enriching domain {domain}: {str(e)}")
            return None
    
    def batch_enrich(
        self,
        domains: list,
        delay_between_calls: float = 1.0
    ) -> Dict[str, Optional[Dict]]:
        """
        Enrich multiple domains with rate limiting.
        
        Args:
            domains: List of domains to enrich
            delay_between_calls: Delay between API calls (seconds)
            
        Returns:
            Dictionary of domain -> classification result
        """
        import time
        
        results = {}
        
        for i, domain in enumerate(domains):
            logger.info(f"Enriching {i+1}/{len(domains)}: {domain}")
            
            classification = self.enrich_domain(domain)
            results[domain] = classification
            
            # Rate limiting (except for last call)
            if i < len(domains) - 1:
                time.sleep(delay_between_calls)
        
        return results
    
    def get_statistics(self) -> Dict:
        """
        Get enrichment statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'api_calls_made': self.total_api_calls,
            'total_tokens_used': self.total_tokens_used,
            'avg_tokens_per_call': (
                self.total_tokens_used / self.total_api_calls
                if self.total_api_calls > 0 else 0
            ),
            'enabled': self.enabled
        }
    
    @staticmethod
    def estimate_cost(tokens_used: int) -> float:
        """
        Estimate cost based on token usage.
        Note: Update pricing based on actual Sarvam rates.
        
        Args:
            tokens_used: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Example: $0.001 per 1K tokens
        # Update based on actual Sarvam pricing
        cost_per_1k_tokens = 0.001
        return (tokens_used / 1000) * cost_per_1k_tokens


class EnrichmentPipeline:
    """
    Complete enrichment pipeline.
    Orchestrates: Rule-based → Local DB → Sarvam API → Store result
    """
    
    def __init__(
        self,
        categorizer,
        intelligence_db,
        sarvam_enrichment
    ):
        """
        Initialize enrichment pipeline.
        
        Args:
            categorizer: DomainCategorizer instance
            intelligence_db: DomainIntelligenceDB instance
            sarvam_enrichment: SarvamEnrichment instance
        """
        self.categorizer = categorizer
        self.intelligence_db = intelligence_db
        self.sarvam = sarvam_enrichment
        
        self.stats = {
            'total_processed': 0,
            'rule_based_hits': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'unknown_remaining': 0
        }
        
        logger.info("EnrichmentPipeline initialized")
    
    def enrich(self, domain: str, force_api: bool = False) -> Tuple[str, float, str]:
        """
        Enrich a domain through complete pipeline.
        
        Args:
            domain: Domain to enrich
            force_api: If True, force API call even if cached
            
        Returns:
            (category, confidence, source) tuple
        """
        self.stats['total_processed'] += 1
        
        # Stage 1: Check local cache (if not forced API)
        if not force_api:
            cached = self.intelligence_db.get_domain(domain)
            if cached:
                self.stats['cache_hits'] += 1
                return (
                    cached['category'],
                    cached['confidence'],
                    cached['source']
                )
        
        # Stage 2: Rule-based categorization
        category, confidence = self.categorizer.categorize(domain)
        
        if category.value != "Unknown":
            self.stats['rule_based_hits'] += 1
            # Store in DB
            self.intelligence_db.store_domain(
                domain,
                category.value,
                confidence,
                'rule-based'
            )
            return (category.value, confidence, 'rule-based')
        
        # Stage 3: Try Sarvam API enrichment
        if self.sarvam.enabled:
            logger.info(f"Calling Sarvam API for unknown domain: {domain}")
            result = self.sarvam.enrich_domain(domain)
            
            if result:
                self.stats['api_calls'] += 1
                
                new_category = result.get('category', 'Unknown')
                confidence = result.get('confidence', 0.5)
                reasoning = result.get('reasoning', '')
                
                # Store enrichment result in DB
                self.intelligence_db.store_domain(
                    domain,
                    new_category,
                    confidence,
                    'sarvam-2b',
                    reasoning
                )
                
                # Log enrichment event
                self.intelligence_db.log_enrichment(
                    domain,
                    'Unknown',
                    new_category,
                    json.dumps(result),
                    result.get('tokens_used', 0)
                )
                
                return (new_category, confidence, 'sarvam-2b')
        
        # Stage 4: Store as unknown and mark for future enrichment
        self.intelligence_db.store_domain(
            domain,
            'Unknown',
            0.0,
            'unknown'
        )
        self.stats['unknown_remaining'] += 1
        
        return ('Unknown', 0.0, 'unknown')
    
    def batch_enrich(self, domains: list) -> Dict[str, Tuple[str, float, str]]:
        """
        Enrich multiple domains through pipeline.
        
        Args:
            domains: List of domains
            
        Returns:
            Dictionary of domain -> (category, confidence, source)
        """
        results = {}
        for domain in domains:
            results[domain] = self.enrich(domain)
        return results
    
    def get_statistics(self) -> Dict:
        """
        Get pipeline statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()
        stats['sarvam_stats'] = self.sarvam.get_statistics()
        stats['db_stats'] = self.intelligence_db.get_statistics()
        return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test Sarvam enrichment
    sarvam = SarvamEnrichment()
    
    print(f"\nSarvam Enrichment Status: {sarvam.enabled}")
    print(f"API Key Present: {'Yes' if sarvam.api_key else 'No'}")
    
    # Note: Actual API call requires valid API key
    if sarvam.enabled:
        print("\nAttempting to enrich unknown domain...")
        result = sarvam.enrich_domain('supergptcoder.ai')
        if result:
            print(json.dumps(result, indent=2))
    else:
        print("\nSet SARVAM_API_KEY environment variable to enable enrichment")
        print("Example: export SARVAM_API_KEY='your-key-here'")
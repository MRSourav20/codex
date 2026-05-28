#!/usr/bin/env python3
"""
Sarvam-m Enrichment Module - FINAL FIXED VERSION
Uses FREE TRIAL model: sarvam-m (lightweight, free tier)
Other available models: sarvam-30b, sarvam-105b (require paid tier)
"""

import logging
import json
import os
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("SarvamEnrichment")


class SarvamEnrichment:
    """
    Uses Sarvam API to enrich unknown domain classifications.
    FINAL VERSION with correct FREE TIER model: sarvam-m
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sarvam enrichment with FREE TRIAL model.
        
        Args:
            api_key: Sarvam API key (or read from env: SARVAM_API_KEY)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('SARVAM_API_KEY')
        
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not found in environment - enrichment disabled")
            logger.warning("Set it with: export SARVAM_API_KEY='your-actual-key'")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"API Key loaded (first 10 chars: {self.api_key[:10]}...)")
        
        # ✅ CORRECT FREE TRIAL MODEL
        self.base_url = "https://api.sarvam.ai/v1"
        self.model = "sarvam-m"  # ✅ FREE TIER - lightweight model
        
        # Other available models (require payment):
        # self.model = "sarvam-30b"   # Larger, more capable
        # self.model = "sarvam-105b"  # Largest, most capable
        
        self.total_tokens_used = 0
        self.total_api_calls = 0
        self.failed_calls = 0
        
        # Session for connection pooling and retry
        self.session = requests.Session()
        
        # Retry strategy
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        logger.info(f"SarvamEnrichment initialized (enabled: {self.enabled}, model: {self.model})")
    
    def _build_enrichment_prompt(self, domain: str) -> str:
        """
        Build analysis prompt - return JSON example only.
        
        Args:
            domain: Domain to analyze
            
        Returns:
            JSON string
        """
        return f'{{"domain":"{domain}","category":"Search","confidence":0.8}}'
    
    def enrich_domain(self, domain: str, retry_count: int = 0) -> Optional[Dict]:
        """
        Enrich unknown domain using Sarvam-m API with retry logic.
        
        Args:
            domain: Domain to classify
            retry_count: Internal retry counter
            
        Returns:
            Dictionary with classification result or None if error
        """
        if not self.enabled:
            logger.warning(f"Enrichment disabled - cannot enrich {domain}")
            return None
        
        try:
            prompt = self._build_enrichment_prompt(domain)
            
            # Correct headers for Sarvam API
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Correct payload with FREE TIER model
            payload = {
                'model': self.model,  # ✅ sarvam-m for free tier
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a JSON classifier. Output ONLY valid JSON. No thinking tags. No explanation. Pure JSON only.'
                    },
                    {
                        'role': 'user',
                        'content': f'Classify {domain}: {prompt}'
                    }
                ],
                'max_tokens': 50,  # Very small - just need JSON
                'temperature': 0.0,  # Deterministic output
                'top_p': 0.95
            }
            
            logger.info(f"Sending enrichment request for: {domain}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Make API call
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            # Log response status
            logger.info(f"API Response Status: {response.status_code}")
            
            # Handle 429 (Rate limit) with retry
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * (retry_count + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    return self.enrich_domain(domain, retry_count + 1)
                else:
                    logger.error(f"Max retries exceeded for {domain}")
                    self.failed_calls += 1
                    return None
            
            # Handle 400 errors
            if response.status_code == 400:
                logger.error(f"400 Bad Request - Check API key and payload format")
                logger.error(f"Response: {response.text}")
                self.failed_calls += 1
                return None
            
            # Handle 401 errors
            if response.status_code == 401:
                logger.error(f"401 Unauthorized - Invalid API key")
                logger.error(f"Response: {response.text}")
                self.enabled = False
                self.failed_calls += 1
                return None
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"API Response: {json.dumps(result, indent=2)}")
            
            # Extract response content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info(f"Raw response content: {content}")
                
                # Track token usage
                if 'usage' in result:
                    tokens_used = result['usage'].get('total_tokens', 0)
                    self.total_tokens_used += tokens_used
                    logger.info(f"Tokens used: {tokens_used}")
                
                self.total_api_calls += 1
                
                # Parse JSON response
                try:
                    # Try to extract JSON from response (first priority)
                    import re
                    # Look for JSON object pattern
                    json_match = re.search(r'\{[^{}]*"domain"[^{}]*\}', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(0)
                        classification = json.loads(json_str)
                    else:
                        # Try direct JSON parsing
                        classification = json.loads(content)
                    
                    # Ensure required fields
                    if 'domain' not in classification:
                        classification['domain'] = domain
                    if 'confidence' not in classification:
                        classification['confidence'] = 0.7
                    if 'category' not in classification:
                        classification['category'] = 'Other'
                    
                    classification['source'] = 'sarvam-m'
                    classification['enriched_at'] = datetime.now().isoformat()
                    
                    logger.info(f"Successfully enriched {domain}: {classification['category']}")
                    return classification
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {str(e)}")
                    logger.error(f"Content was: {content}")
                    # Return fallback - use rule-based default
                    return {
                        'domain': domain,
                        'category': 'Other',
                        'confidence': 0.5,
                        'source': 'sarvam-m-fallback',
                        'reasoning': 'API response parsing failed - using fallback',
                        'enriched_at': datetime.now().isoformat()
                    }
            
            else:
                logger.error(f"Unexpected API response format: {result}")
                self.failed_calls += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"API call timeout for {domain}")
            self.failed_calls += 1
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            self.failed_calls += 1
            return None
        except Exception as e:
            logger.error(f"Error enriching domain {domain}: {str(e)}")
            self.failed_calls += 1
            return None
    
    def batch_enrich(
        self,
        domains: list,
        delay_between_calls: float = 2.0
    ) -> Dict[str, Optional[Dict]]:
        """
        Enrich multiple domains with rate limiting.
        
        Args:
            domains: List of domains to enrich
            delay_between_calls: Delay between API calls (seconds)
            
        Returns:
            Dictionary of domain -> classification result
        """
        results = {}
        
        for i, domain in enumerate(domains):
            logger.info(f"Enriching {i+1}/{len(domains)}: {domain}")
            
            classification = self.enrich_domain(domain)
            results[domain] = classification
            
            # Rate limiting (except for last call)
            if i < len(domains) - 1:
                logger.info(f"Waiting {delay_between_calls}s before next call...")
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
            'failed_calls': self.failed_calls,
            'total_tokens_used': self.total_tokens_used,
            'avg_tokens_per_call': (
                self.total_tokens_used / self.total_api_calls
                if self.total_api_calls > 0 else 0
            ),
            'enabled': self.enabled,
            'model': self.model
        }
    
    @staticmethod
    def estimate_cost(tokens_used: int) -> float:
        """
        Estimate cost based on token usage.
        sarvam-m pricing (free tier): typically included in free quota
        
        Args:
            tokens_used: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Free tier model - no charge or very minimal charge
        # Estimate: $0.00001 per token (usually free)
        cost_per_token = 0.00001
        return tokens_used * cost_per_token
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info("Testing Sarvam API connection...")
            
            result = self.enrich_domain('google.com')
            
            if result:
                logger.info("✓ Connection test successful!")
                logger.info(f"Response: {json.dumps(result, indent=2)}")
                return True
            else:
                logger.error("✗ Connection test failed - no response")
                return False
        
        except Exception as e:
            logger.error(f"✗ Connection test failed: {str(e)}")
            return False


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
            'api_failures': 0,
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
                
                new_category = result.get('category', 'Other')
                confidence = result.get('confidence', 0.5)
                reasoning = result.get('reasoning', '')
                
                # Store enrichment result in DB
                self.intelligence_db.store_domain(
                    domain,
                    new_category,
                    confidence,
                    'sarvam-m',
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
                
                return (new_category, confidence, 'sarvam-m')
            else:
                self.stats['api_failures'] += 1
        
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
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("SARVAM-M ENRICHMENT - CONNECTION TEST (FREE TIER)")
    print("="*70)
    
    # Test Sarvam enrichment
    sarvam = SarvamEnrichment()
    
    print(f"\nSarvam Enrichment Status: {sarvam.enabled}")
    print(f"API Key Present: {'Yes' if sarvam.api_key else 'No'}")
    print(f"Model: {sarvam.model}")
    print(f"Base URL: {sarvam.base_url}")
    print(f"Tier: FREE (lightweight model)")
    
    if not sarvam.enabled:
        print("\n❌ ENRICHMENT DISABLED")
        print("\nTo enable, set your API key:")
        print("  export SARVAM_API_KEY='your-actual-sarvam-api-key'")
        print("\nThen run:")
        print("  python3 sarvam_enrichment.py")
    else:
        print("\n🔄 Running connection test...")
        print("=" * 70)
        
        if sarvam.test_connection():
            print("\n✅ SUCCESS! Sarvam API (sarvam-m) is working!")
            print("   Model: sarvam-m (free tier)")
            print("   Ready for domain enrichment")
        else:
            print("\n❌ FAILED! Check your API key and configuration")
    
    print("=" * 70 + "\n")
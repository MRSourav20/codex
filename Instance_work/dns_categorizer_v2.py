#!/usr/bin/env python3
"""
Enhanced Domain Categorizer - Chunk 3
Lightweight rule-based classification with UNKNOWN marking.
Serves as first-stage fast categorization before AI enrichment.
"""

import logging
from typing import Optional, Dict, Set, Tuple
from enum import Enum
import re

logger = logging.getLogger("DomainCategorizer")


class DomainCategory(Enum):
    """Domain category enumeration."""
    AI_ASSISTANT = "AI Assistant"
    DEVELOPMENT = "Development"
    CODING_PLATFORM = "Coding Platform"
    SEARCH_ENGINE = "Search Engine"
    MEDIA = "Media"
    SOCIAL_MEDIA = "Social Media"
    CLOUD_SERVICES = "Cloud Services"
    COMMUNICATION = "Communication"
    UNKNOWN = "Unknown"


class DomainCategorizer:
    """
    Lightweight rule-based domain categorizer.
    First-stage fast classification using patterns and keywords.
    Unknown domains are marked for enrichment.
    """
    
    def __init__(self):
        """Initialize categorizer with rule patterns."""
        self.rules = self._initialize_rules()
        self.keyword_patterns = self._initialize_patterns()
        logger.info("DomainCategorizer initialized (rule-based, first-stage)")
    
    def _initialize_rules(self) -> Dict[DomainCategory, Set[str]]:
        """
        Initialize domain rules.
        Exact domain matches - fast lookup.
        
        Returns:
            Dictionary of category -> set of exact domains
        """
        return {
            DomainCategory.AI_ASSISTANT: {
                'chat.openai.com',
                'openai.com',
                'claude.ai',
                'anthropic.com',
                'gemini.google.com',
                'bard.google.com',
                'chatgpt.com',
                'perplexity.ai',
                'mistral.ai',
                'cohere.com',
                'replicate.com',
            },
            DomainCategory.DEVELOPMENT: {
                'github.com',
                'gitlab.com',
                'bitbucket.org',
                'npm.com',
                'npmjs.com',
                'npmjs.org',
                'pypi.org',
                'crates.io',
                'maven.org',
                'docker.com',
            },
            DomainCategory.CODING_PLATFORM: {
                'stackoverflow.com',
                'dev.to',
                'codepen.io',
                'jsfiddle.net',
                'repl.it',
                'glitch.com',
                'heroku.com',
            },
            DomainCategory.SEARCH_ENGINE: {
                'google.com',
                'bing.com',
                'yahoo.com',
                'duckduckgo.com',
                'baidu.com',
                'yandex.com',
            },
            DomainCategory.MEDIA: {
                'youtube.com',
                'youtu.be',
                'netflix.com',
                'twitch.tv',
                'vimeo.com',
                'dailymotion.com',
            },
            DomainCategory.SOCIAL_MEDIA: {
                'facebook.com',
                'instagram.com',
                'twitter.com',
                'x.com',
                'tiktok.com',
                'reddit.com',
                'linkedin.com',
            },
            DomainCategory.CLOUD_SERVICES: {
                'aws.amazon.com',
                'azure.microsoft.com',
                'cloud.google.com',
                'digitalocean.com',
                'heroku.com',
            },
            DomainCategory.COMMUNICATION: {
                'gmail.com',
                'outlook.com',
                'mail.google.com',
                'protonmail.com',
                'slack.com',
                'discord.com',
            },
        }
    
    def _initialize_patterns(self) -> Dict[DomainCategory, list]:
        """
        Initialize keyword patterns for categorization.
        Used when domain doesn't match exact rules.
        
        Returns:
            Dictionary of category -> list of regex patterns
        """
        return {
            DomainCategory.AI_ASSISTANT: [
                r'(chat|gpt|claude|ai|assistant|bot)',
                r'(openai|anthropic|gemini|bard)',
            ],
            DomainCategory.DEVELOPMENT: [
                r'(github|gitlab|git)',
                r'(npm|pypi|cargo)',
            ],
            DomainCategory.CODING_PLATFORM: [
                r'(stack|code|dev)',
                r'(repl|sandbox|ide)',
            ],
            DomainCategory.SEARCH_ENGINE: [
                r'(search|google|bing)',
            ],
            DomainCategory.SOCIAL_MEDIA: [
                r'(social|insta|tweet|reddit)',
            ],
        }
    
    def categorize(
        self,
        domain: str,
        confidence: bool = False
    ) -> Tuple[DomainCategory, float]:
        """
        Categorize domain using rule-based matching.
        Returns UNKNOWN for domains not matching rules.
        
        Args:
            domain: Domain name to categorize
            confidence: If True, return confidence score
            
        Returns:
            (DomainCategory, confidence_score) tuple
        """
        domain_lower = domain.lower().rstrip('.')
        
        # Stage 1: Exact match (high confidence)
        for category, keywords in self.rules.items():
            if domain_lower in keywords:
                return (category, 1.0)
        
        # Stage 2: Subdomain match (medium confidence)
        domain_parts = domain_lower.split('.')
        for category, keywords in self.rules.items():
            for keyword in keywords:
                keyword_parts = keyword.split('.')
                # Check if keyword is parent domain
                if len(domain_parts) >= len(keyword_parts):
                    if domain_lower.endswith('.' + keyword) or domain_lower.endswith(keyword):
                        return (category, 0.85)
        
        # Stage 3: Keyword pattern matching (low confidence)
        for category, patterns in self.keyword_patterns.items():
            for pattern in patterns:
                if re.search(pattern, domain_lower, re.IGNORECASE):
                    return (category, 0.6)
        
        # Unknown domain - return with 0 confidence
        return (DomainCategory.UNKNOWN, 0.0)
    
    def is_unknown(self, domain: str) -> bool:
        """
        Check if domain is unknown (not categorized by rules).
        
        Args:
            domain: Domain to check
            
        Returns:
            True if domain is unknown
        """
        category, _ = self.categorize(domain)
        return category == DomainCategory.UNKNOWN
    
    def is_ai_assistant(self, domain: str) -> bool:
        """
        Check if domain is AI assistant.
        
        Args:
            domain: Domain to check
            
        Returns:
            True if AI assistant
        """
        category, _ = self.categorize(domain)
        return category == DomainCategory.AI_ASSISTANT
    
    def categorize_batch(self, domains: list) -> Dict[str, Tuple[str, float]]:
        """
        Categorize multiple domains.
        Returns dict of domain -> (category, confidence).
        
        Args:
            domains: List of domain names
            
        Returns:
            Dictionary of domain -> (category_str, confidence)
        """
        results = {}
        for domain in domains:
            category, confidence = self.categorize(domain)
            results[domain] = (category.value, confidence)
        return results
    
    def get_category_stats(self, domains: list) -> Dict[str, int]:
        """
        Get category distribution for domains.
        
        Args:
            domains: List of domain names
            
        Returns:
            Dictionary of category -> count
        """
        stats = {category.value: 0 for category in DomainCategory}
        
        for domain in domains:
            category, _ = self.categorize(domain)
            stats[category.value] += 1
        
        return {k: v for k, v in stats.items() if v > 0}
    
    def get_ai_domains(self) -> Set[str]:
        """
        Get known AI assistant domains.
        
        Returns:
            Set of AI assistant domains
        """
        return self.rules[DomainCategory.AI_ASSISTANT]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    categorizer = DomainCategorizer()
    
    # Test domains
    test_domains = [
        'google.com',
        'api.github.com',
        'chat.openai.com',
        'supergptcoder.ai',  # Unknown - should be marked for enrichment
        'stackoverflow.com',
        'unknown-domain-xyz.io',
    ]
    
    print("\n" + "="*70)
    print("DOMAIN CATEGORIZATION TEST (RULE-BASED, FIRST-STAGE)")
    print("="*70)
    
    for domain in test_domains:
        category, confidence = categorizer.categorize(domain)
        is_unknown = categorizer.is_unknown(domain)
        print(f"{domain:30} → {category.value:20} (conf: {confidence:.2f}, unknown: {is_unknown})")
    
    print("\n" + "="*70)
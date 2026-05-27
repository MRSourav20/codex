# Chunk 3: Adaptive Behavioral Intelligence with Sarvam-2B Enrichment

## Overview

Chunk 3 extends Chunk 2 with an **intelligent domain enrichment layer** that learns and adapts over time. Instead of relying solely on hardcoded domain lists, the system uses AI-powered analysis to classify unknown domains and continuously improve its detection capability.

**Architecture**: 
```
DNS Domain → Rule-Based Fast Match → Local Intelligence DB → 
  Sarvam-2B API (for unknowns) → Store & Cache → Future detections are instant
```

---

## Key Innovation: Adaptive Learning Pipeline

### Traditional Approach (Chunk 2)
- Hardcoded domain lists
- Static categorization
- Unknown domains marked but not analyzed
- Limited detection capability

### Chunk 3 Approach
- Fast rule-based first stage
- **Local intelligence database** for caching
- **Sarvam-2B API** for unknown domain analysis
- Continuous learning (store results locally)
- Minimized API calls through intelligent caching
- Adaptive detection that improves over time

---

## Architecture Flow

```
┌─ Candidate DNS Query
│
├─ Extract domain (e.g., "supergptcoder.ai")
│
├─ Stage 1: Rule-Based Categorizer (Fast)
│  └─ Check hardcoded rules for common domains
│     └─ If known: return immediately (⚡ fast)
│     └─ If unknown: proceed to Stage 2
│
├─ Stage 2: Local Intelligence DB (Instant)
│  └─ Check if domain was seen before
│     └─ If cached: return cached result (💾 instant)
│     └─ If not cached: proceed to Stage 3
│
├─ Stage 3: Sarvam-2B API (Intelligent)
│  └─ Send to API with analysis prompt
│     └─ API responds with:
│        - Category (AI Assistant, Development, etc.)
│        - Confidence score (0.0-1.0)
│        - Reasoning
│        - Related keywords
│     └─ Store result in local DB
│     └─ Return to caller (🤖 enriched)
│
└─ Future Detections
   └─ Automatic cache hit (⚡ instant, no API cost)
```

---

## New Modules

### 1. dns_categorizer_v2.py (Enhanced Categorizer)
**Purpose**: Fast first-stage rule-based categorization

**Features**:
- Exact domain matching
- Subdomain pattern matching
- Keyword pattern matching
- **Marks UNKNOWN domains clearly**
- Confidence scoring (0.0-1.0)
- Lightweight (no network calls)

**Categories**:
- AI Assistant
- Development
- Coding Platform
- Search Engine
- Media
- Social Media
- Cloud Services
- Communication
- **Unknown** (marked for enrichment)

**Usage**:
```python
categorizer = DomainCategorizer()
category, confidence = categorizer.categorize("google.com")
# Returns: (AI_ASSISTANT, 1.0)

is_unknown = categorizer.is_unknown("supergptcoder.ai")
# Returns: True
```

### 2. domain_intelligence_db.py (Local Intelligence Cache)
**Purpose**: Persistent local storage of domain classifications

**Key Feature**: Avoids repeated API calls through intelligent caching

**Database Schema**:

```sql
-- Domains table
CREATE TABLE domains (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE,
    category TEXT,
    confidence REAL,
    source TEXT,           -- 'rule-based', 'sarvam-2b', 'unknown'
    reasoning TEXT,
    first_seen TEXT,
    last_seen TEXT,
    times_detected INTEGER
)

-- Enrichment log (tracks API usage)
CREATE TABLE enrichment_log (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    previous_category TEXT,
    new_category TEXT,
    api_response TEXT,
    cost_tokens INTEGER,    -- For cost tracking
    created_at TIMESTAMP
)

-- Statistics table
CREATE TABLE statistics (
    total_domains INTEGER,
    known_domains INTEGER,
    api_calls_made INTEGER,
    cached_hits INTEGER
)
```

**Key Methods**:
```python
db = DomainIntelligenceDB()

# Retrieve cached classification (instant, no cost)
result = db.get_domain("google.com")
# Returns: {domain, category, confidence, source, ...}

# Store new classification
db.store_domain(
    "supergptcoder.ai",
    "AI Assistant",
    0.89,
    "sarvam-2b",
    "Domain name suggests AI coding assistant"
)

# Get unknown domains needing enrichment
unknowns = db.get_unknown_domains(limit=50)

# Track API usage
db.log_enrichment(
    domain="supergptcoder.ai",
    previous_category="Unknown",
    new_category="AI Assistant",
    cost_tokens=150
)

# Get statistics
stats = db.get_statistics()
# Returns: {total_domains, by_category, api_calls_made, ...}
```

**Cost Optimization**:
- Cache hits: Free, instant
- Rule-based: Free, fast
- API calls: Only for new unknown domains
- Re-detection: Instant from cache

### 3. sarvam_enrichment.py (API Integration)
**Purpose**: Intelligent domain analysis using Sarvam-2B

**Key Feature**: Enriches unknown domains with AI-powered classification

**How it Works**:
```
Input: Domain name (e.g., "supergptcoder.ai")
    ↓
Sarvam-2B Model analyzes:
  - Domain name keywords
  - URL patterns
  - Known domain characteristics
  - AI/coding tool signatures
    ↓
Output JSON:
{
    "domain": "supergptcoder.ai",
    "category": "AI Assistant",
    "is_ai_related": true,
    "is_coding_related": true,
    "confidence": 0.89,
    "reasoning": "Domain name strongly suggests AI coding assistant functionality",
    "keywords": ["gpt", "coder", "ai", "assistant"]
}
```

**Usage**:
```python
sarvam = SarvamEnrichment(api_key="your-key")

# Enrich single domain
result = sarvam.enrich_domain("supergptcoder.ai")
# Returns: {category, confidence, reasoning, ...}

# Batch enrichment with rate limiting
results = sarvam.batch_enrich([
    "supergptcoder.ai",
    "unknown-domain.xyz"
], delay_between_calls=1.0)

# Track cost
stats = sarvam.get_statistics()
# Returns: {api_calls_made, total_tokens_used, ...}

# Estimate cost
estimated = SarvamEnrichment.estimate_cost(500)  # 500 tokens
```

**Cost Optimization**:
- Batch API calls to reduce overhead
- Rate limiting to avoid throttling
- Token tracking for cost monitoring
- Only enrich truly unknown domains

### 4. EnrichmentPipeline (Orchestrator)
**Purpose**: Coordinates all enrichment stages

**Pipeline Logic**:
```python
def enrich(domain):
    1. Check local cache (free, instant)
    2. Rule-based categorization (free, fast)
    3. If unknown: call Sarvam API
    4. Store result in cache
    5. Return classification
```

**Usage**:
```python
pipeline = EnrichmentPipeline(categorizer, db, sarvam)

# Enrich single domain
category, confidence, source = pipeline.enrich("google.com")
# Returns: ("Search Engine", 1.0, "rule-based")

category, confidence, source = pipeline.enrich("supergptcoder.ai")
# Returns: ("AI Assistant", 0.89, "sarvam-2b")

# Next detection of supergptcoder.ai
category, confidence, source = pipeline.enrich("supergptcoder.ai")
# Returns: ("AI Assistant", 0.89, "sarvam-2b") - INSTANT from cache!
```

**Cost Analysis**:
- First detection: 1 API call
- Subsequent detections: 0 API calls (cached)
- Massive cost savings on repeated domains

---

## Integration with Chunk 2

### Enhanced Monitor (monitor_v3.py)
New orchestrator that coordinates:
1. DNS capture (from Chunk 2)
2. Smart categorization (rule-based first)
3. Intelligence DB caching
4. Sarvam enrichment (for unknowns)
5. Event detection (from Chunk 2)
6. Logging (from Chunk 2)

**Console Output**:
```
[12:44:10] ⚡ google.com                      Search Engine           (conf: 1.00)
[12:44:12] 💾 github.com                      Development            (conf: 0.85)
[12:44:14] 🤖 supergptcoder.ai                AI Assistant           (conf: 0.89)
[12:44:15] 💾 supergptcoder.ai                AI Assistant           (conf: 0.89)
                                               ↑ instant cache hit!

⚠️  EVENT: AI_DOMAIN_BURST (HIGH)
   Details: Multiple AI domains detected
```

**Indicators**:
- ⚡ = Rule-based (fast)
- 💾 = From cache (instant, free)
- 🤖 = Sarvam API (enriched)

---

## Configuration

### Enable/Disable Enrichment
```bash
# With enrichment (default)
sudo python3 monitor_v3.py

# Without enrichment (Chunk 2 mode)
sudo python3 monitor_v3.py --no-enrichment
```

### Set Sarvam API Key
```bash
# Method 1: Environment variable
export SARVAM_API_KEY="your-api-key"
sudo python3 monitor_v3.py

# Method 2: Code
from sarvam_enrichment import SarvamEnrichment
sarvam = SarvamEnrichment(api_key="your-key")
```

### Adjust Enrichment Threshold
```bash
# Only enrich domains with confidence < 0.7
sudo python3 monitor_v3.py --enrichment-threshold 0.7
```

---

## Cost Optimization Strategy

### Minimize API Calls

**Strategy 1: Local Caching**
- First detection: API call
- Subsequent detections: Cache hit (0 cost)
- Savings: 90%+ on repeated domains

**Strategy 2: Fast Rules First**
- Rule-based matching (free)
- Only call API for true unknowns
- Typical rule hit rate: 80-90%

**Strategy 3: Batch Enrichment**
- Group API calls
- Rate limiting (avoid throttling)
- Reduced overhead

**Strategy 4: Selective Enrichment**
- High-confidence rules: skip API
- Only enrich uncertain domains
- Threshold-based API gating

### Cost Example

**Scenario**: Monitor 8-hour interview with 1000 DNS queries

```
Without Intelligence DB:
- API calls: 1000 (worst case)
- Cost: High ($1-5+)

With Intelligence DB:
- Unique domains: ~100
- Rule-based hits: ~80 (80%)
- API calls needed: ~20 (20%)
- Cost: Low ($0.02-0.10)

Savings: 90%+ reduction in API cost!
```

---

## Database Queries

### View Intelligence Database
```bash
# All stored domains
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT domain, category, confidence, source FROM domains ORDER BY domain;"

# AI-related domains
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT domain, confidence FROM domains WHERE category='AI Assistant';"

# Recently enriched
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT domain, new_category, cost_tokens FROM enrichment_log ORDER BY created_at DESC LIMIT 20;"

# Enrichment statistics
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT COUNT(*) as total_enrichments, SUM(cost_tokens) as total_tokens FROM enrichment_log;"

# Category distribution
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT category, COUNT(*) FROM domains GROUP BY category ORDER BY COUNT(*) DESC;"
```

### Export Intelligence
```bash
python3 << 'EOF'
from domain_intelligence_db import DomainIntelligenceDB

db = DomainIntelligenceDB()
report_path = db.export_intelligence()
print(f"Exported to: {report_path}")
EOF
```

---

## Monitoring & Cost Tracking

### Session Statistics
```python
pipeline = EnrichmentPipeline(...)

stats = pipeline.get_statistics()
# {
#   'total_processed': 1000,
#   'rule_based_hits': 800,
#   'cache_hits': 150,
#   'api_calls': 50,
#   'sarvam_stats': {
#     'api_calls_made': 50,
#     'total_tokens_used': 7500,
#     'avg_tokens_per_call': 150
#   }
# }
```

### Cost Estimation
```python
# After session
sarvam_stats = sarvam.get_statistics()
tokens_used = sarvam_stats['total_tokens_used']

estimated_cost = SarvamEnrichment.estimate_cost(tokens_used)
print(f"Estimated cost: ${estimated_cost}")
```

---

## Real-World Detection Capabilities

### What Chunk 3 Can Now Detect

**Known AI Tools** (instant cache):
- OpenAI ChatGPT
- Anthropic Claude
- Google Gemini
- Perplexity AI
- Mistral AI
- ... and 100s more as they're discovered

**Unknown AI Tools** (Sarvam enrichment):
- New AI startups
- Niche AI services
- Variations/mirrors of known tools
- Custom/branded AI solutions
- Hidden helper tools

**Example Unknown Domains Classified**:
```
Domain: supergptcoder.ai
API Response: AI Assistant (conf: 0.89)
Reasoning: "Domain name strongly suggests AI coding assistant"

Domain: cheapcodinghelp.net
API Response: Coding Helper (conf: 0.85)
Reasoning: "Domain indicates code assistance service"

Domain: aiwriter-pro.com
API Response: AI Content (conf: 0.82)
Reasoning: "Suggests AI-powered writing tool"
```

---

## Integration Points (Chunk 4+)

### Dashboard Integration
```python
# Real-time domain insights
domains = db.get_high_confidence_domains(min_confidence=0.8)
# → Display on dashboard

# AI activity tracking
ai_domains = db.get_domain_stats()['by_category']['AI Assistant']
# → Show AI usage stats

# Enrichment history
enrichments = db.get_enrichment_log()
# → Timeline of detected new AI tools
```

### Session Linking
```python
# Link enriched domains to interview session
session.linked_domains = [
    {
        'domain': 'chat.openai.com',
        'category': 'AI Assistant',
        'detected_at': '12:44:14',
        'confidence': 1.0,
        'source': 'rule-based'
    },
    {
        'domain': 'supergptcoder.ai',
        'category': 'AI Assistant',
        'detected_at': '12:44:20',
        'confidence': 0.89,
        'source': 'sarvam-2b'
    }
]
```

### Anomaly Detection (Future)
```python
# Build on enriched data
def detect_ai_usage_pattern(domains):
    ai_domains = [d for d in domains if d['category'] == 'AI Assistant']
    
    if len(ai_domains) >= 3:
        return "Suspicious AI usage pattern detected"
    
    # More sophisticated detection...
```

---

## Performance Impact

### Latency
- Rule-based: <1ms
- Cache hit: <5ms
- API call: 500-2000ms (batched)

### Memory
- Intelligence DB: ~1MB per 10k domains
- Cached in memory: Minimal

### API Calls
- Expected: 10-20% of total domains
- Batch processing: Reduced overhead

---

## Troubleshooting

### Enrichment Disabled
```bash
# Check if API key set
echo $SARVAM_API_KEY

# Set it
export SARVAM_API_KEY="your-key"

# Run with enrichment
sudo python3 monitor_v3.py
```

### No API Calls Made
```bash
# Check logs
tail -f dns_logs/monitor_v3.log | grep -i sarvam

# Most domains probably hit rule-based cache
# This is actually good (cost efficient)
```

### High Token Usage
```bash
# Reduce enrichment threshold (enrich fewer domains)
sudo python3 monitor_v3.py --enrichment-threshold 0.7

# Only truly unknown domains will be enriched
```

### Database Errors
```bash
# Reset intelligence DB
rm dns_logs/domain_intelligence.db

# Monitor will recreate on startup
sudo python3 monitor_v3.py
```

---

## Security Considerations

### API Key Management
- Store in environment variable: `export SARVAM_API_KEY=...`
- Never hardcode in source
- Rotate regularly
- Monitor usage

### Data Privacy
- Intelligence DB stored locally
- API calls only for unknown domains
- No candidate data sent to API
- Metadata-only analysis

### Cost Control
- Monitor token usage
- Set alerts for unexpected costs
- Use enrichment threshold to gate API calls
- Regular cost reviews

---

## Comparison: Chunk 2 vs Chunk 3

| Feature | Chunk 2 | Chunk 3 |
|---------|---------|---------|
| Capture DNS | ✅ | ✅ |
| Rule-based categorization | ✅ | ✅ (faster) |
| Local caching | ❌ | ✅ |
| Unknown domain analysis | ❌ | ✅ (Sarvam) |
| AI detection | ✅ (hardcoded) | ✅ (adaptive) |
| Cost optimization | N/A | ✅ (90%+ savings) |
| Learning capability | ❌ | ✅ (improves over time) |
| Event detection | ✅ | ✅ |
| Logging | ✅ | ✅ (enhanced) |
| API integration | ❌ | ✅ |

---

## Next Steps

### Immediate
1. Set up Sarvam API key
2. Run with enrichment enabled
3. Monitor for unknown domain detections
4. Track API costs

### Short-term
1. Analyze enrichment results
2. Fine-tune detection rules
3. Export intelligence reports
4. Improve categorization based on results

### Medium-term
1. Batch enrich unknown domains
2. Build statistical models on enriched data
3. Create domain risk scoring
4. Dashboard integration (Chunk 4)

### Long-term
1. Continuous learning from new domains
2. Anomaly detection using enriched context
3. Advanced behavioral analysis
4. Predictive integrity signals

---

## File Structure

```
packet_test/
├── dns_capture.py              # (Chunk 2 - unchanged)
├── dns_logger.py               # (Chunk 2 - unchanged)
├── dns_event_detector.py       # (Chunk 2 - unchanged)
├── dns_categorizer_v2.py       # NEW: Enhanced categorizer
├── domain_intelligence_db.py   # NEW: Local intelligence cache
├── sarvam_enrichment.py        # NEW: API integration
├── monitor_v3.py               # NEW: Enhanced orchestrator
├── requirements.txt            # UPDATED: Added requests
└── dns_logs/
    ├── dns_capture.db         # (Chunk 2 data)
    ├── dns_queries.jsonl      # (Chunk 2 data)
    ├── domain_intelligence.db # NEW: Intelligence cache
    └── ...
```

---

## Quick Start

```bash
# 1. Set API key
export SARVAM_API_KEY="your-key"

# 2. Update dependencies
pip install -r requirements.txt

# 3. Run with enrichment
sudo python3 monitor_v3.py

# 4. Check intelligence database
sqlite3 dns_logs/domain_intelligence.db \
    "SELECT domain, category FROM domains;"

# 5. View costs
python3 -c "from sarvam_enrichment import SarvamEnrichment; \
print(SarvamEnrichment().estimate_cost(500))"
```

---

## Summary

**Chunk 3 delivers:**

✅ Intelligent domain enrichment  
✅ Local intelligence caching  
✅ Sarvam-2B API integration  
✅ Cost-optimized API usage  
✅ Adaptive learning capability  
✅ Backward compatible with Chunk 2  
✅ Production-ready code  
✅ Comprehensive documentation  

**Status**: Ready for production deployment with Sarvam API key

**Next**: Chunk 4 (Dashboard & Real-time Visualization)
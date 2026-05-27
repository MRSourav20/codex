# 🧠 COADEX 2.0 — MASTER BRAIN DOCUMENT
> **One file to rule them all.** This is the single source of truth for the Interview Integrity Platform.  
> Synthesized from: `deep-research-report.md` · `interview-integrity-master-plan.md` · `token_optimization_report.md` · `implementation_plan.md.resolved`

---

## 🎯 PROJECT MISSION

**Detect AI-assisted cheating in live remote interviews.**  
Monitor 5 signal layers (Network · Browser · System · Webcam · Typing), extract metadata-level intelligence through an AWS EC2 gateway, and produce an integrity report for the interviewer — all without full packet inspection or heavy ML infrastructure.

---

## 🏗️ FINAL PRODUCT STRUCTURE

### Candidate Side — Electron Desktop Client
- **Why Electron?** Browser-only solutions cannot monitor background processes or desktop-level events. Electron = Chromium + Node.js = full OS access + controlled browser session.
- **What it does:**
  - Session management (connects to AWS gateway)
  - Browser monitoring (tab switches, clipboard, focus)
  - Process monitoring (psutil via Python child process)
  - Webcam access (OpenCV gaze tracking)
  - Metadata collection and transmission

### Backend — AWS EC2 Gateway
- **Role:** Temporary interview gateway + metadata collector
- **Stack:**
  - `FastAPI` — REST API for session lifecycle + event ingestion
  - `mitmproxy` — optional HTTP/S inspection (with candidate consent)
  - `pyshark` / `tshark` — DNS + SNI packet capture
  - `SQLite` — lightweight encrypted event storage

### Interviewer Side — Web Dashboard
- Live monitoring during interview
- Shows: integrity score · alerts · suspicious timeline · webcam analysis · network intelligence · final report

---

## 🔄 FINAL SYSTEM FLOW

```
Candidate Electron Client
        ↓
  AWS EC2 Gateway  (FastAPI + PyShark + mitmproxy)
        ↓
  Metadata Extraction  (DNS · SNI · WebSocket · Browser · Process · Gaze)
        ↓
  Anomaly Engine  (Rule-based scoring → lookup table)
        ↓
  Dashboard + Integrity Report  (Interviewer web UI)
```

---

## 🏛️ SYSTEM ARCHITECTURE

```
Candidate Machine (Electron)              AWS EC2 Gateway          Reviewer
┌────────────────────────────┐          ┌──────────────────┐     ┌──────────────┐
│ Electron Interview Client  │          │ FastAPI Backend  │     │ Web Dashboard│
│  ├─ Browser (Chromium)     │──HTTPS──▶│ PyShark Capture  │────▶│  Live Score  │
│  ├─ OpenCV Webcam          │          │ mitmproxy (opt.) │     │  Alerts      │
│  ├─ psutil Process Monitor │          │ Anomaly Engine   │     │  Timeline    │
│  ├─ Typing Monitor         │          │ SQLite Storage   │     │  Report      │
│  └─ Session Manager        │          └──────────────────┘     └──────────────┘
└────────────────────────────┘
```

**5 Signal Layers:**  
`Network` · `Browser` · `System/Process` · `Webcam` · `Typing`

---

## ⚡ MVP SCOPE (What We Build First)

### ✅ MVP Includes
| Feature | Implementation |
|---|---|
| Metadata-level monitoring | DNS, SNI, domain, IP logging (no deep packet inspection) |
| DNS/domain observation | PyShark on EC2 gateway |
| WebSocket activity tracking | Connection state changes only (open/close/burst) |
| Browser behavior | Tab switches, clipboard paste, focus events (Electron) |
| Process detection | psutil blacklist scan + hash-diff every 30s |
| OpenCV gaze tracking | MediaPipe Lite FaceMesh at 1fps adaptive |
| Rule-based anomaly scoring | Lookup table (no ML training needed) |
| Interviewer dashboard | Live score + alerts + post-session report |

### ❌ MVP Explicitly Avoids
- Full enterprise VPN infrastructure (WireGuard for MVP, can add later)
- Deep packet inspection (only metadata/headers visible)
- Heavy ML training (rule-based scoring first, ML in Phase 2)

---

## 🛠️ COMPLETE TECH STACK

| Layer | Tool | Notes |
|---|---|---|
| **Candidate Client** | **Electron + Node.js** | Kiosk mode, OS-level access, embeds Python agent |
| **Interview Browser** | Chromium (via Electron) | Controlled session, no external windows |
| **Session Tunnel** | WireGuard (MVP) / AWS VPN | Ephemeral keys, auto-expire at session end |
| **Gateway Backend** | **FastAPI (Python 3.11+)** | REST API on AWS EC2 |
| **Packet Capture** | **PyShark** (wraps TShark) | DNS/SNI capture on EC2 interface |
| **HTTP Inspection** | **mitmproxy** | Optional; only with candidate consent |
| **Process Monitor** | **psutil** (Python) | Cross-platform, BSD license |
| **Webcam Pipeline** | **OpenCV + MediaPipe Lite** | FaceMesh landmarks, head pose, gaze zones |
| **Anomaly Engine** | **Rule lookup table** → scikit-learn Phase 2 | Deterministic first |
| **Storage** | **SQLite + LZ4** | Lightweight, encrypted, per-session |
| **Dashboard** | **HTML + Vanilla JS** | Interviewer web UI, JWT auth |
| **Cloud** | **AWS EC2** (t3.micro, Ubuntu 22.04) | Free tier for MVP |

---

## 🔐 THREAT MODEL

| Threat | Signal Caught By | Detection Method |
|---|---|---|
| AI overlay (Cluely-style) | System layer | psutil blacklist + hotkey burst detection |
| Remote taker / proxy | Network layer | IP change, concurrent session metadata |
| ChatGPT/Copilot tab | Browser layer | Tab nav + SNI match to AI domains |
| Screen sharing | System layer | VM/RDP process, extra display detection |
| Clipboard paste | Typing layer | >200 char burst in <1s (impossible to type) |
| Gaze/attention loss | Webcam layer | Head turn >45°, face off-frame via MediaPipe |

---

## 📦 BUILD PLAN — 6 CHUNKS

> Each chunk = one independent build sprint. Chunks 2–5 can run in parallel after Chunk 1.

```
CHUNK 1: Infrastructure + AWS EC2 Setup
   │
   ├──► CHUNK 2: Network Monitor (PyShark on EC2)
   ├──► CHUNK 3: Electron Client (Browser + Clipboard Monitor)
   ├──► CHUNK 4: Process Agent (psutil + VM detection)
   ├──► CHUNK 5: Webcam Pipeline (OpenCV + MediaPipe Lite)
   │
   └──► CHUNK 6: Anomaly Engine + Interviewer Dashboard
```

---

### CHUNK 1 — AWS EC2 Infrastructure & Session Gateway
**Duration:** 1–2 days | **Output:** Live FastAPI on EC2 with session endpoints

#### AWS EC2 Setup
```
Instance: Ubuntu 22.04, t3.micro (Free Tier)
Open Ports:
  - 51820/UDP  → WireGuard VPN tunnel
  - 8000/TCP   → FastAPI backend
  - 22/TCP     → SSH access
Install: python3.11, pip, wireguard, tshark, sqlite3, mitmproxy
```

#### Files to Build
| File | Purpose |
|---|---|
| `session_tunnel.py` | Generate ephemeral WireGuard keys per session, spin up/tear down tunnel |
| `session_manager.py` | create_session() → session_id + WireGuard config; end_session() → flush + cleanup |
| `main.py` (FastAPI) | All API endpoints |

#### FastAPI Endpoints
```
POST /session/start           → returns session_id + WireGuard config
POST /session/end/{id}        → teardown tunnel, flush logs
GET  /report/{session_id}     → fetch integrity report
POST /events/{session_id}     → receive monitoring events from Electron client
```

**✅ Chunk 1 Done When:** `POST /session/start` returns WireGuard config, `POST /session/end` cleans up.

---

### CHUNK 2 — Network Monitoring Layer (on EC2)
**Duration:** 1–2 days | **Output:** DNS/SNI logging + EMA anomaly detection

#### Files to Build
| File | Purpose |
|---|---|
| `network_monitor.py` | PyShark DNS + TLS SNI capture, 5s sampling |
| `traffic_analyzer.py` | EMA-based traffic anomaly detection |
| `domain_classifier.py` | LRU cache (500 entries), AI domain blocklist |
| `event_logger.py` | Binary compact event format, circular buffers |

#### Key Implementation Details

**DNS/SNI Sampling (not streaming)**
```python
# Sample every 5s — 80-85% reduction in network processing
# Only deep-inspect if anomaly detected
capture_dns_queries(interface)   # → domain + timestamp every 5s
capture_tls_sni(interface)       # → SNI hostname from TLS ClientHello
```

**EMA Anomaly Detector**
```python
# Track 3 metrics: packet_count, bytes_per_sec, request_frequency
metric = 0.2 * new_value + 0.8 * prev_metric   # EMA update
if abs(metric - baseline) > 2 * sigma: trigger_alert()
```

**Domain Classifier**
```python
AI_HELPER_DOMAINS = {
  "chatgpt.com", "copilot.microsoft.com", "claude.ai",
  "gemini.google.com", "perplexity.ai", "phind.com"
}
domain_cache = LRUCache(maxsize=500)   # 90% fewer threat-DB lookups
classify_domain(domain) → "safe" | "suspicious" | "ai_helper"
```

**Compact Event Format (8 bytes/event)**
```python
# [event_code(1B), ts_delta_ms(3B), value1(2B), value2(2B)]
EVENT_CODES = {
  0x01: "dns_query",  0x02: "paste",      0x03: "tab_switch",
  0x04: "gaze_drift", 0x05: "process_new",0x06: "ws_connect",
  0x07: "idle",       0x08: "typing_spike",0x09: "tls_connect"
}
CircularBuffer(maxsize=1000)   # per module, no unbounded growth
```

**WebSocket — Event-Driven (not streaming)**
```python
ws_log = ["open", "close", "burst"]   # NOT every frame
# Per-session: 400KB → 40KB (90% reduction)
```

**Storage Target:** `50MB → 12MB` per session

**✅ Chunk 2 Done When:** DNS + SNI logged every 5s, EMA anomalies firing, domain cache working.

---

### CHUNK 3 — Electron Client (Browser + Clipboard Layer)
**Duration:** 2–3 days | **Output:** Desktop interview client with browser monitoring

#### Architecture
```
Electron Main Process (Node.js)
  ├─ Session Manager (connects to EC2 API)
  ├─ Process Monitor (calls Python psutil agent)
  ├─ Webcam Bridge (calls Python OpenCV agent)
  └─ BrowserWindow (Chromium, kiosk mode)
       ├─ content.js (clipboard, paste, input monitoring)
       └─ background.js (tab switches, navigation, focus)
```

#### Files to Build
| File | Purpose |
|---|---|
| `electron/main.js` | Main process, kiosk window, child process bridge |
| `electron/preload.js` | Context bridge to renderer |
| `electron/renderer/content.js` | Clipboard paste detection, input monitoring |
| `electron/renderer/background.js` | Tab aggregation, navigation delta encoding |
| `electron/session.js` | Connect to EC2 API, send events |

#### Key Implementation Details

**Tab Switch Aggregation (aggregate, not log)**
```python
tab_metrics = {
  "switches_per_min": 2.5,
  "avg_focus_sec": 180,
  "suspicious_domains": ["chatgpt.com", "copilot.microsoft.com"]
}
# Alert ONLY: >5 focus changes per 10s window
# Storage: 30MB → 2MB per session (95% reduction)
```

**Clipboard Paste Detection**
```javascript
// Flag when:
// 1. charCount > 200 AND duration < 1s (physically impossible to type)
// 2. 3+ pastes in < 30s
// 3. Repeated identical content
document.addEventListener('paste', (e) => { /* detect + POST to EC2 */ });
```

**Navigation Delta Encoding**
```javascript
// Store index references, NOT full URLs (70% storage reduction)
domains_visited = ["domain1", "domain2", "domain3"]
transitions = [{from: 0, to: 1, dur_sec: 45}, ...]
```

**✅ Chunk 3 Done When:** Electron client connects to EC2, tab aggregation working, paste events POST to backend.

---

### CHUNK 4 — Process & System Monitor (psutil Agent)
**Duration:** 1–2 days | **Output:** Background process scanner + VM detection

#### Files to Build
| File | Purpose |
|---|---|
| `agent/process_monitor.py` | Hash-diff process scan every 30s |
| `agent/vm_detector.py` | One-time VM fingerprint at session start |

#### Key Implementation Details

**Hash-Diff Process Scanner (not full rescan)**
```python
BLACKLIST = {
  "zoom", "anydesk", "teamviewer", "rustdesk", "vmware",
  "virtualbox", "obs", "chatgpt", "copilot-app"
}

# Startup: snapshot
baseline_hash = hash(frozenset(get_process_names()))

# Every 30s: compare hash only (0.0001 cost if unchanged)
current_hash = hash(frozenset(get_process_names()))
if current_hash != baseline_hash:
    delta = current_set - baseline_set   # log ONLY new processes

# Storage: 15MB → 0.5MB per session (99% reduction)
```

**VM Fingerprint (one-time, cached)**
```python
# Run ONCE at session start — cache result — NEVER re-run
vm_flags = check_cpu_flags()      # hypervisor CPU flag
         | check_audio_devices()   # "VB-Audio", "VirtualBox" etc.
         | check_disk_model()      # "VBOX", "VMWARE", "QEMU" strings
# Flag in session metadata if VM detected
# Savings: 99% for non-VM sessions
```

**✅ Chunk 4 Done When:** Process scanner running, VM check fires once, blacklisted processes trigger EC2 events.

---

### CHUNK 5 — Webcam Pipeline (OpenCV + MediaPipe Lite)
**Duration:** 2–3 days | **Output:** Gaze tracking + attention scoring

#### Files to Build
| File | Purpose |
|---|---|
| `agent/webcam_monitor.py` | Adaptive frame capture (1fps default) |
| `agent/gaze_classifier.py` | PnP head pose → gaze zone classification |
| `agent/attention_aggregator.py` | 5-min window attention scoring |

#### Key Implementation Details

**Adaptive Frame Sampling**
```python
fps = 1   # default (97% fewer frames vs 30fps)
if anomaly_detected: fps = 5  # burst for 30s
# Returns to 1fps after burst window
```

**MediaPipe Lite FaceMesh**
```python
# Lite model (not full) — 70% fewer compute tokens
# Extract: nose tip, eye corners, mouth corners for PnP pose
# 468 landmarks at 1fps
```

**Head Pose → Gaze Zone Classifier**
```python
ZONES = ["center", "edge", "off_screen", "down"]

# Baseline: average of first 20 frames → FROZEN
baseline = avg_pose(first_20_frames)

# Alert only on deviation > 1.5σ from baseline
if deviation > 1.5 * sigma:
    log_event("gaze_drift", zone, duration_sec)

# Store ZONE only — NOT pixel coordinates
```

**5-Minute Attention Window**
```python
attention_window = {
  "attention_score": 0-100,    # aggregate
  "drift_count": int,
  "off_screen_sec": int,
  "side_glances": int
}
# Store aggregate, NOT individual frame events (90% data reduction)
```

**Storage Target:** `100MB → 15MB` per session

**✅ Chunk 5 Done When:** Webcam at 1fps, face zones classified, gaze drift events firing on >1.5σ deviation.

---

### CHUNK 6 — Anomaly Engine + Interviewer Dashboard
**Duration:** 2–3 days | **Output:** Scoring engine + live dashboard + report

#### Files to Build
| File | Purpose |
|---|---|
| `engine/anomaly_engine.py` | Lookup table scoring + correlation rules |
| `engine/baseline_manager.py` | 5-minute baseline capture + freeze |
| `engine/report_generator.py` | Human-readable timeline report |
| `dashboard/index.html` | Interviewer web dashboard |
| `dashboard/app.js` | Live score, alerts, timeline, report export |

#### Key Implementation Details

**Lookup Table Scoring (no dynamic computation)**
```python
RISK_TABLE = {
  "paste_small": 2,    "paste_large": 8,    "paste_code": 12,
  "tab_switch_low": 0, "tab_switch_high": 5,
  "gaze_normal": 0,    "gaze_repeated": 6,  "gaze_sustained": 10,
  "domain_safe": 0,    "domain_suspicious": 8, "domain_ai_helper": 15,
  "blacklist_process": 20, "vm_detected": 10,
  "typing_spike": 8,   "idle_anomaly": 3,
}
# Thresholds: score > 15 → flag for review; score > 30 → high priority
```

**30-Second Buffered Processing (not real-time)**
```python
buffer = {
  "window": [T, T+30],
  "network":  [anomalies_only],
  "browser":  [anomalies_only],
  "webcam":   {summary_stats},
  "typing":   {summary_stats},
  "system":   [delta_processes]
}
score = sum(RISK_TABLE[event] for event in buffer)
# 70% reduction in processing overhead
```

**Correlation Bonus Rules (only when base score > 5)**
```python
if paste_event AND tab_to_ai_domain:    score += 5
if gaze_off AND clipboard_paste:        score += 4
if blacklist_process AND typing_spike:  score += 6
# 85% of correlation analysis skipped (only runs at threshold)
```

**Baseline Freeze (5-minute capture, never updated)**
```python
baseline = capture_first_5min()  # WPM, tab_rate, focus, network
# FROZEN after 5 minutes — NEVER updated mid-session
```

**Interviewer Dashboard — What It Shows**
| Panel | Content |
|---|---|
| Integrity Score | Live cumulative score (0–100) + risk badge |
| Alerts | Real-time event notifications with severity |
| Suspicious Timeline | Chronological list of flagged events |
| Webcam Analysis | Attention score, gaze drift count, off-screen time |
| Network Intelligence | Domains visited, AI helper hits, WebSocket activity |
| Final Report | One-click export (PDF / JSON) post-session |

**Report Format**
```
| Time     | Module  | Event      | Detail              | Score |
|----------|---------|------------|---------------------|-------|
| 10:05:12 | Browser | tab_switch | → chatgpt.com       | 15    |
| 10:05:40 | Input   | paste      | 350 chars           | 8     |
| 10:06:05 | Webcam  | gaze_drift | 5s off-screen       | 10    |
```

**✅ Chunk 6 Done When:** Full end-to-end works — session start → monitor → session end → report in <5 min.

---

## 📋 SESSION LIFECYCLE

```
SESSION START
  ├─► EC2: Generate ephemeral session keys → provision tunnel
  ├─► Client: Connect to EC2 gateway
  ├─► Capture 5-min baseline (WPM, tab rate, network, gaze) → FREEZE
  └─► One-time VM/process fingerprint → cache

RUNNING (per 30s buffer)
  ├─► EC2: Sample DNS/SNI every 5s
  ├─► Client: Read tab metrics (aggregated)
  ├─► Client: Hash-diff process list
  ├─► Client: Sample webcam frame (1fps adaptive)
  ├─► Client: Read typing window stats
  └─► EC2: Score buffer → ALERT if > threshold

SESSION END
  ├─► Flush circular buffers to SQLite
  ├─► Generate timestamped integrity report
  ├─► Revoke session keys / tear down tunnel
  ├─► Encrypt + store (retain only if flagged)
  └─► Purge raw data (GDPR minimal retention)
```

---

## 📊 DATA SCHEMA — EVENT LOG

```
| Timestamp           | Source   | Event         | Detail                    |
|---------------------|----------|---------------|---------------------------|
| 2026-05-25T10:00:05 | Network  | dns_query     | domain=cheatsite.com      |
| 2026-05-25T10:00:05 | Network  | tls_connect   | SNI=api.openai.com        |
| 2026-05-25T10:00:12 | Browser  | tab_switch    | → github.com              |
| 2026-05-25T10:00:15 | Input    | paste         | contentHash=abcd1234      |
| 2026-05-25T10:00:20 | Webcam   | gaze_drift    | zone=off_screen, 4s       |
```

**Binary compact format (8 bytes/event):**  
`[event_code(1B) | ts_delta_ms(3B) | value1(2B) | value2(2B)]`

**Circular buffers (fixed size, no unbounded growth):**
- Network alerts: last 1000 events
- Browser events: last 500 events
- Typing metrics: last 100 windows

---

## 🔒 PRIVACY & LEGAL CONSTRAINTS (NON-NEGOTIABLE)

| Constraint | Implementation |
|---|---|
| Consent prompt | Shown before EVERY session — explain all signals |
| No raw video storage | Only pose/zone metadata stored |
| No keystroke content | Only timing statistics (WPM, std dev) |
| Hashed IDs | No plaintext user IDs in any log |
| Encryption at rest | AES-256 for SQLite file |
| Auto-purge | Clean sessions deleted after report generation |
| GDPR scope | Logs expire after review window (30 days) |
| PII minimization | Store only domain names, hashed content, not raw text |

---

## 📈 EXPECTED OUTCOMES

| Metric | Baseline | After MVP | After Full Optimization |
|---|---|---|---|
| Storage/session | ~215 MB | ~91 MB | ~55 MB |
| Tokens/session | ~50,000 | ~20,000 | ~12,500 |
| Processing overhead | 100% | 40% | 25% |
| Detection accuracy | — | >95% | >95% |
| False positive rate | — | <5% | <5% |

**Annual savings (1,000 interviews/month):** ~$4,500–8,000 in token + storage costs

---

## ✅ FINAL VALIDATION CHECKLIST

- [ ] Anomaly detection accuracy ≥ 95% (test with 50+ labeled sessions)
- [ ] False positive rate < 5%
- [ ] Token consumption reduced > 60%
- [ ] Storage reduced > 70%
- [ ] No PII in raw logs
- [ ] Report generated < 5 minutes post-session
- [ ] Tunnel teardown completes < 5s after session end
- [ ] Baseline frozen correctly at minute 5
- [ ] Circular buffers prevent memory growth in 3h+ sessions
- [ ] Consent prompt shown before every session
- [ ] Electron client kiosk mode prevents external window access

---

## 🗓️ 6-WEEK DEVELOPMENT TIMELINE

```
Week 1: Chunk 1 — AWS EC2 + FastAPI + Session Tunnel
Week 2: Chunks 2 & 4 — Network Monitor (EC2) + Process Agent (parallel)
Week 3: Chunk 3 — Electron Client + Browser Monitor
Week 4: Chunk 5 — Webcam Pipeline (OpenCV + MediaPipe Lite)
Week 5: Chunk 6 — Anomaly Engine + Scoring
Week 6: Chunk 6 — Dashboard + Integration Testing + Report Generator
```

---

## 🔑 WHAT YOU NEED TO PROVIDE (Per Chunk)

| Chunk | Required Input |
|---|---|
| **Chunk 1** | AWS EC2 SSH access details OR confirm "use local machine" |
| **Chunk 2** | VirusTotal API key (free tier, optional) OR say "skip threat API" |
| **Chunk 3** | Nothing — full Electron client code generated |
| **Chunk 4** | Nothing — psutil agent code generated |
| **Chunk 5** | Nothing — webcam pipeline code generated |
| **Chunk 6** | Nothing — dashboard + engine code generated |

---

## 📁 FINAL PROJECT FILE STRUCTURE

```
coadex-2.0/
├── ec2_backend/
│   ├── main.py                  # FastAPI app
│   ├── session_manager.py       # Session lifecycle
│   ├── session_tunnel.py        # WireGuard key management
│   ├── network_monitor.py       # PyShark DNS/SNI capture
│   ├── traffic_analyzer.py      # EMA anomaly detection
│   ├── domain_classifier.py     # LRU cache + AI domain list
│   ├── event_logger.py          # Binary compact logger + circular buffer
│   └── engine/
│       ├── anomaly_engine.py    # Lookup table scoring
│       ├── baseline_manager.py  # 5-min baseline freeze
│       └── report_generator.py  # Human-readable timeline
│
├── electron_client/
│   ├── main.js                  # Electron main process
│   ├── preload.js               # Context bridge
│   ├── session.js               # EC2 connection + event sender
│   └── renderer/
│       ├── content.js           # Clipboard + input monitoring
│       └── background.js        # Tab aggregation + nav delta
│
├── python_agent/
│   ├── process_monitor.py       # psutil hash-diff scanner
│   ├── vm_detector.py           # One-time VM fingerprint
│   ├── webcam_monitor.py        # Adaptive frame capture
│   ├── gaze_classifier.py       # PnP → gaze zones
│   └── attention_aggregator.py  # 5-min attention window
│
└── dashboard/
    ├── index.html               # Interviewer web UI
    ├── app.js                   # Live score + timeline + report
    └── auth.js                  # JWT login for reviewer
```

---

*Ready to build? Say **"Start Chunk 1"** — I'll generate all the AWS EC2 setup steps and FastAPI code.*  
*Built with: FastAPI · PyShark · mitmproxy · OpenCV · MediaPipe Lite · Electron · psutil · SQLite · AWS EC2*  
*All core components free/OSS. Minimal cloud dependency. GDPR-compliant by design.*

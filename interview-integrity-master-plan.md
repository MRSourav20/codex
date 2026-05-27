# Interview Integrity Platform — Master Build Plan
> **Goal:** Detect AI-assisted cheating in live remote interviews via 5 signal layers, optimized for 70–75% lower compute/storage overhead.

---

## 1. SYSTEM ARCHITECTURE (One-Line View)

```
Candidate Machine                    Gateway Server              Reviewer
┌─────────────────────┐             ┌──────────────┐           ┌──────────┐
│ Browser Extension   │──WireGuard──▶ Packet Logger │──Events──▶ Dashboard│
│ Electron Agent      │   Tunnel    │ DNS/SNI Cache │           │ Report   │
│ Webcam (OpenCV)     │             │ Anomaly Engine│           └──────────┘
│ Typing Monitor      │             └──────────────┘
└─────────────────────┘
```

**5 Signal Layers:** Network · Browser · System · Webcam · Typing  
**Core Output:** Timestamped event log → human reviewer (NOT a black-box score)

---

## 2. TECH STACK (Free/OSS Only)

| Layer | Tool | Why |
|---|---|---|
| VPN Tunnel | **WireGuard** | Kernel-level, simple keys, fast setup |
| Packet Capture | **PyShark** (wraps TShark) | Python-native DNS/SNI parsing |
| HTTPS Inspection | **mitmproxy** | Optional; only with user consent |
| Browser Monitor | **Chrome Extension** (MV3) | `tabs`, clipboard, focus events |
| Desktop Agent | **Electron + Node** | Process list, OS clipboard, kiosk mode |
| Process Scan | **psutil** (Python) | Cross-platform, BSD license |
| Webcam | **MediaPipe FaceMesh (Lite)** | Landmarks + head pose, CPU-only |
| Storage | **SQLite + LZ4** | Lightweight encrypted local DB |
| Anomaly Engine | **Rule lookup table** → scikit-learn (Phase 2) | Start deterministic, add ML later |

---

## 3. THREAT MODEL (What You're Detecting)

| Threat | Signal | Detection Method |
|---|---|---|
| AI overlay (Cluely-style) | Hidden process + hotkey burst | psutil blacklist + typing spike |
| Remote taker / proxy | IP change, concurrent login | Session tunnel metadata |
| ChatGPT/Copilot tab | Browser nav to AI domain | Extension + SNI match |
| Screen sharing | VM/RDP process, extra display | psutil + hardware check |
| Clipboard paste | Large char burst <1s | Typing monitor pattern |
| Gaze/attention loss | Head turn >45°, face off-frame | MediaPipe head pose |

---

## 4. OPTIMIZED MODULE DESIGN

### 4.1 Network Layer
**Rule: Sample, don't stream.**

```python
# EMA-based traffic monitor (not raw packet store)
metric = 0.2 * new_value + 0.8 * prev_metric   # update every 5s
if abs(metric - baseline) > 2 * sigma: trigger_alert()

# Domain cache (avoid repeat API calls)
domain_cache = LRUCache(maxsize=500)  # 90% fewer threat-DB lookups

# WebSocket: log state changes only
ws_log = ["open", "close", "burst"]   # NOT every frame
```

**Storage target:** `50MB → 12MB` per session  
**Log format per event:** `[ts_delta_ms, event_code, domain_hash, bytes]` (4 fields, not full JSON objects)

---

### 4.2 Browser Layer
**Rule: Aggregate, don't enumerate.**

```python
# Tab switching — store metrics, not event list
tab_metrics = {
  "switches_per_min": 2.5,
  "avg_focus_sec": 180,
  "suspicious_domains": ["chatgpt.com", "copilot.microsoft.com"]
}
# Alert only: >5 focus changes per 10s window

# Navigation — delta encoding
transitions = [{"from": 0, "to": 1, "dur_sec": 45}, ...]  # domain index refs

# Copy-paste — flag only suspicious patterns:
#   1. >200 chars burst in <1 sec
#   2. >3 pastes in <30 sec
#   3. Repeated identical content
```

**Storage target:** `30MB → 2MB` per session

---

### 4.3 System/Process Layer
**Rule: Hash-diff, don't rescan.**

```python
# Startup: snapshot + hash process list
baseline_hash = hash(frozenset(get_process_names()))

# Every 30s: compare hash only (0.0001 cost if unchanged)
current_hash = hash(frozenset(get_process_names()))
if current_hash != baseline_hash:
    delta = current_set - baseline_set   # log only NEW processes

# One-time VM fingerprint at session start
vm_flags = check_cpu_flags() | check_audio_devices() | check_disk_model()
# Cache result; never re-run unless anomaly triggered

BLACKLIST = {"zoom", "anydesk", "teamviewer", "rustdesk", "vmware", 
             "virtualbox", "obs", "chatgpt", "copilot-app"}
```

**Storage target:** `15MB → 0.5MB` per session

---

### 4.4 Webcam Layer
**Rule: Zones + adaptive FPS, not continuous precision.**

```python
# Adaptive sampling
fps = 1   # default
if anomaly_detected: fps = 5  # burst to 5fps for 30s

# Gaze zones (not pixel coordinates)
ZONES = ["center", "edge", "off_screen", "down"]

# Head pose: anomaly-only logging
baseline = avg_pose(first_20_frames)   # freeze after 20 frames
if deviation > 1.5 * sigma:
    log_event("gaze_drift", zone, duration_sec)

# Attention window (per 5 minutes)
attention = {
  "score": 0–100,
  "drift_count": int,
  "off_screen_sec": int,
  "side_glances": int
}
```

**Storage target:** `100MB → 15MB` per session  
**Use MediaPipe Lite** (not full model) — 70% fewer compute tokens

---

### 4.5 Typing Layer
**Rule: Windows + macro metrics, not keystrokes.**

```python
# 30-second statistical window
window = {
  "avg_interval_ms": 85,
  "std_dev": 12,
  "wpm": 72,
  "key_count": 450
}
# Flag: sudden WPM spike >150 (paste), rhythm std_dev jump >2σ

# Paste detection (no keystroke log needed)
if char_burst > 200 and duration < 1.0:   # physically impossible to type
    log_event("paste_detected", char_count, timestamp)

# Idle detection
if idle > 30s during_coding_phase: log_event("idle_anomaly")
```

**Storage target:** `20MB → 0.3MB` per session

---

## 5. ANOMALY ENGINE

### Scoring — Lookup Table (not dynamic computation)

```python
RISK_TABLE = {
  "paste_small":      2,   "paste_large":      8,   "paste_code": 12,
  "tab_switch_low":   0,   "tab_switch_high":  5,
  "gaze_normal":      0,   "gaze_repeated":    6,   "gaze_sustained": 10,
  "domain_safe":      0,   "domain_suspicious":8,   "domain_ai_helper": 15,
  "blacklist_process":20,  "vm_detected":      10,
  "typing_spike":     8,   "idle_anomaly":     3,
}

# Correlation bonus (only checked when base score > 5)
if paste_event AND tab_to_ai_domain: score += 5
```

### Processing — 30s Buffered Windows

```python
# Collect all signals in buffer, process together
buffer = {
  "window": [T, T+30],
  "network":  [anomalies_only],
  "browser":  [anomalies_only],
  "webcam":   {summary_stats},
  "typing":   {summary_stats},
  "system":   [delta_processes]
}
# Then: score = sum(RISK_TABLE[event] for event in buffer)
# Alert threshold: score > 15 → flag for review; score > 30 → high priority
```

### Baseline — Freeze After 5 Minutes

```python
baseline = capture_first_5min()   # WPM, tab rate, focus, network
# NEVER update baseline after this point
# All comparisons reference this frozen profile
```

---

## 6. COMPACT EVENT SCHEMA

```python
# Binary-compact event record (not full JSON)
# [event_code(1B), ts_delta_ms(3B), value1(2B), value2(2B)] = 8 bytes/event
EVENT_CODES = {
  0x01: "dns_query",     0x02: "paste",        0x03: "tab_switch",
  0x04: "gaze_drift",    0x05: "process_new",  0x06: "ws_connect",
  0x07: "idle",          0x08: "typing_spike", 0x09: "tls_connect"
}

# Human-readable report (generated on demand only)
report_row = {
  "ts": "10:05:12",
  "module": "Browser",
  "event": "tab_switch",
  "detail": "→ chatgpt.com",
  "score": 15
}
```

**Storage:** Circular buffers per module (fixed size, no unbounded growth)
- Network: last 1000 events
- Browser: last 500 events
- Typing: last 100 windows

**Lazy loading:** Full traces stored on disk; load only if `total_score > threshold`

---

## 7. BUILD PHASES

### Phase 1 — Foundation (Week 1–2) | Target: 55–60% savings

| Task | Time | Savings |
|---|---|---|
| WireGuard tunnel + ephemeral keys | 1 day | — |
| DNS/SNI capture with 5s sampling | 2 hrs | 75% network |
| Tab-switch aggregation (metrics, not log) | 1 hr | 95% browser |
| Process whitelist + hash-diff | 3 hrs | 99% system |
| Typing window stats (30s buckets) | 2 hrs | 99% typing |
| Lookup-table scoring engine | 4 hrs | 95% engine |
| Event binary compression | 3 hrs | 70% storage |

### Phase 2 — Webcam + Buffering (Week 3–4) | Additional: +10–15%

| Task | Time | Savings |
|---|---|---|
| MediaPipe Lite + 1fps adaptive sampling | 4 hrs | 97% webcam |
| Zoned gaze estimation | 8 hrs | 70% compute |
| 30s buffered window processing | 6 hrs | 70% engine |
| Circular buffers + lazy loading | 5 hrs | 85% memory |
| Domain LRU cache | 2 hrs | 90% lookups |

### Phase 3 — Advanced (Week 5–6) | Additional: +5%

| Task | Time |
|---|---|
| Delta-of-delta time-series compression | 6 hrs |
| Triggered correlation analysis | 5 hrs |
| ML baseline (Isolation Forest on labeled data) | 8 hrs |
| Dashboard + report generator | 4 hrs |

---

## 8. SESSION LIFECYCLE

```
START
  │
  ├─► Generate ephemeral WireGuard keys → spin up tunnel
  ├─► Capture 5-min baseline (freeze after)
  ├─► One-time VM/process fingerprint
  │
RUNNING (per 30s buffer)
  ├─► Sample DNS/SNI (every 5s)
  ├─► Read tab metrics (aggregated)
  ├─► Hash-diff process list
  ├─► Sample webcam frame (1fps adaptive)
  ├─► Read typing window stats
  ├─► Score buffer → alert if > threshold
  │
END
  ├─► Flush circular buffers to SQLite
  ├─► Generate timestamped event report
  ├─► Revoke WireGuard keys / tear down tunnel
  ├─► Encrypt + store (retain only if flagged)
  └─► Purge raw data (GDPR minimal retention)
```

---

## 9. PRIVACY CONSTRAINTS (Non-Negotiable)

- **Consent prompt** before session starts — explain every signal collected
- **No raw video storage** — only pose/zone metadata
- **No keystroke content** — only timing statistics
- **Hashed IDs** — no plaintext user IDs in logs
- **Encryption at rest** — AES-256 for SQLite file
- **Auto-purge** — clean sessions deleted after report generation
- **GDPR scope** — logs expire after review window (e.g. 30 days)

---

## 10. EXPECTED OUTCOMES

| Metric | Before | After Phase 1 | After Full |
|---|---|---|---|
| Storage/session | ~215 MB | ~91 MB | ~55 MB |
| Tokens/session | ~50,000 | ~20,000 | ~12,500 |
| Processing overhead | 100% | 40% | 25% |
| Detection accuracy | baseline | >95% | >95% |
| False positive rate | — | <5% | <5% |

**Annual savings at 1000 interviews/month:** ~$4,500–8,000 in token + storage costs

---

## 11. VALIDATION CHECKLIST

- [ ] Anomaly detection accuracy ≥ 95% (test with 50+ labeled sessions)
- [ ] False positive rate < 5%
- [ ] Token consumption reduced > 60%
- [ ] Storage reduced > 70%
- [ ] No PII in raw logs
- [ ] Report generated < 5 minutes post-session
- [ ] Tunnel teardown completes < 5s after session end
- [ ] Baseline frozen correctly at minute 5
- [ ] Circular buffers prevent memory growth in 3h+ sessions

---

*Built with: WireGuard · PyShark · MediaPipe Lite · psutil · Chrome MV3 · SQLite · Python 3.11+*  
*All components free/OSS. No cloud dependencies required for MVP.*

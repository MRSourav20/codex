# Optimus Monitoring Platform

A live intelligence monitoring system that captures, categorizes, enriches, and reports on network activity in real-time.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Sarvam API key in `.env`

```
SARVAM_API_KEY=sk_...
```

### 3. (Optional) Configure email delivery in `.env`

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-app-password
SMTP_TO=recipient@example.com
```

### 4. Start the monitor (requires root for packet capture)

```bash
sudo python3 optimus.py
```

---

## Demo Mode (Phase 7)

Open a **second terminal** and run DNS lookups while the dashboard is running:

```bash
nslookup github.com
nslookup chat.openai.com
nslookup claude.ai
nslookup google.com
nslookup stackoverflow.com
nslookup youtube.com
nslookup perplexity.ai
```

The dashboard captures and categorizes each domain in real-time.

---

## On Exit (Ctrl+C)

When you stop the monitor, Optimus automatically:

1. Generates `reports/<session_id>.json`
2. Generates `reports/<session_id>.html` (styled dark-theme report)
3. Generates `reports/<session_id>.txt` (plain text summary)
4. Sends email (if SMTP configured)

---

## Architecture

```
optimus.py
├── backend/session_manager.py         Session lifecycle
├── backend/dns_monitor/
│   ├── dns_capture.py                 Packet capture (pyshark)
│   └── dns_logger.py                  SQLite logging
├── backend/enrichment/
│   ├── dns_categorizer_v2.py          Rule-based categorization
│   └── Sarvam_enrichment.py           AI enrichment (Sarvam API)
├── backend/intelligence/
│   └── domain_intelligence_db.py      Local domain cache
├── backend/anomaly_engine/
│   └── dns_event_detector.py          Suspicious event detection
├── backend/reporting/
│   └── report_generator.py            JSON / HTML / TXT reports
├── backend/email/
│   └── smtp_sender.py                 Email delivery
└── backend/opencv_events.py           Face monitoring (optional)
```

---

## Reports Location

All reports are saved in `reports/` directory:

| File | Description |
|------|-------------|
| `<session_id>.json` | Full structured data |
| `<session_id>.html` | Styled HTML for sharing |
| `<session_id>.txt`  | Plain text summary |

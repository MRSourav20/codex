#!/usr/bin/env python3
"""
Optimus – Monitoring Platform
Single entrypoint. Run this file to start a monitoring session.

Usage:
    sudo python3 optimus.py

Demo (in another terminal):
    nslookup github.com
    nslookup chat.openai.com
    nslookup claude.ai
"""

import os
import sys
import signal
import threading
import time
import logging
from datetime import datetime
from collections import defaultdict, deque
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# ── Rich imports ──────────────────────────────────────────────────────────────
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.console import Console
from rich.progress_bar import ProgressBar
from rich import box

# ── Internal imports ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.session_manager import SessionManager
from backend.dns_monitor.dns_capture import DNSPacketCapture
from backend.dns_monitor.dns_logger import DNSLogger
from backend.enrichment.dns_categorizer_v2 import DomainCategorizer
from backend.intelligence.domain_intelligence_db import DomainIntelligenceDB
from backend.enrichment.Sarvam_enrichment import SarvamEnrichment, EnrichmentPipeline
from backend.anomaly_engine.dns_event_detector import SuspiciousEventDetector
from backend.reporting.report_generator import ReportGenerator
from backend.email.smtp_sender import SmtpSender

# Optional OpenCV
try:
    from backend.opencv_events import OpenCVMonitor
    OPENCV_AVAILABLE = True
except Exception:
    OPENCV_AVAILABLE = False

logging.basicConfig(level=logging.WARNING)
console = Console()

# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "AI Assistant":     "bright_red",
    "Development":      "cyan",
    "Coding Platform":  "blue",
    "Search Engine":    "green",
    "Media":            "magenta",
    "Social Media":     "yellow",
    "Cloud Services":   "cyan",
    "Communication":    "white",
    "Unknown":          "dim",
}

SOURCE_ICONS = {
    "rule-based": "⚡",
    "sarvam-m":   "🤖",
    "cache":      "💾",
    "unknown":    "❓",
}


class OptimusMonitor:
    def __init__(self, interface: str = "any"):
        self.interface   = interface
        self.running     = True
        self.start_time  = datetime.now()

        # Session
        self.session_mgr = SessionManager()
        self.session_id  = self.session_mgr.start_session()

        # DNS pipeline
        self.capture     = DNSPacketCapture(interface=interface)
        self.logger      = DNSLogger()
        self.categorizer = DomainCategorizer()
        self.intel_db    = DomainIntelligenceDB()
        self.sarvam      = SarvamEnrichment()
        self.pipeline    = EnrichmentPipeline(self.categorizer, self.intel_db, self.sarvam)
        self.detector    = SuspiciousEventDetector(
            ai_domains=self.categorizer.get_ai_domains(),
            burst_threshold=3,
            burst_window_seconds=15,
        )

        # Reporting
        self.reporter    = ReportGenerator()
        self.mailer      = SmtpSender()

        # Live state (thread-safe behind a lock)
        self._lock             = threading.Lock()
        self.domain_feed: deque = deque(maxlen=15)   # (domain, category, conf, source, ts)
        self.category_counts: dict = defaultdict(int)
        self.risk_events: deque    = deque(maxlen=8)
        self.stats = {
            "total":   0,
            "unique":  0,
            "enriched": 0,
            "risk_score": 0,
        }
        self._seen_domains: set = set()

        # Signal handling
        signal.signal(signal.SIGINT,  self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    # ── Dashboard layout ──────────────────────────────────────────────────────
    def _make_header(self) -> Panel:
        elapsed = datetime.now() - self.start_time
        h, rem  = divmod(int(elapsed.total_seconds()), 3600)
        m, s    = divmod(rem, 60)
        runtime = f"{h:02d}:{m:02d}:{s:02d}"
        text = Text(justify="center")
        text.append("◈  OPTIMUS  ", style="bold bright_cyan")
        text.append("│", style="dim")
        text.append(f"  Session {self.session_id}  ", style="bold white")
        text.append("│", style="dim")
        text.append(f"  ⏱  {runtime}  ", style="bold green")
        text.append("│", style="dim")
        text.append("  LIVE MONITORING  ", style="bold bright_yellow")
        return Panel(Align.center(text), style="bold bright_cyan on grey11", padding=(0, 1))

    def _make_dns_feed(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAD, expand=True, show_footer=False,
                      header_style="bold bright_cyan")
        table.add_column("Time",     style="dim",          width=8)
        table.add_column("Icon",     style="",             width=3, no_wrap=True)
        table.add_column("Domain",   style="bold",         no_wrap=True)
        table.add_column("Category", justify="right",      no_wrap=True)
        table.add_column("Conf",     justify="right",      width=5)
        with self._lock:
            feed = list(self.domain_feed)
        for (domain, category, conf, source, ts) in reversed(feed):
            color = CATEGORY_COLORS.get(category, "white")
            icon  = SOURCE_ICONS.get(source, "  ")
            conf_str = f"{conf:.0%}" if conf else "—"
            table.add_row(ts, icon, domain, f"[{color}]{category}[/]", conf_str)
        return Panel(table, title="[bold bright_cyan]◉ LIVE DNS FEED[/]",
                     border_style="bright_cyan", padding=(0, 1))

    def _make_categories(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True, header_style="bold white")
        table.add_column("Category", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("", no_wrap=True)
        with self._lock:
            cc = dict(self.category_counts)
        total = max(sum(cc.values()), 1)
        for cat, count in sorted(cc.items(), key=lambda x: -x[1]):
            color    = CATEGORY_COLORS.get(cat, "white")
            bar_fill = int((count / total) * 20)
            bar      = f"[{color}]{'█' * bar_fill}{'░' * (20 - bar_fill)}[/]"
            table.add_row(f"[{color}]{cat}[/]", str(count), bar)
        return Panel(table, title="[bold white]◈ CATEGORY DISTRIBUTION[/]",
                     border_style="white", padding=(0, 1))

    def _make_risk_events(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True, header_style="bold red")
        table.add_column("Event", style="bold red")
        table.add_column("Domain", style="yellow", no_wrap=True)
        table.add_column("Severity", justify="center")
        with self._lock:
            events = list(self.risk_events)
        if not events:
            table.add_row("[dim]No suspicious events detected[/]", "", "")
        for ev in reversed(events):
            sev   = ev.get("severity", "INFO")
            color = "bright_red" if sev == "HIGH" else "yellow" if sev == "MEDIUM" else "cyan"
            table.add_row(ev.get("event_type", "—"),
                          ev.get("domain") or "—",
                          f"[{color}]{sev}[/]")
        return Panel(table, title="[bold red]⚠ RISK EVENTS[/]",
                     border_style="red", padding=(0, 1))

    def _make_stats(self) -> Panel:
        with self._lock:
            s = dict(self.stats)
        score = min(s["risk_score"], 100)
        if score < 30:
            score_color = "green"
        elif score < 70:
            score_color = "yellow"
        else:
            score_color = "bright_red"
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value",  justify="right", style="bold white")
        table.add_row("Total Domains",    str(s["total"]))
        table.add_row("Unique Domains",   str(s["unique"]))
        table.add_row("AI-Enriched",      str(s["enriched"]))
        table.add_row("Risk Score",       f"[{score_color}]{score:.0f}/100[/]")
        return Panel(table, title="[bold cyan]◈ SESSION STATS[/]",
                     border_style="cyan", padding=(0, 1))

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header",  size=3),
            Layout(name="body")
        )
        layout["body"].split_row(
            Layout(name="left",  ratio=3),
            Layout(name="right", ratio=2)
        )
        layout["right"].split_column(
            Layout(name="cats",   ratio=2),
            Layout(name="risk",   ratio=2),
            Layout(name="stats",  ratio=1),
        )
        layout["header"].update(self._make_header())
        layout["left"].update(self._make_dns_feed())
        layout["cats"].update(self._make_categories())
        layout["risk"].update(self._make_risk_events())
        layout["stats"].update(self._make_stats())
        return layout

    # ── DNS Capture thread ────────────────────────────────────────────────────
    def _capture_thread(self):
        try:
            import pyshark
            cap = pyshark.LiveCapture(
                interface=self.interface,
                display_filter="dns",
                use_json=True,
                include_raw=False,
            )
            for pkt in cap.sniff_continuously():
                if not self.running:
                    cap.close()
                    break
                try:
                    self.capture.packet_count += 1
                    extracted = self.capture._extract_dns_domains(pkt)
                    for item in extracted:
                        domain = item["domain"] if isinstance(item, dict) else item
                        self._handle_domain(domain)
                except Exception:
                    pass
        except PermissionError:
            console.print("[red]ERROR: root/sudo required for packet capture.[/red]")
            sys.exit(1)
        except Exception as e:
            if self.running:
                logging.error(f"Capture thread: {e}")

    def _handle_domain(self, domain: str):
        ts  = datetime.now().strftime("%H:%M:%S")
        cat, conf, source = self.pipeline.enrich(domain)

        with self._lock:
            self.stats["total"] += 1
            if domain not in self._seen_domains:
                self._seen_domains.add(domain)
                self.stats["unique"] += 1
            if source == "sarvam-m":
                self.stats["enriched"] += 1
            self.category_counts[cat] += 1
            self.domain_feed.append((domain, cat, conf, source, ts))

        # Risk events
        events = self.detector.detect_events(domain, datetime.now().isoformat())
        with self._lock:
            for ev in events:
                self.risk_events.append(ev)
                self.stats["risk_score"] = min(
                    self.stats["risk_score"] + (40 if ev.get("severity") == "HIGH" else 15),
                    100
                )

        # Log
        self.logger.log_dns_query(
            domain=domain,
            timestamp=datetime.now().isoformat(),
            category=cat,
            source=source,
            confidence=conf,
            session_id=self.session_id,
        )

    # ── Shutdown ──────────────────────────────────────────────────────────────
    def _handle_shutdown(self, *_):
        self.running = False

    def _finalize(self):
        console.print("\n[bold yellow]⏹  Stopping capture…[/bold yellow]")
        with self._lock:
            s = dict(self.stats)
            udoms = list(self._seen_domains)
            cats  = dict(self.category_counts)
            events = list(self.risk_events)

        self.session_mgr.end_session(self.session_id, {
            "total_packets": self.capture.packet_count,
            "unique_domains": s["unique"],
            "risk_score": s["risk_score"],
        })

        # Reports
        console.print("[bold cyan]📄  Generating reports…[/bold cyan]")
        paths = self.reporter.generate(
            session_id=self.session_id,
            started_at=self.start_time.isoformat(),
            ended_at=datetime.now().isoformat(),
            unique_domains=udoms,
            categories=cats,
            risk_events=events,
            stats=s,
        )
        self.session_mgr.save_report_paths(
            self.session_id, paths["json"], paths["html"], paths["txt"]
        )
        console.print(f"[green]✓ JSON:[/green]  {paths['json']}")
        console.print(f"[green]✓ HTML:[/green]  {paths['html']}")
        console.print(f"[green]✓ TXT:[/green]   {paths['txt']}")

        # Email
        console.print("[bold cyan]📧  Sending email report…[/bold cyan]")
        sent = self.mailer.send(self.session_id, paths)
        if sent:
            console.print("[green]✓ Email delivered.[/green]")
        else:
            console.print("[yellow]⚠  Email not sent (check SMTP config).[/yellow]")

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        t = threading.Thread(target=self._capture_thread, daemon=True)
        t.start()

        try:
            with Live(self._build_layout(), refresh_per_second=2, screen=True) as live:
                while self.running:
                    time.sleep(0.5)
                    live.update(self._build_layout())
        except KeyboardInterrupt:
            self.running = False
        finally:
            self._finalize()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Optimus Monitoring Platform")
    parser.add_argument("--interface", default="any", help="Network interface (default: any)")
    args = parser.parse_args()

    monitor = OptimusMonitor(interface=args.interface)
    monitor.run()

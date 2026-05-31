"""
Optimus Report Generator – produces JSON, HTML, and TXT session reports.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


class ReportGenerator:
    def __init__(self, output_dir: str = REPORTS_DIR):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    # ── Public ────────────────────────────────────────────────────────────────
    def generate(
        self,
        session_id: str,
        started_at: str,
        ended_at: str,
        unique_domains: List[str],
        categories: Dict[str, int],
        risk_events: List[Dict],
        stats: Dict[str, Any],
    ) -> Dict[str, str]:
        """Generate all 3 report formats. Returns dict of {format: path}."""
        # Deduplicate domains
        unique_domains = list(set(unique_domains))
        duration_secs  = self._duration(started_at, ended_at)

        data = {
            "session_id":     session_id,
            "started_at":     started_at,
            "ended_at":       ended_at,
            "duration_secs":  duration_secs,
            "unique_domains": unique_domains,
            "categories":     categories,
            "risk_events":    risk_events,
            "stats":          stats,
        }

        json_path = self._write_json(session_id, data)
        html_path = self._write_html(session_id, data)
        txt_path  = self._write_txt(session_id, data)

        return {"json": json_path, "html": html_path, "txt": txt_path}

    # ── Private ───────────────────────────────────────────────────────────────
    @staticmethod
    def _duration(started_at: str, ended_at: str) -> int:
        try:
            s = datetime.fromisoformat(started_at)
            e = datetime.fromisoformat(ended_at)
            return int((e - s).total_seconds())
        except Exception:
            return 0

    def _write_json(self, session_id: str, data: dict) -> str:
        path = os.path.join(self.output_dir, f"{session_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def _write_txt(self, session_id: str, data: dict) -> str:
        path = os.path.join(self.output_dir, f"{session_id}.txt")
        dur  = data["duration_secs"]
        m, s = divmod(dur, 60)
        lines = [
            "=" * 60,
            "  OPTIMUS MONITORING REPORT",
            "=" * 60,
            f"Session ID  : {data['session_id']}",
            f"Started     : {data['started_at']}",
            f"Ended       : {data['ended_at']}",
            f"Duration    : {m}m {s}s",
            f"Unique Doms : {len(data['unique_domains'])}",
            f"Risk Score  : {data['stats'].get('risk_score', 0):.0f}/100",
            "",
            "CATEGORY DISTRIBUTION",
            "-" * 40,
        ]
        for cat, count in sorted(data["categories"].items(), key=lambda x: -x[1]):
            lines.append(f"  {cat:<25} {count}")
        lines += ["", "RISK EVENTS", "-" * 40]
        if data["risk_events"]:
            for ev in data["risk_events"]:
                lines.append(f"  [{ev.get('severity','?')}] {ev.get('event_type','?')} — {ev.get('domain','—')}")
        else:
            lines.append("  None detected.")
        lines += ["", "DOMAIN LOG", "-" * 40]
        for d in sorted(data["unique_domains"]):
            lines.append(f"  {d}")
        lines.append("=" * 60)
        with open(path, "w") as f:
            f.write("\n".join(lines))
        return path

    def _write_html(self, session_id: str, data: dict) -> str:
        path = os.path.join(self.output_dir, f"{session_id}.html")
        dur  = data["duration_secs"]
        m, s = divmod(dur, 60)
        score = data['stats'].get('risk_score', 0)
        score_color = "#22c55e" if score < 30 else "#f59e0b" if score < 70 else "#ef4444"

        cat_rows = "\n".join(
            f"<tr><td>{c}</td><td>{n}</td></tr>"
            for c, n in sorted(data["categories"].items(), key=lambda x: -x[1])
        )
        evt_rows = "\n".join(
            f"<tr><td style='color:#ef4444'>{e.get('event_type','?')}</td>"
            f"<td>{e.get('domain','—')}</td>"
            f"<td>{e.get('severity','?')}</td></tr>"
            for e in data["risk_events"]
        ) or "<tr><td colspan='3'>None detected.</td></tr>"
        dom_items = "\n".join(f"<li>{d}</li>" for d in sorted(data["unique_domains"]))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Optimus Report – {session_id}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0a0a0a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:2rem}}
    h1{{color:#22d3ee;font-size:1.8rem;margin-bottom:0.3rem}}
    h2{{color:#94a3b8;font-size:1rem;font-weight:400;margin-bottom:2rem}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin:1.5rem 0}}
    .card{{background:#111827;border:1px solid #1e293b;border-radius:12px;padding:1.2rem}}
    .card h3{{color:#64748b;font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem}}
    .card .val{{font-size:1.6rem;font-weight:700;color:#f1f5f9}}
    .risk{{color:{score_color}}}
    table{{width:100%;border-collapse:collapse;background:#111827;border-radius:8px;overflow:hidden;margin:.8rem 0}}
    th{{background:#1e293b;color:#94a3b8;padding:.6rem 1rem;text-align:left;font-size:.8rem;text-transform:uppercase}}
    td{{padding:.55rem 1rem;border-bottom:1px solid #1e293b;font-size:.9rem}}
    tr:last-child td{{border:none}}
    section{{margin:2rem 0}}
    section h3{{color:#22d3ee;margin-bottom:.6rem;font-size:1rem}}
    ul{{list-style:none;columns:3;column-gap:1rem}}
    li{{padding:.2rem 0;color:#cbd5e1;font-size:.85rem;border-bottom:1px solid #1e293b}}
    footer{{margin-top:3rem;color:#475569;font-size:.8rem}}
    .badge{{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.75rem;font-weight:600;background:#1e293b;color:#94a3b8}}
  </style>
</head>
<body>
  <h1>◈ Optimus Monitoring Report</h1>
  <h2>Session {session_id} &nbsp;·&nbsp; {data['started_at'][:10]}</h2>

  <div class="grid">
    <div class="card"><h3>Session ID</h3><div class="val" style="font-size:1.2rem">{session_id}</div></div>
    <div class="card"><h3>Duration</h3><div class="val">{m}m {s}s</div></div>
    <div class="card"><h3>Unique Domains</h3><div class="val">{len(data['unique_domains'])}</div></div>
    <div class="card"><h3>Risk Score</h3><div class="val risk">{score:.0f}<span style="font-size:1rem;color:#475569">/100</span></div></div>
  </div>

  <section>
    <h3>Category Distribution</h3>
    <table>
      <tr><th>Category</th><th>Count</th></tr>
      {cat_rows}
    </table>
  </section>

  <section>
    <h3>Risk Events</h3>
    <table>
      <tr><th>Event</th><th>Domain</th><th>Severity</th></tr>
      {evt_rows}
    </table>
  </section>

  <section>
    <h3>Domain Log ({len(data['unique_domains'])} unique)</h3>
    <ul>{dom_items}</ul>
  </section>

  <footer>Generated by Optimus · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</footer>
</body>
</html>"""
        with open(path, "w") as f:
            f.write(html)
        return path

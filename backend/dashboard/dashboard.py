import time
import os
import sys
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.console import Console

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.session_manager import SessionManager
from backend.dns_monitor.dns_logger import DNSLogger
from backend.wg_peer import WGPeerManager
from backend.risk_engine import RiskEngine

console = Console()

class OptimusDashboard:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_manager = SessionManager()
        self.dns_logger = DNSLogger()
        self.risk_engine = RiskEngine()
        self.wg_manager = WGPeerManager()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main")
        )
        layout["main"].split_row(
            Layout(name="left_column", ratio=1),
            Layout(name="right_column", ratio=2)
        )
        layout["left_column"].split(
            Layout(name="status", ratio=1),
            Layout(name="risk", ratio=1)
        )
        layout["right_column"].split(
            Layout(name="domains", ratio=2),
            Layout(name="events", ratio=1)
        )
        return layout

    def get_status_panel(self, session_data) -> Panel:
        status = session_data[5]
        candidate_ip = session_data[4]
        tunnel = session_data[8] if len(session_data) > 8 else "Pending"
        
        table = Table.grid(padding=1)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")
        
        table.add_row("Session ID", self.session_id)
        table.add_row("Status", f"[green]ACTIVE[/green]" if status == "active" else f"[red]{status.upper()}[/red]")
        table.add_row("Candidate IP", candidate_ip)
        table.add_row("Tunnel", f"[green]CONNECTED[/green]" if tunnel == "connected" else f"[yellow]{tunnel.upper()}[/yellow]")
        
        return Panel(table, title="[bold white]Candidate Status[/]", border_style="blue")
        
    def get_risk_panel(self) -> Panel:
        result = self.risk_engine.evaluate_session(self.session_id)
        score = result["score"]
        level = result["level"]
        
        color = "green" if level == "Low" else "yellow" if level == "Medium" else "red"
        content = Align.center(
            f"\n[bold {color} text-align=center]RISK LEVEL: {level.upper()}[/]\n\n"
            f"[bold white text-align=center]SCORE: {score}/100[/]\n"
        )
        return Panel(content, title="[bold white]Integrity Engine[/]", border_style=color)

    def get_domains_panel(self) -> Panel:
        # Get recent domains from DB (would be filtered by session ideally)
        # Note: currently dns_queries has session_id, so let's query it
        import sqlite3
        conn = sqlite3.connect(self.dns_logger.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT domain, query_type, category, confidence FROM dns_queries WHERE session_id = ? ORDER BY timestamp DESC LIMIT 15", (self.session_id,))
        rows = cursor.fetchall()
        conn.close()
        
        table = Table(expand=True)
        table.add_column("Domain", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Category", justify="right", style="green")
        table.add_column("Conf.", justify="right", style="yellow")
        
        for row in rows:
            table.add_row(row[0], row[1], row[2] or "Unknown", f"{row[3]:.1f}" if row[3] else "-")
            
        return Panel(table, title="[bold white]Live Domain Feed[/]", border_style="cyan")

    def get_events_panel(self) -> Panel:
        events = self.dns_logger.get_suspicious_events(limit=5, session_id=self.session_id)
        table = Table(expand=True)
        table.add_column("Event Type", style="bold red")
        table.add_column("Count", justify="right", style="yellow")
        
        for e in events:
            table.add_row(e["event_type"], str(e["count"]))
            
        if not events:
            table.add_row("[green]No suspicious events detected.[/green]", "")
            
        return Panel(table, title="[bold white]Suspicious Events[/]", border_style="red")

    def render(self) -> Layout:
        session_data = self.session_manager.get_session(self.session_id)
        if not session_data:
            return Layout(Panel("[red]Session not found[/red]"))
        
        # Periodically check WireGuard tunnel internally if pending
        tunnel_status = session_data[8] if len(session_data) > 8 else "pending"
        if tunnel_status != "connected":
            self.wg_manager.check_connection_status(self.session_id)

        layout = self.generate_layout()
        layout["header"].update(Panel(Align.center("[bold cyan]OPTIMUS CONTROL CENTER[/bold cyan]  |  LIVE INTELLIGENCE STREAM"), style="bold blue on black"))
        layout["status"].update(self.get_status_panel(session_data))
        layout["risk"].update(self.get_risk_panel())
        layout["domains"].update(self.get_domains_panel())
        layout["events"].update(self.get_events_panel())
        
        return layout

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashboard.py <SESSION_ID>")
        sys.exit(1)
        
    dashboard = OptimusDashboard(sys.argv[1])
    try:
        with Live(dashboard.render(), refresh_per_second=2, screen=True) as live:
            while True:
                time.sleep(0.5)
                live.update(dashboard.render())
    except KeyboardInterrupt:
        print("Exiting dashboard...")

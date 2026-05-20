from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .codexbar_client import CodexBarClient, CodexBarError
from .formatters.waybar_formatter import format_waybar
from .models import UsageReport, utc_now_iso
from .normalize import normalize_usage


@dataclass(slots=True)
class DashboardState:
    client: CodexBarClient
    providers: list[str]
    source: str
    refresh_seconds: int
    cost_refresh_seconds: int
    live_report: UsageReport = field(default_factory=lambda: UsageReport(providers=[]))
    cost_report: UsageReport = field(default_factory=lambda: UsageReport(providers=[]))
    live_error: str | None = None
    cost_error: str | None = None
    live_updated_at: str | None = None
    cost_updated_at: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop_event: threading.Event = field(default_factory=threading.Event)

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self._refresh_loop, daemon=True)
        thread.start()
        return thread

    def refresh_once(self, force_cost: bool = False) -> None:
        self._refresh_live()
        if force_cost or not self.cost_updated_at:
            self._refresh_cost()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "generated_at": utc_now_iso(),
                "refresh_seconds": self.refresh_seconds,
                "live": self.live_report.to_dict(),
                "cost": self.cost_report.to_dict(include_raw=True),
                "live_error": self.live_error,
                "cost_error": self.cost_error,
                "live_updated_at": self.live_updated_at,
                "cost_updated_at": self.cost_updated_at,
            }

    def waybar(self) -> str:
        with self.lock:
            return format_waybar(self.live_report)

    def _refresh_loop(self) -> None:
        next_cost = 0.0
        while not self.stop_event.is_set():
            now = time.monotonic()
            self._refresh_live()
            if now >= next_cost:
                self._refresh_cost()
                next_cost = now + self.cost_refresh_seconds
            self.stop_event.wait(self.refresh_seconds)

    def _refresh_live(self) -> None:
        try:
            report = normalize_usage(
                self.client.fetch_usage_json(self.providers, source=self.source)
            )
            error = None
        except CodexBarError as exc:
            report = UsageReport(providers=[], error=str(exc))
            error = str(exc)

        with self.lock:
            self.live_report = report
            self.live_error = error
            self.live_updated_at = utc_now_iso()

    def _refresh_cost(self) -> None:
        try:
            report = normalize_usage(self.client.fetch_cost_json(self.providers))
            error = None
        except CodexBarError as exc:
            report = UsageReport(providers=[], error=str(exc))
            error = str(exc)

        with self.lock:
            self.cost_report = report
            self.cost_error = error
            self.cost_updated_at = utc_now_iso()


class DashboardHandler(BaseHTTPRequestHandler):
    state: DashboardState

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(DASHBOARD_HTML)
            return
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/dashboard":
            self._send_json(self.state.snapshot())
            return
        if parsed.path == "/api/live":
            self._send_json(self.state.snapshot()["live"])
            return
        if parsed.path == "/api/cost":
            self._send_json(self.state.snapshot()["cost"])
            return
        if parsed.path == "/bar":
            query = parse_qs(parsed.query)
            if query.get("refresh") == ["1"]:
                self.state.refresh_once()
            self._send_text(self.state.waybar(), content_type="application/json")
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any]) -> None:
        self._send_text(
            json.dumps(payload, ensure_ascii=False),
            content_type="application/json",
        )

    def _send_html(self, payload: str) -> None:
        self._send_text(payload, content_type="text/html; charset=utf-8")

    def _send_text(self, payload: str, content_type: str) -> None:
        encoded = payload.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def run_server(
    host: str,
    port: int,
    client: CodexBarClient,
    providers: list[str],
    source: str,
    refresh_seconds: int,
    cost_refresh_seconds: int,
) -> None:
    state = DashboardState(
        client=client,
        providers=providers,
        source=source,
        refresh_seconds=refresh_seconds,
        cost_refresh_seconds=cost_refresh_seconds,
    )
    state.start()

    handler = type("BoundDashboardHandler", (DashboardHandler,), {"state": state})
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        state.stop_event.set()
        server.server_close()


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codex Usage</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101114;
      --panel: #1a1c22;
      --muted: #969ba8;
      --text: #f3f5f8;
      --line: #303440;
      --accent: #51b6ff;
      --ok: #4ade80;
      --warn: #facc15;
      --crit: #fb7185;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 15px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }
    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 28px; letter-spacing: 0; }
    .subtle { color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 18px;
      margin-top: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    .stack { display: grid; gap: 14px; }
    .provider-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }
    .badge {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      color: var(--muted);
      font-size: 12px;
    }
    .window { display: grid; gap: 7px; }
    .window-title {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-weight: 700;
    }
    .bar {
      height: 10px;
      background: #292d37;
      border-radius: 999px;
      overflow: hidden;
    }
    .bar > div {
      height: 100%;
      width: 0;
      background: var(--ok);
      transition: width .25s ease;
    }
    .bar > div.warn { background: var(--warn); }
    .bar > div.crit { background: var(--crit); }
    .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .metric strong {
      display: block;
      font-size: 20px;
      margin-top: 5px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 13px;
    }
    th, td {
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 600; }
    .right { text-align: right; }
    .error { color: var(--crit); white-space: pre-wrap; }
    @media (max-width: 800px) {
      .grid { grid-template-columns: 1fr; }
      header { align-items: start; flex-direction: column; }
      .metrics { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Codex Usage</h1>
        <p class="subtle" id="account">Loading live account limits...</p>
      </div>
      <p class="subtle" id="updated">Starting</p>
    </header>
    <div class="grid">
      <section class="stack">
        <div class="provider-head">
          <h2>Live Limits</h2>
          <span class="badge" id="source">source</span>
        </div>
        <div id="live"></div>
      </section>
      <section class="stack">
        <h2>Cost</h2>
        <div class="metrics">
          <div class="metric"><span class="subtle">Today</span><strong id="today-cost">-</strong></div>
          <div class="metric"><span class="subtle">Last 7 days</span><strong id="week-cost">-</strong></div>
          <div class="metric"><span class="subtle">Last 30 days</span><strong id="month-cost">-</strong></div>
        </div>
        <div id="models"></div>
      </section>
    </div>
  </main>
  <script>
    const money = value => '$' + Number(value || 0).toFixed(2);
    const tokens = value => {
      value = Number(value || 0);
      if (value >= 1_000_000) return (value / 1_000_000).toFixed(2) + 'M tokens';
      if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K tokens';
      return value + ' tokens';
    };
    const day = value => new Date(value + 'T00:00:00Z');
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[ch]));
    function renderWindow(window) {
      const used = Number(window.used_percent ?? 0);
      const cls = used >= 95 ? 'crit' : used >= 80 ? 'warn' : '';
      return `<div class="window">
        <div class="window-title">
          <span>${escapeHtml(window.name)}</span>
          <span>${used}% used · ${window.remaining_percent ?? '-'}% remaining</span>
        </div>
        <div class="bar"><div class="${cls}" style="width:${Math.max(0, Math.min(100, used))}%"></div></div>
        <p class="subtle">Resets ${escapeHtml(window.reset_label || window.resets_at || '-')}</p>
      </div>`;
    }
    function renderLive(live) {
      const provider = (live.providers || [])[0];
      if (!provider) {
        document.getElementById('live').innerHTML = `<p class="error">${escapeHtml(live.error || 'No live data')}</p>`;
        return;
      }
      document.getElementById('account').textContent = provider.account || 'No account';
      document.getElementById('source').textContent = provider.source || 'unknown';
      document.getElementById('live').innerHTML = (provider.windows || []).map(renderWindow).join('');
    }
    function renderCost(cost) {
      const provider = (cost.providers || [])[0];
      const raw = provider && provider.raw ? provider.raw : {};
      const rows = raw.daily || [];
      const latest = rows.length ? rows[rows.length - 1].date : null;
      const latestDate = latest ? day(latest) : null;
      const todayRows = latest ? rows.filter(row => row.date === latest) : [];
      const weekRows = latestDate ? rows.filter(row => day(row.date) >= new Date(latestDate.getTime() - 6 * 86400000)) : [];
      const sum = (items, key) => items.reduce((total, row) => total + Number(row[key] || 0), 0);
      document.getElementById('today-cost').textContent = money(sum(todayRows, 'totalCost'));
      document.getElementById('week-cost').textContent = money(sum(weekRows, 'totalCost'));
      document.getElementById('month-cost').textContent = money(raw.last30DaysCostUSD || sum(rows, 'totalCost'));
      const recent = rows.slice(-8).reverse();
      document.getElementById('models').innerHTML = `<table>
        <thead><tr><th>Date</th><th class="right">Cost</th><th class="right">Tokens</th></tr></thead>
        <tbody>${recent.map(row => `<tr><td>${escapeHtml(row.date)}</td><td class="right">${money(row.totalCost)}</td><td class="right">${tokens(row.totalTokens)}</td></tr>`).join('')}</tbody>
      </table>`;
    }
    async function refresh() {
      const response = await fetch('/api/dashboard', { cache: 'no-store' });
      const data = await response.json();
      renderLive(data.live);
      renderCost(data.cost);
      document.getElementById('updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    }
    refresh();
    setInterval(refresh, 10000);
  </script>
</body>
</html>
"""

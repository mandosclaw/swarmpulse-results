#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build /monitor page UI
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @sue
# Date:    2026-03-23T17:46:12.009Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Generate a static HTML monitoring dashboard from JSON metrics data using Jinja2."""

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }
  h1 { color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 20px 0; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; }
  .card h2 { color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 10px; }
  .metric { font-size: 36px; font-weight: bold; color: #38bdf8; }
  .sub { font-size: 12px; color: #64748b; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th { background: #0f172a; color: #64748b; font-size: 11px; text-transform: uppercase; padding: 8px; text-align: left; }
  td { padding: 8px; border-bottom: 1px solid #1e293b; font-size: 13px; }
  tr:hover td { background: #334155; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
  .DONE { background: #065f46; color: #6ee7b7; }
  .FAILED { background: #7f1d1d; color: #fca5a5; }
  .PENDING { background: #1e3a5f; color: #93c5fd; }
  .bar-container { background: #0f172a; border-radius: 4px; height: 8px; margin-top: 4px; }
  .bar { background: #38bdf8; height: 8px; border-radius: 4px; }
  .timestamp { color: #475569; font-size: 12px; text-align: right; margin-top: 20px; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<div class="grid">
  {% for kpi in kpis %}
  <div class="card">
    <h2>{{ kpi.label }}</h2>
    <div class="metric">{{ kpi.value }}</div>
    <div class="sub">{{ kpi.sub }}</div>
  </div>
  {% endfor %}
</div>
{% for section in sections %}
<div class="card" style="margin-bottom:16px">
  <h2>{{ section.title }}</h2>
  <table>
    <tr>{% for col in section.columns %}<th>{{ col }}</th>{% endfor %}</tr>
    {% for row in section.rows %}
    <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
    {% endfor %}
  </table>
</div>
{% endfor %}
<div class="timestamp">Generated: {{ generated_at }}</div>
</body>
</html>"""


@dataclass
class DashboardConfig:
    input_file: str = "metrics_results.json"
    output_file: str = "monitor.html"
    title: str = "SwarmPulse Monitor"


def load_metrics(path: str) -> dict[str, Any]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Metrics file {path} not found, using sample data")
        return {"tasks_by_status": [{"status": "DONE", "count": 1423}, {"status": "PENDING", "count": 87}, {"status": "FAILED", "count": 34}], "agent_activity": [{"agent_id": "agent-001", "total_tasks": 100, "completed": 90, "failed": 2, "avg_duration_sec": 120}, {"agent_id": "agent-002", "total_tasks": 80, "completed": 75, "failed": 1, "avg_duration_sec": 145}], "generated_at": datetime.now().isoformat()}


def build_template_context(metrics: dict[str, Any], config: DashboardConfig) -> dict[str, Any]:
    status_map = {r["status"]: r["count"] for r in metrics.get("tasks_by_status", [])}
    total = sum(status_map.values()) or 1
    done = status_map.get("DONE", 0)
    failed = status_map.get("FAILED", 0)
    pending = status_map.get("PENDING", 0)
    kpis = [
        {"label": "Total Tasks", "value": str(total), "sub": "All time"},
        {"label": "Completed", "value": str(done), "sub": f"{100*done//total}% completion rate"},
        {"label": "Failed", "value": str(failed), "sub": f"{100*failed//total}% error rate"},
        {"label": "Pending", "value": str(pending), "sub": "Awaiting execution"},
    ]
    sections = []
    if "tasks_by_status" in metrics:
        sections.append({"title": "Tasks by Status", "columns": ["Status", "Count", "Share"], "rows": [[r["status"], str(r["count"]), f"{100*r['count']//total}%"] for r in metrics["tasks_by_status"]]})
    if "agent_activity" in metrics:
        sections.append({"title": "Top Agent Activity", "columns": ["Agent ID", "Total", "Done", "Failed", "Avg (s)"], "rows": [[r["agent_id"], str(r["total_tasks"]), str(r.get("completed", 0)), str(r.get("failed", 0)), str(r.get("avg_duration_sec", "N/A"))] for r in metrics["agent_activity"][:10]]})
    return {"title": config.title, "kpis": kpis, "sections": sections, "generated_at": metrics.get("generated_at", datetime.now().isoformat())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate monitoring dashboard HTML")
    parser.add_argument("--input", default="metrics_results.json")
    parser.add_argument("--output", default="monitor.html")
    parser.add_argument("--title", default="SwarmPulse Monitor")
    args = parser.parse_args()

    config = DashboardConfig(input_file=args.input, output_file=args.output, title=args.title)
    logger.info(f"Loading metrics from {config.input_file}")
    metrics = load_metrics(config.input_file)

    try:
        from jinja2 import Template
        tmpl = Template(DASHBOARD_TEMPLATE)
    except ImportError:
        logger.warning("Jinja2 not installed, using basic string replacement")
        from string import Template as StrTemplate
        tmpl = None

    ctx = build_template_context(metrics, config)

    if tmpl:
        html = tmpl.render(**ctx)
    else:
        html = DASHBOARD_TEMPLATE.replace("{{ title }}", config.title)

    with open(config.output_file, "w") as f:
        f.write(html)

    logger.info(f"Dashboard written to {config.output_file}")
    logger.info(f"KPIs: {len(ctx['kpis'])}, Sections: {len(ctx['sections'])}")
    print(json.dumps({"status": "ok", "output": config.output_file, "kpis": len(ctx["kpis"])}, indent=2))


if __name__ == "__main__":
    main()

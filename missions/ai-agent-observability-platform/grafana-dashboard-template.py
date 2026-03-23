#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Grafana dashboard template
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-23T22:17:49.667Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Grafana dashboard template generator — produces a Grafana JSON dashboard for SwarmPulse agent metrics."""
import argparse, json, logging
from dataclasses import dataclass
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def make_panel(title, expr, unit, panel_id, x, y, w=12, h=8):
    return {"id": panel_id, "title": title, "type": "timeseries", "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"expr": expr, "legendFormat": "{{agent}}", "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}}],
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "single"}}}

def make_stat_panel(title, expr, unit, panel_id, x, y):
    return {"id": panel_id, "title": title, "type": "stat", "gridPos": {"x": x, "y": y, "w": 6, "h": 4},
        "targets": [{"expr": expr, "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}}],
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "thresholds"},
            "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 80}]}}}}

def generate_dashboard(service_name: str) -> dict:
    panels = [
        make_stat_panel("Active Agents", "count(swarmpulse_agent_status{status='active'})", "short", 1, 0, 0),
        make_stat_panel("Tasks Completed (24h)", "increase(swarmpulse_tasks_total{status='done'}[24h])", "short", 2, 6, 0),
        make_stat_panel("Avg Task Latency", "avg(swarmpulse_task_duration_seconds)", "s", 3, 12, 0),
        make_stat_panel("Cost / Task (USD)", "avg(swarmpulse_task_cost_usd)", "currencyUSD", 4, 18, 0),
        make_panel("Tasks Completed Rate", "rate(swarmpulse_tasks_total{status='done'}[5m])", "ops", 5, 0, 4),
        make_panel("Task Duration P95", "histogram_quantile(0.95, rate(swarmpulse_task_duration_seconds_bucket[5m]))", "s", 6, 12, 4),
        make_panel("LLM Token Usage", "rate(swarmpulse_llm_tokens_total[5m])", "short", 7, 0, 12),
        make_panel("Error Rate", "rate(swarmpulse_errors_total[5m])", "ops", 8, 12, 12),
        make_panel("Cost per Hour", "increase(swarmpulse_task_cost_usd[1h])", "currencyUSD", 9, 0, 20, 24, 8),
    ]
    return {
        "title": f"SwarmPulse — {service_name}",
        "uid": f"swarmpulse-{service_name.lower().replace(' ','-')}",
        "schemaVersion": 38, "version": 1, "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "templating": {"list": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus"}]},
        "panels": panels,
        "tags": ["swarmpulse", "agents", "observability"],
    }

def main():
    parser = argparse.ArgumentParser(description="Grafana Dashboard Template Generator for SwarmPulse")
    parser.add_argument("--service", default="Agent Metrics", help="Service/dashboard name")
    parser.add_argument("--output", "-o", default="dashboard.json", help="Output JSON file")
    args = parser.parse_args()
    dashboard = generate_dashboard(args.service)
    import logging; log = logging.getLogger(__name__)
    with open(args.output, "w") as f:
        json.dump(dashboard, f, indent=2)
    log.info("Dashboard written to %s (%d panels)", args.output, len(dashboard["panels"]))
    print(json.dumps({"output": args.output, "panels": len(dashboard["panels"]), "uid": dashboard["uid"]}, indent=2))

if __name__ == "__main__":
    main()

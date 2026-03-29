#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Grafana dashboard template
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-29T13:16:25.984Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Grafana dashboard template for AI Agent Observability Platform
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2025-01-14

Generates complete Grafana dashboard JSON templates for monitoring AI agents,
including distributed tracing, token costs, latency, throughput, and anomaly detection.
"""

import json
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional


class GrafanaDashboardGenerator:
    """Generate Grafana dashboard templates for AI agent observability."""

    def __init__(self, dashboard_name: str, refresh_interval: str = "30s"):
        self.dashboard_name = dashboard_name
        self.refresh_interval = refresh_interval
        self.dashboard_uid = self._generate_uid(dashboard_name)
        self.panels = []
        self.next_panel_id = 1

    @staticmethod
    def _generate_uid(name: str) -> str:
        """Generate a UID from dashboard name."""
        return "".join(c.lower() if c.isalnum() else "" for c in name)[:40]

    def add_row(self, title: str, collapsed: bool = False) -> None:
        """Add a collapsible row to the dashboard."""
        panel = {
            "id": self.next_panel_id,
            "type": "row",
            "title": title,
            "collapsed": collapsed,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": len(self.panels)},
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_timeseries_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 8,
        gridpos_w: int = 12,
        unit: str = "short",
        legend_show: bool = True,
    ) -> None:
        """Add a time series panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "timeseries",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "custom": {
                        "lineWidth": 1,
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                    "unit": unit,
                },
                "overrides": [],
            },
            "options": {
                "legend": {
                    "displayMode": "list" if legend_show else "hidden",
                    "placement": "bottom",
                    "calcs": ["mean", "max"],
                },
                "tooltip": {
                    "mode": "multi",
                    "sort": "asc",
                },
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_gauge_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 8,
        gridpos_w: int = 6,
        unit: str = "short",
        min_value: int = 0,
        max_value: int = 100,
    ) -> None:
        """Add a gauge panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "gauge",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "min": min_value,
                    "max": max_value,
                    "unit": unit,
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": max_value * 0.7},
                            {"color": "red", "value": max_value * 0.9},
                        ],
                    },
                },
                "overrides": [],
            },
            "options": {
                "orientation": "auto",
                "textMode": "auto",
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                },
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_stat_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 4,
        gridpos_w: int = 6,
        unit: str = "short",
    ) -> None:
        """Add a stat panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "stat",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                        ],
                    },
                },
                "overrides": [],
            },
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                },
                "orientation": "auto",
                "textMode": "auto",
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_heatmap_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 8,
        gridpos_w: int = 12,
    ) -> None:
        """Add a heatmap panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "heatmap",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                },
                "overrides": [],
            },
            "options": {
                "legend": {
                    "displayMode": "list",
                    "placement": "bottom",
                    "calcs": [],
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none",
                },
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_table_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 8,
        gridpos_w: int = 24,
    ) -> None:
        """Add a table panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "table",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                },
                "overrides": [],
            },
            "options": {
                "showHeader": True,
                "sortBy": [
                    {
                        "displayName": "time",
                        "desc": True,
                    }
                ],
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def add_pie_chart_panel(
        self,
        title: str,
        targets: List[Dict[str, Any]],
        gridpos_x: int = 0,
        gridpos_y: int = 0,
        gridpos_h: int = 8,
        gridpos_w: int = 12,
        unit: str = "short",
    ) -> None:
        """Add a pie chart panel."""
        panel = {
            "id": self.next_panel_id,
            "type": "piechart",
            "title": title,
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False,
                        },
                    },
                },
                "overrides": [],
            },
            "options": {
                "legend": {
                    "displayMode": "list",
                    "placement": "bottom",
                    "calcs": ["value"],
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none",
                },
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                },
            },
            "gridPos": {
                "h": gridpos_h,
                "w": gridpos_w,
                "x": gridpos_x,
                "y": gridpos_y,
            },
        }
        self.next_panel_id += 1
        self.panels.append(panel)

    def build_dashboard(self) -> Dict[str, Any]:
        """Build the complete dashboard JSON."""
        dashboard = {
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": "-- Grafana --",
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
            },
            "editable": True,
            "gnetId": None,
            "graphTooltip": 1,
            "id": None,
            "links": [],
            "panels": self.panels,
            "schemaVersion": 35,
            "style": "dark",
            "tags": ["ai-agents", "observability", "swarm-pulse"],
            "templating": {
                "list": [
                    {
                        "allValue": None,
                        "current": {
                            "selected": False,
                            "text": "Prometheus",
                            "value": "Prometheus",
                        },
                        "hide": 0,
                        "includeAll": False,
                        "label": "Data Source",
                        "multi": False,
                        "name": "datasource",
                        "options": [],
                        "query": "prometheus",
                        "refresh": 1,
                        "regex": "",
                        "skipUrlSync": False,
                        "sort": 1,
                        "tagValuesQuery": "",
                        "tags": [],
                        "tagsQuery": "",
                        "type": "datasource",
                        "useTags": False,
                    },
                    {
                        "allValue": None,
                        "current": {"selected": False, "text": "All", "value": "$__all"},
                        "datasource": "${datasource}",
                        "definition": "label_values(agent_requests_total, agent_id)",
                        "description": None,
                        "error": None,
                        "hide": 0,
                        "includeAll": True,
                        "label": "Agent ID",
                        "multi": True,
                        "name": "agent_id",
                        "options": [],
                        "query": {
                            "query": "label_values(agent_requests_total, agent_id)",
                            "refId": "StandardVariableQuery",
                        },
                        "refresh": 1,
                        "regex": "",
                        "skipUrlSync": False,
                        "sort": 1,
                        "tagValuesQuery": "",
                        "tags": [],
                        "tagsQuery": "",
                        "type": "query",
                        "useTags": False,
                    },
                    {
                        "allValue": None,
                        "current": {
                            "selected": False,
                            "text": "All",
                            "value": "$__all",
                        },
                        "datasource": "${datasource}",
                        "definition": "label_values(agent_token_cost, model)",
                        "description": None,
                        "error": None,
                        "hide": 0,
                        "includeAll": True,
                        "label": "Model",
                        "multi": True,
                        "name": "model",
                        "options": [],
                        "query": {
                            "query": "label_values(agent_token_cost, model)",
                            "refId": "StandardVariableQuery",
                        },
                        "refresh": 1,
                        "regex": "",
                        "skipUrlSync": False,
                        "sort": 1,
                        "tagValuesQuery": "",
                        "tags": [],
                        "tagsQuery": "",
                        "type": "query",
                        "useTags": False,
                    },
                ]
            },
            "time": {
                "from": "now-6h",
                "to": "now",
            },
            "timepicker": {
                "refresh_intervals": [
                    "5s",
                    "10s",
                    "30s",
                    "1m",
                    "5m",
                    "15m",
                    "30m",
                    "1h",
                    "2h",
                    "1d",
                ]
            },
            "timezone": "browser",
            "title": self.dashboard_name,
            "uid": self.dashboard_uid,
            "version": 1,
            "weekStart": "monday",
            "refresh": self.refresh_interval,
        }
        return dashboard


def create_metrics_overview_dashboard() -> Dict[str, Any]:
    """Create the metrics overview dashboard."""
    gen = GrafanaDashboardGenerator("AI Agent Metrics Overview", "30s")

    gen.add_row("Agent Performance Overview")

    gen.add_stat_panel(
        "Total Requests
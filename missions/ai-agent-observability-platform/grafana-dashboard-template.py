#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Grafana dashboard template
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-28T22:02:37.453Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Grafana dashboard template
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2024

This module generates a complete Grafana dashboard template for AI agent observability,
including distributed tracing, token cost attribution, and anomaly detection visualizations.
"""

import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
import hashlib
import random
import string


class GrafanaDashboardGenerator:
    """Generates Grafana dashboard templates for AI agent observability."""

    def __init__(self, dashboard_name: str, refresh_interval: str = "30s"):
        """Initialize dashboard generator.
        
        Args:
            dashboard_name: Name of the dashboard
            refresh_interval: How often to refresh the dashboard
        """
        self.dashboard_name = dashboard_name
        self.refresh_interval = refresh_interval
        self.dashboard_uid = self._generate_uid()
        self.panels = []
        self.panel_id = 1
        self.row_index = 0

    def _generate_uid(self) -> str:
        """Generate unique identifier for dashboard."""
        hash_input = f"{self.dashboard_name}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]

    def _get_next_panel_id(self) -> int:
        """Get next available panel ID."""
        current_id = self.panel_id
        self.panel_id += 1
        return current_id

    def _get_grid_position(self, column: int, row: int, width: int = 12, height: int = 8) -> Dict[str, int]:
        """Generate grid position for panel."""
        return {
            "h": height,
            "w": width,
            "x": column,
            "y": row
        }

    def add_agent_performance_panel(self) -> None:
        """Add panel for agent performance metrics."""
        panel = {
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False
                        },
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "pointSize": 5,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "auto",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "red",
                                "value": 80
                            }
                        ]
                    },
                    "unit": "ms"
                },
                "overrides": []
            },
            "gridPos": self._get_grid_position(0, self.row_index, 12, 8),
            "id": self._get_next_panel_id(),
            "options": {
                "legend": {
                    "calcs": ["mean", "max"],
                    "displayMode": "table",
                    "placement": "bottom",
                    "showLegend": True
                },
                "tooltip": {
                    "mode": "multi",
                    "sort": "none"
                }
            },
            "pluginVersion": "9.5.3",
            "targets": [
                {
                    "expr": 'rate(agent_request_duration_seconds_sum[5m])',
                    "interval": "",
                    "legendFormat": "{{agent_id}} - avg latency",
                    "refId": "A"
                },
                {
                    "expr": 'rate(agent_request_duration_seconds_count[5m])',
                    "interval": "",
                    "legendFormat": "{{agent_id}} - throughput",
                    "refId": "B"
                }
            ],
            "title": "Agent Performance - Latency & Throughput",
            "type": "timeseries"
        }
        self.panels.append(panel)
        self.row_index += 8

    def add_token_cost_panel(self) -> None:
        """Add panel for token cost attribution."""
        panel = {
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {
                        "align": "auto",
                        "displayMode": "auto",
                        "inspect": False
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "yellow",
                                "value": 1000
                            },
                            {
                                "color": "red",
                                "value": 5000
                            }
                        ]
                    },
                    "unit": "short"
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Cost ($)"},
                        "properties": [
                            {
                                "id": "color",
                                "value": {"mode": "palette-classic"}
                            },
                            {
                                "id": "custom.displayMode",
                                "value": "color-background"
                            }
                        ]
                    }
                ]
            },
            "gridPos": self._get_grid_position(0, self.row_index, 12, 8),
            "id": self._get_next_panel_id(),
            "options": {
                "footer": {
                    "countRows": False,
                    "fields": "",
                    "reducer": ["sum"],
                    "show": True
                },
                "showHeader": True,
                "sortBy": [
                    {
                        "displayName": "Cost ($)",
                        "desc": True
                    }
                ]
            },
            "pluginVersion": "9.5.3",
            "targets": [
                {
                    "expr": 'sum by (agent_id) (increase(token_cost_total[1h]))',
                    "format": "table",
                    "instant": True,
                    "refId": "A"
                }
            ],
            "title": "Token Cost Attribution by Agent",
            "transformations": [
                {
                    "id": "organize",
                    "options": {
                        "excludeByName": {
                            "Time": True,
                            "__name__": True
                        },
                        "indexByName": {},
                        "renameByName": {
                            "Value": "Cost ($)",
                            "agent_id": "Agent ID"
                        }
                    }
                }
            ],
            "type": "table"
        }
        self.panels.append(panel)
        self.row_index += 8

    def add_anomaly_detection_panel(self) -> None:
        """Add panel for anomaly detection visualization."""
        panel = {
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 20,
                        "gradientMode": "opacity",
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False
                        },
                        "lineInterpolation": "smooth",
                        "lineWidth": 2,
                        "pointSize": 5,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "never",
                        "spanNulls": True,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "dashed"
                        }
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "orange",
                                "value": 2
                            },
                            {
                                "color": "red",
                                "value": 3
                            }
                        ]
                    },
                    "unit": "short"
                },
                "overrides": []
            },
            "gridPos": self._get_grid_position(0, self.row_index, 12, 8),
            "id": self._get_next_panel_id(),
            "options": {
                "legend": {
                    "calcs": ["mean", "max", "min"],
                    "displayMode": "table",
                    "placement": "right",
                    "showLegend": True
                },
                "tooltip": {
                    "mode": "multi",
                    "sort": "desc"
                }
            },
            "pluginVersion": "9.5.3",
            "targets": [
                {
                    "expr": 'agent_anomaly_score',
                    "interval": "",
                    "legendFormat": "{{agent_id}} - anomaly score",
                    "refId": "A"
                },
                {
                    "expr": 'agent_anomaly_threshold',
                    "interval": "",
                    "legendFormat": "Threshold",
                    "refId": "B"
                }
            ],
            "title": "Anomaly Detection Scores",
            "type": "timeseries"
        }
        self.panels.append(panel)
        self.row_index += 8

    def add_distributed_tracing_panel(self) -> None:
        """Add panel for distributed tracing visualization."""
        panel = {
            "datasource": {"type": "jaeger", "uid": "jaeger"},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "hideFrom": {
                            "tooltip": False,
                            "viz": False,
                            "legend": False
                        }
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            }
                        ]
                    },
                    "unit": "ms"
                },
                "overrides": []
            },
            "gridPos": self._get_grid_position(0, self.row_index, 12, 8),
            "id": self._get_next_panel_id(),
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": True
                }
            },
            "pluginVersion": "9.5.3",
            "targets": [
                {
                    "serviceName": "ai-agent-service",
                    "refId": "A"
                }
            ],
            "title": "Distributed Tracing - Request Flow",
            "type": "nodeGraph"
        }
        self.panels.append(panel)
        self.row_index += 8

    def add_error_rate_panel(self) -> None:
        """Add panel for error rate monitoring."""
        panel = {
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {
                        "align": "auto",
                        "displayMode": "color-background",
                        "inspect": False
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "percentage",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "yellow",
                                "value": 1
                            },
                            {
                                "color": "red",
                                "value": 5
                            }
                        ]
                    },
                    "unit": "percent"
                },
                "overrides": []
            },
            "gridPos": self._get_grid_position(0, self.row_index, 12, 8),
            "id": self._get_next_panel_id(),
            "options": {
                "footer": {
                    "countRows": False,
                    "fields": "",
                    "reducer": ["mean"],
                    "show": True
                },
                "showHeader": True
            },
            "pluginVersion": "9.5.3",
            "targets": [
                {
                    "expr": '(sum(rate(agent_errors_total[5m])) / sum(rate(agent_requests_total[5m]))) * 100',
                    "format": "table",
                    "instant": True,
                    "refId": "A"
                }
            ],
            "title": "Error Rate by Agent",
            "type": "stat"
        }
        self.panels.append(panel)
        self.row_index += 8

    def build_dashboard(self) -> Dict[str, Any]:
        """Build complete dashboard object."""
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
                        "type": "dashboard"
                    }
                ]
            },
            "editable": True,
            "fiscalYearStartMonth": 0,
            "graphTooltip": 1,
            "id": None,
            "links": [],
            "liveNow": False,
            "panels": self.panels,
            "refresh": self.refresh_interval,
            "schemaVersion": 37,
            "style": "dark",
            "tags": ["ai-agents", "observability", "performance"],
            "templating": {
                "list": [
                    {
                        "current": {
                            "selected": False,
                            "text": "Prometheus",
                            "value": "prometheus"
                        },
                        "description": None,
                        "error": None,
                        "hide":
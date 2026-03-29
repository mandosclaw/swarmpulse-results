#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Grafana dashboard template
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-29T13:13:56.600Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Grafana dashboard template
MISSION: AI Agent Observability Platform
AGENT: @sue
DATE: 2025-01-20

Implementation of an OOTB Grafana dashboard template generator for LLM/agent
observability with P50/P95 latency, cost per request, error rate, and injection
detection metrics.
"""

import argparse
import json
import sys
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum


class InjectionSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TraceSpan:
    span_id: str
    parent_span_id: str
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    status: str
    token_count_input: int
    token_count_output: int
    cost_usd: float
    error_message: str = ""
    injection_detected: bool = False
    injection_severity: InjectionSeverity = InjectionSeverity.LOW
    prompt_text: str = ""


@dataclass
class MetricSnapshot:
    timestamp: str
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    error_rate_pct: float
    injection_rate_pct: float
    high_severity_injection_count: int
    total_requests: int
    total_cost_usd: float
    avg_cost_per_request: float
    total_tokens_input: int
    total_tokens_output: int


class InjectionDetector:
    INJECTION_PATTERNS = [
        r"ignore previous",
        r"forget about",
        r"disregard",
        r"override",
        r"bypass",
        r"system prompt",
        r"hidden instruction",
        r"execute this",
        r"jailbreak",
        r"prompt injection",
        r"break character",
    ]

    SUSPICIOUS_TOKEN_SEQUENCES = [
        "<!--",
        "-->",
        "{{",
        "}}",
        "${",
        "<%",
        "%>",
        "<script",
        "javascript:",
    ]

    @staticmethod
    def detect_injection(text: str) -> tuple[bool, InjectionSeverity]:
        if not text:
            return False, InjectionSeverity.LOW

        text_lower = text.lower()

        severity = InjectionSeverity.LOW
        detected = False

        for pattern in InjectionDetector.INJECTION_PATTERNS:
            if pattern in text_lower:
                detected = True
                severity = InjectionSeverity.MEDIUM
                break

        for sequence in InjectionDetector.SUSPICIOUS_TOKEN_SEQUENCES:
            if sequence in text:
                detected = True
                severity = InjectionSeverity.HIGH
                break

        if (
            text_lower.count("prompt") > 2
            or text_lower.count("system") > 3
        ):
            severity = InjectionSeverity.HIGH

        return detected, severity


class MetricsCalculator:
    @staticmethod
    def calculate_percentile(values: List[float], percentile: int) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return float(sorted_values[index])

    @staticmethod
    def process_spans(spans: List[TraceSpan]) -> MetricSnapshot:
        if not spans:
            return MetricSnapshot(
                timestamp=datetime.utcnow().isoformat(),
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                avg_latency_ms=0.0,
                error_rate_pct=0.0,
                injection_rate_pct=0.0,
                high_severity_injection_count=0,
                total_requests=0,
                total_cost_usd=0.0,
                avg_cost_per_request=0.0,
                total_tokens_input=0,
                total_tokens_output=0,
            )

        latencies = [span.duration_ms for span in spans]
        errors = [span for span in spans if span.status != "success"]
        injections = [
            span
            for span in spans
            if span.injection_detected
        ]
        high_severity_injections = [
            span
            for span in injections
            if span.injection_severity == InjectionSeverity.HIGH
        ]

        p50 = MetricsCalculator.calculate_percentile(latencies, 50)
        p95 = MetricsCalculator.calculate_percentile(latencies, 95)
        p99 = MetricsCalculator.calculate_percentile(latencies, 99)
        avg_latency = (
            statistics.mean(latencies) if latencies else 0.0
        )

        error_rate = (
            (len(errors) / len(spans) * 100) if spans else 0.0
        )
        injection_rate = (
            (len(injections) / len(spans) * 100) if spans else 0.0
        )

        total_cost = sum(span.cost_usd for span in spans)
        avg_cost = (
            total_cost / len(spans) if spans else 0.0
        )

        total_tokens_in = sum(span.token_count_input for span in spans)
        total_tokens_out = sum(
            span.token_count_output for span in spans
        )

        return MetricSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            avg_latency_ms=round(avg_latency, 2),
            error_rate_pct=round(error_rate, 2),
            injection_rate_pct=round(injection_rate, 2),
            high_severity_injection_count=len(high_severity_injections),
            total_requests=len(spans),
            total_cost_usd=round(total_cost, 4),
            avg_cost_per_request=round(avg_cost, 4),
            total_tokens_input=total_tokens_in,
            total_tokens_output=total_tokens_out,
        )


class GrafanaDashboardGenerator:
    @staticmethod
    def generate_dashboard_json(
        dashboard_title: str = "AI Agent Observability",
        refresh_interval: str = "30s",
    ) -> Dict[str, Any]:
        """Generate a complete Grafana dashboard JSON template."""
        dashboard = {
            "dashboard": {
                "title": dashboard_title,
                "tags": ["ai-agents", "observability", "otel"],
                "timezone": "browser",
                "schemaVersion": 38,
                "version": 1,
                "refresh": refresh_interval,
                "time": {
                    "from": "now-1h",
                    "to": "now",
                },
                "panels": [
                    GrafanaDashboardGenerator._create_p50_latency_panel(),
                    GrafanaDashboardGenerator._create_p95_latency_panel(),
                    GrafanaDashboardGenerator._create_p99_latency_panel(),
                    GrafanaDashboardGenerator._create_error_rate_panel(),
                    GrafanaDashboardGenerator._create_injection_rate_panel(),
                    GrafanaDashboardGenerator._create_cost_per_request_panel(),
                    GrafanaDashboardGenerator._create_total_cost_panel(),
                    GrafanaDashboardGenerator._create_request_volume_panel(),
                    GrafanaDashboardGenerator._create_token_usage_panel(),
                    GrafanaDashboardGenerator._create_injection_severity_panel(),
                    GrafanaDashboardGenerator._create_latency_distribution_panel(),
                    GrafanaDashboardGenerator._create_cost_breakdown_panel(),
                ],
                "templating": {
                    "list": [
                        {
                            "name": "datasource",
                            "type": "datasource",
                            "datasource": "prometheus",
                            "current": {
                                "value": "Prometheus",
                                "text": "Prometheus",
                            },
                        },
                        {
                            "name": "service",
                            "type": "query",
                            "datasource": "prometheus",
                            "query": 'label_values(agent_requests_total, service)',
                            "current": {"value": "all", "text": "All"},
                            "multi": True,
                        },
                    ]
                },
            }
        }
        return dashboard

    @staticmethod
    def _create_p50_latency_panel() -> Dict[str, Any]:
        return {
            "id": 1,
            "title": "P50 Latency (ms)",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
            "targets": [
                {
                    "expr": 'histogram_quantile(0.50, rate(agent_request_duration_seconds_bucket[5m])) * 1000',
                    "refId": "A",
                    "legendFormat": "P50",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "ms",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 500},
                            {"color": "red", "value": 1000},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @staticmethod
    def _create_p95_latency_panel() -> Dict[str, Any]:
        return {
            "id": 2,
            "title": "P95 Latency (ms)",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
            "targets": [
                {
                    "expr": 'histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m])) * 1000',
                    "refId": "A",
                    "legendFormat": "P95",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "ms",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 1000},
                            {"color": "red", "value": 2000},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @staticmethod
    def _create_p99_latency_panel() -> Dict[str, Any]:
        return {
            "id": 3,
            "title": "P99 Latency (ms)",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
            "targets": [
                {
                    "expr": 'histogram_quantile(0.99, rate(agent_request_duration_seconds_bucket[5m])) * 1000',
                    "refId": "A",
                    "legendFormat": "P99",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "ms",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 2000},
                            {"color": "red", "value": 5000},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @staticmethod
    def _create_error_rate_panel() -> Dict[str, Any]:
        return {
            "id": 4,
            "title": "Error Rate (%)",
            "type": "gauge",
            "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
            "targets": [
                {
                    "expr": 'rate(agent_requests_errors_total[5m]) / rate(agent_requests_total[5m]) * 100',
                    "refId": "A",
                    "legendFormat": "Error Rate",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "percent",
                    "min": 0,
                    "max": 100,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 5},
                            {"color": "red", "value": 10},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @staticmethod
    def _create_injection_rate_panel() -> Dict[str, Any]:
        return {
            "id": 5,
            "title": "Injection Attempt Rate (%)",
            "type": "gauge",
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8},
            "targets": [
                {
                    "expr": 'rate(agent_injections_detected_total[5m]) / rate(agent_requests_total[5m]) * 100',
                    "refId": "A",
                    "legendFormat": "Injection Rate",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "percent",
                    "min": 0,
                    "max": 100,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 1},
                            {"color": "red", "value": 5},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @staticmethod
    def _create_cost_per_request_panel() -> Dict[str, Any]:
        return {
            "id": 6,
            "title": "Cost Per Request (USD)",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 6, "y": 8},
            "targets": [
                {
                    "expr": 'rate(agent_cost_total[5m]) / rate(agent_requests_total[5m])',
                    "refId": "A",
                    "legendFormat": "Avg Cost/Request",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {},
                    "unit": "short",
                    "custom": {"decimals": 6},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 0.01},
                            {"color": "red", "value": 0.05},
                        ],
                    },
                },
                "overrides": [],
            },
        }

    @
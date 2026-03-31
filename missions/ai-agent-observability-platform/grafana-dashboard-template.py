#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Grafana dashboard template
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-31T18:42:57.962Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Grafana dashboard template for AI Agent Observability Platform
Mission: OpenTelemetry-native observability for LLM/agent workloads
Agent: @sue
Date: 2024
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
import random
import statistics


class ObservabilityMetrics:
    """Collector and analyzer for agent observability metrics."""
    
    def __init__(self):
        self.traces: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "latencies": [],
            "costs": [],
            "errors": [],
            "injection_attempts": [],
            "timestamps": []
        }
    
    def add_trace(self, span_id: str, operation: str, duration_ms: float,
                  token_count: int, cost_usd: float, error: bool = False,
                  injection_detected: bool = False, metadata: Dict = None) -> None:
        """Add a trace span to the collection."""
        trace = {
            "span_id": span_id,
            "operation": operation,
            "duration_ms": duration_ms,
            "token_count": token_count,
            "cost_usd": cost_usd,
            "error": error,
            "injection_detected": injection_detected,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.traces.append(trace)
        self.metrics["latencies"].append(duration_ms)
        self.metrics["costs"].append(cost_usd)
        if error:
            self.metrics["errors"].append(trace)
        if injection_detected:
            self.metrics["injection_attempts"].append(trace)
        self.metrics["timestamps"].append(datetime.utcnow())
    
    def calculate_latency_percentiles(self) -> Dict[str, float]:
        """Calculate P50 and P95 latency percentiles."""
        if not self.metrics["latencies"]:
            return {"p50": 0.0, "p95": 0.0}
        
        sorted_latencies = sorted(self.metrics["latencies"])
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        
        return {
            "p50": float(sorted_latencies[p50_idx]) if p50_idx < len(sorted_latencies) else 0.0,
            "p95": float(sorted_latencies[p95_idx]) if p95_idx < len(sorted_latencies) else 0.0,
            "mean": statistics.mean(sorted_latencies) if sorted_latencies else 0.0,
            "min": float(min(sorted_latencies)) if sorted_latencies else 0.0,
            "max": float(max(sorted_latencies)) if sorted_latencies else 0.0
        }
    
    def calculate_cost_metrics(self) -> Dict[str, float]:
        """Calculate cost metrics."""
        if not self.metrics["costs"]:
            return {"total": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "total": sum(self.metrics["costs"]),
            "mean": statistics.mean(self.metrics["costs"]),
            "min": min(self.metrics["costs"]),
            "max": max(self.metrics["costs"]),
            "per_request": sum(self.metrics["costs"]) / len(self.metrics["costs"])
        }
    
    def calculate_error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if not self.traces:
            return 0.0
        error_count = len(self.metrics["errors"])
        return (error_count / len(self.traces)) * 100.0
    
    def calculate_injection_rate(self) -> float:
        """Calculate injection detection rate as percentage."""
        if not self.traces:
            return 0.0
        injection_count = len(self.metrics["injection_attempts"])
        return (injection_count / len(self.traces)) * 100.0
    
    def detect_injection_patterns(self, text: str) -> bool:
        """Detect common prompt injection patterns."""
        injection_patterns = [
            "ignore previous",
            "forget instructions",
            "bypass",
            "override",
            "disregard",
            "system prompt",
            "jailbreak",
            "hidden instructions",
            "secret mode",
            "admin mode",
            "unauthorized access",
            "execute code",
            "run command"
        ]
        
        text_lower = text.lower()
        for pattern in injection_patterns:
            if pattern in text_lower:
                return True
        return False
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Generate complete dashboard data."""
        latency_percentiles = self.calculate_latency_percentiles()
        cost_metrics = self.calculate_cost_metrics()
        error_rate = self.calculate_error_rate()
        injection_rate = self.calculate_injection_rate()
        
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_requests": len(self.traces),
                "total_traces": len(self.traces),
                "time_window": self._get_time_window()
            },
            "latency": {
                "p50_ms": latency_percentiles["p50"],
                "p95_ms": latency_percentiles["p95"],
                "mean_ms": latency_percentiles["mean"],
                "min_ms": latency_percentiles["min"],
                "max_ms": latency_percentiles["max"]
            },
            "cost": {
                "total_usd": cost_metrics["total"],
                "mean_per_request": cost_metrics["per_request"],
                "min_usd": cost_metrics["min"],
                "max_usd": cost_metrics["max"],
                "mean_usd": cost_metrics["mean"]
            },
            "errors": {
                "error_rate_percent": error_rate,
                "total_errors": len(self.metrics["errors"]),
                "error_details": self.metrics["errors"][-5:] if self.metrics["errors"] else []
            },
            "security": {
                "injection_rate_percent": injection_rate,
                "total_injections_detected": len(self.metrics["injection_attempts"]),
                "injection_details": self.metrics["injection_attempts"][-5:] if self.metrics["injection_attempts"] else []
            },
            "operations": self._get_operations_breakdown()
        }
        
        return dashboard
    
    def _get_time_window(self) -> str:
        """Get the time window of collected metrics."""
        if not self.metrics["timestamps"]:
            return "0s"
        
        if len(self.metrics["timestamps"]) == 1:
            return "0s"
        
        time_diff = self.metrics["timestamps"][-1] - self.metrics["timestamps"][0]
        seconds = time_diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        else:
            return f"{int(seconds / 3600)}h"
    
    def _get_operations_breakdown(self) -> Dict[str, Any]:
        """Get breakdown by operation type."""
        operations = {}
        for trace in self.traces:
            op = trace["operation"]
            if op not in operations:
                operations[op] = {
                    "count": 0,
                    "latencies": [],
                    "costs": []
                }
            operations[op]["count"] += 1
            operations[op]["latencies"].append(trace["duration_ms"])
            operations[op]["costs"].append(trace["cost_usd"])
        
        for op_name, op_data in operations.items():
            operations[op_name] = {
                "count": op_data["count"],
                "mean_latency_ms": statistics.mean(op_data["latencies"]) if op_data["latencies"] else 0.0,
                "total_cost_usd": sum(op_data["costs"])
            }
        
        return operations


class GrafanaDashboardTemplate:
    """Generate Grafana dashboard JSON template."""
    
    @staticmethod
    def generate_dashboard_json(title: str = "AI Agent Observability") -> str:
        """Generate complete Grafana dashboard JSON template."""
        dashboard = {
            "dashboard": {
                "id": None,
                "uid": "ai-agent-observability",
                "title": title,
                "tags": ["agent", "observability", "otel", "apm"],
                "timezone": "browser",
                "schemaVersion": 38,
                "version": 0,
                "refresh": "30s",
                "time": {
                    "from": "now-6h",
                    "to": "now"
                },
                "panels": [
                    GrafanaDashboardTemplate._create_p50_latency_panel(),
                    GrafanaDashboardTemplate._create_p95_latency_panel(),
                    GrafanaDashboardTemplate._create_cost_per_request_panel(),
                    GrafanaDashboardTemplate._create_error_rate_panel(),
                    GrafanaDashboardTemplate._create_injection_rate_panel(),
                    GrafanaDashboardTemplate._create_latency_distribution_panel(),
                    GrafanaDashboardTemplate._create_cost_trend_panel(),
                    GrafanaDashboardTemplate._create_error_details_panel()
                ],
                "templating": {
                    "list": [
                        {
                            "name": "datasource",
                            "type": "datasource",
                            "datasource": "prometheus",
                            "current": {"value": "prometheus", "text": "Prometheus"}
                        }
                    ]
                }
            },
            "overwrite": True
        }
        return json.dumps(dashboard, indent=2)
    
    @staticmethod
    def _create_p50_latency_panel() -> Dict[str, Any]:
        """Create P50 latency gauge panel."""
        return {
            "id": 1,
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
            "type": "gauge",
            "title": "P50 Latency (ms)",
            "targets": [
                {
                    "expr": "histogram_quantile(0.50, rate(agent_span_duration_seconds_bucket[5m]))",
                    "legendFormat": "P50"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "min": 0,
                    "max": 5000,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 1000},
                            {"color": "red", "value": 3000}
                        ]
                    },
                    "unit": "ms"
                }
            }
        }
    
    @staticmethod
    def _create_p95_latency_panel() -> Dict[str, Any]:
        """Create P95 latency gauge panel."""
        return {
            "id": 2,
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
            "type": "gauge",
            "title": "P95 Latency (ms)",
            "targets": [
                {
                    "expr": "histogram_quantile(0.95, rate(agent_span_duration_seconds_bucket[5m]))",
                    "legendFormat": "P95"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "min": 0,
                    "max": 10000,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 2000},
                            {"color": "red", "value": 5000}
                        ]
                    },
                    "unit": "ms"
                }
            }
        }
    
    @staticmethod
    def _create_cost_per_request_panel() -> Dict[str, Any]:
        """Create cost per request panel."""
        return {
            "id": 3,
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
            "type": "stat",
            "title": "Cost Per Request",
            "targets": [
                {
                    "expr": "rate(agent_token_cost_usd_total[5m])",
                    "legendFormat": "Cost/s"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "currencyUSD",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 0.01},
                            {"color": "red", "value": 0.05}
                        ]
                    }
                }
            }
        }
    
    @staticmethod
    def _create_error_rate_panel() -> Dict[str, Any]:
        """Create error rate panel."""
        return {
            "id": 4,
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
            "type": "gauge",
            "title": "Error Rate (%)",
            "targets": [
                {
                    "expr": "100 * (sum(rate(agent_span_errors_total[5m])) / sum(rate(agent_spans_total[5m])))",
                    "legendFormat": "Error %"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "min": 0,
                    "max": 100,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 1},
                            {"color": "red", "value": 5}
                        ]
                    },
                    "unit": "percent"
                }
            }
        }
    
    @staticmethod
    def _create_injection_rate_panel() -> Dict[str, Any]:
        """Create injection detection rate panel."""
        return {
            "id": 5,
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
            "type": "gauge",
            "title": "Injection Detection Rate (%)",
            "targets": [
                {
                    "expr": "100 * (sum(rate(agent_injection_attempts_total[5m])) / sum(rate(agent_spans_total[5m])))",
                    "legendFormat": "Injection %"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "min": 0,
                    "max": 10,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 0.1},
                            {"color": "red", "value": 1}
                        ]
                    },
                    "unit": "percent"
                }
            }
        }
    
    @staticmethod
    def _create_latency_distribution_panel() -> Dict[str, Any]:
        """Create latency distribution histogram panel."""
        return {
            "id": 6,
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
            "type": "histogram",
            "title": "Latency Distribution",
            "targets": [
                {
                    "expr": "rate(agent_span_duration_seconds_bucket[5m])",
                    "legendFormat": "{{le}}"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "ms"
                }
            }
        }
    
    @staticmethod
    def _create_cost_trend_panel() -> Dict[str, Any]:
        """Create cost trend over time panel."""
        return {
            "id": 7,
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24},
            "type": "timeseries",
            "title": "Cost Trend (5m rate)",
            "targets": [
                {
                    "expr": "rate(agent_token_cost_usd_total[5m])",
                    "legendFormat": "Cost/s"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "currencyUSD",
                    "custom": {
                        "fillOpacity": 10,
                        "showPoints": "never"
                    }
                }
            }
        }
    
    @staticmethod
    def _create_error_details_panel() -> Dict[str, Any]:
        """Create error details table panel."""
        return {
            "id": 8,
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
            "type": "table",
            "title": "Recent Errors",
            "targets": [
                {
                    "expr": "topk(10, agent_span_errors_total)",
                    "format": "table",
                    "instant": True
                }
            ]
        }


class MetricsSimulator:
    """Simulate realistic agent workload metrics."""
    
    @staticmethod
    def generate_realistic_trace(trace_id: int) -> Dict[str, Any]:
        """Generate a realistic trace with multiple spans."""
        operations = ["llm_call", "tool_execution", "embedding", "vector_search", "parsing"]
        has_error = random.random() < 0.05
        has_injection = random.random() < 0.02
        
        operation = random.choice(operations)
        
        if operation == "llm_call":
            duration = random.gauss(800, 200)
            tokens = random.randint(100, 2000)
            cost = tokens * 0.000001
        elif operation == "tool_execution":
            duration = random.gauss(500, 150)
            tokens = random.randint(50, 500)
            cost = 0.0001
        elif operation == "embedding":
            duration = random.gauss(200, 50)
            tokens = random.randint(10, 100)
            cost = tokens * 0.0000002
        elif operation == "vector_search":
            duration = random.gauss(100, 30)
            tokens = 0
            cost = 0.00005
        else:
            duration = random.gauss(50, 20)
            tokens = random.randint(5, 50)
            cost = 0.00001
        
        duration = max(10, duration)
        
        return {
            "span_id": f"span-{trace_id}",
            "operation": operation,
            "duration_ms": duration,
            "token_count": tokens,
            "cost_usd": cost,
            "error": has_error,
            "injection_detected": has_injection
        }


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Observability Platform - Grafana Dashboard Generator"
    )
    parser.add_argument(
        "--num-traces",
        type=int,
        default=100,
        help="Number of trace spans to simulate (default: 100)"
    )
    parser.add_argument(
        "--output-dashboard",
        type=str,
        default="dashboard.json",
        help="Output file for Grafana dashboard JSON template (default: dashboard.json)"
    )
    parser.add_argument(
        "--output-metrics",
        type=str,
        default="metrics.json",
        help="Output file for computed metrics (default: metrics.json)"
    )
    parser.add_argument(
        "--show-summary",
        action="store_true",
        help="Print metrics summary to stdout"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"[INFO] Generating {args.num_traces} simulated traces...", file=sys.stderr)
    
    metrics = ObservabilityMetrics()
    
    for i in range(args.num_traces):
        trace_data = MetricsSimulator.generate_realistic_trace(i)
        metrics.add_trace(
            span_id=trace_data["span_id"],
            operation=trace_data["operation"],
            duration_ms=trace_data["duration_ms"],
            token_count=trace_data["token_count"],
            cost_usd=trace_data["cost_usd"],
            error=trace_data["error"],
            injection_detected=trace_data["injection_detected"]
        )
    
    dashboard_data = metrics.get_dashboard_data()
    
    if args.show_summary:
        print("\n=== AI AGENT OBSERVABILITY DASHBOARD ===")
        print(f"Total Requests: {dashboard_data['summary']['total_requests']}")
        print(f"Time Window: {dashboard_data['summary']['time_window']}")
        print("\n--- LATENCY ---")
        print(f"P50: {dashboard_data['latency']['p50_ms']:.2f}ms")
        print(f"P95: {dashboard_data['latency']['p95_ms']:.2f}ms")
        print(f"Mean: {dashboard_data['latency']['mean_ms']:.2f}ms")
        print("\n--- COST ---")
        print(f"Total: ${dashboard_data['cost']['total_usd']:.4f}")
        print(f"Per Request: ${dashboard_data['cost']['mean_per_request']:.6f}")
        print("\n--- ERRORS ---")
        print(f"Error Rate: {dashboard_data['errors']['error_rate_percent']:.2f}%")
        print(f"Total Errors: {dashboard_data['errors']['total_errors']}")
        print("\n--- SECURITY ---")
        print(f"Injection Detection Rate: {dashboard_data['security']['injection_rate_percent']:.2f}%")
        print(f"Total Injections Detected: {dashboard_data['security']['total_injections_detected']}")
        print("\n--- OPERATIONS ---")
        for op_name, op_stats in dashboard_data['operations'].items():
            print(f"{op_name}: {op_stats['count']} calls, "
                  f"{op_stats['mean_latency_ms']:.2f}ms mean, "
                  f"${op_stats['total_cost_usd']:.6f} total")
    
    if args.output_metrics:
        with open(args.output_metrics, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        if args.verbose:
            print(f"[INFO] Metrics written to {args.output_metrics}", file=sys.stderr)
    
    dashboard_json = GrafanaDashboardTemplate.generate_dashboard_json()
    
    if args.output_dashboard:
        with open(args.output_dashboard, 'w') as f:
            f.write(dashboard_json)
        if args.verbose:
            print(f"[INFO] Dashboard template written to {args.output_dashboard}", file=sys.stderr)
    
    if args.verbose:
        print(f"[INFO] Complete. Metrics and dashboard template generated.", file=sys.stderr)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Agent health heartbeat monitor
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-28T22:02:50.636Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Agent Health Heartbeat Monitor
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2024

Monitors health status of distributed AI agents in SwarmPulse network.
Tracks heartbeats, latency, error rates, and resource utilization.
Generates alerts when agents fall below health thresholds.
"""

import argparse
import json
import time
import threading
import random
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from collections import defaultdict, deque


@dataclass
class HeartbeatMetrics:
    """Container for agent heartbeat metrics"""
    agent_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    latency_ms: float
    error_count: int
    success_count: int
    token_cost: float
    status: str


@dataclass
class HealthAlert:
    """Container for health alerts"""
    alert_id: str
    agent_id: str
    alert_type: str
    severity: str
    message: str
    timestamp: float
    metric_value: float
    threshold: float


class AgentHealthMonitor:
    """Monitors health metrics of distributed AI agents"""

    def __init__(self, heartbeat_timeout_sec: int, cpu_threshold: float,
                 memory_threshold: float, latency_threshold_ms: float,
                 error_rate_threshold: float, check_interval_sec: int):
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.check_interval_sec = check_interval_sec

        self.agent_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.alerts: List[HealthAlert] = []
        self.agent_status: Dict[str, str] = {}
        self.running = False
        self.lock = threading.RLock()

    def record_heartbeat(self, metrics: HeartbeatMetrics) -> None:
        """Record a heartbeat from an agent"""
        with self.lock:
            self.agent_metrics[metrics.agent_id].append(metrics)
            self.agent_status[metrics.agent_id] = "healthy"

    def check_agent_health(self, agent_id: str) -> Dict:
        """Analyze health metrics for a specific agent"""
        with self.lock:
            if agent_id not in self.agent_metrics:
                return {
                    "agent_id": agent_id,
                    "status": "unknown",
                    "message": "No heartbeat data",
                    "last_seen": None,
                    "metrics": {}
                }

            metrics_list = list(self.agent_metrics[agent_id])
            if not metrics_list:
                return {
                    "agent_id": agent_id,
                    "status": "unknown",
                    "message": "Empty metrics history",
                    "last_seen": None,
                    "metrics": {}
                }

            last_metric = metrics_list[-1]
            current_time = time.time()
            time_since_heartbeat = current_time - last_metric.timestamp

            health_status = "healthy"
            issues = []

            if time_since_heartbeat > self.heartbeat_timeout_sec:
                health_status = "offline"
                issues.append(
                    f"No heartbeat for {time_since_heartbeat:.1f}s "
                    f"(timeout: {self.heartbeat_timeout_sec}s)"
                )
                self.agent_status[agent_id] = "offline"
            else:
                cpu_avg = statistics.mean(m.cpu_usage for m in metrics_list)
                if cpu_avg > self.cpu_threshold:
                    health_status = "degraded"
                    issues.append(
                        f"High CPU usage: {cpu_avg:.1f}% "
                        f"(threshold: {self.cpu_threshold}%)"
                    )

                mem_avg = statistics.mean(m.memory_usage for m in metrics_list)
                if mem_avg > self.memory_threshold:
                    health_status = "degraded"
                    issues.append(
                        f"High memory usage: {mem_avg:.1f}% "
                        f"(threshold: {self.memory_threshold}%)"
                    )

                lat_avg = statistics.mean(m.latency_ms for m in metrics_list)
                if lat_avg > self.latency_threshold_ms:
                    health_status = "degraded"
                    issues.append(
                        f"High latency: {lat_avg:.1f}ms "
                        f"(threshold: {self.latency_threshold_ms}ms)"
                    )

                total_requests = sum(
                    m.success_count + m.error_count for m in metrics_list
                )
                total_errors = sum(m.error_count for m in metrics_list)
                error_rate = (
                    (total_errors / total_requests * 100)
                    if total_requests > 0 else 0
                )

                if error_rate > self.error_rate_threshold:
                    health_status = "degraded"
                    issues.append(
                        f"High error rate: {error_rate:.2f}% "
                        f"(threshold: {self.error_rate_threshold}%)"
                    )

                if health_status != "healthy":
                    self.agent_status[agent_id] = health_status

            return {
                "agent_id": agent_id,
                "status": health_status,
                "message": (
                    ", ".join(issues) if issues else "All metrics normal"
                ),
                "last_seen": last_metric.timestamp,
                "time_since_heartbeat_sec": time_since_heartbeat,
                "metrics": {
                    "cpu_avg": (
                        statistics.mean(
                            m.cpu_usage for m in metrics_list
                        )
                    ),
                    "memory_avg": (
                        statistics.mean(
                            m.memory_usage for m in metrics_list
                        )
                    ),
                    "latency_avg_ms": (
                        statistics.mean(
                            m.latency_ms for m in metrics_list
                        )
                    ),
                    "error_rate_percent": error_rate,
                    "total_requests": total_requests,
                    "token_cost_total": sum(m.token_cost for m in metrics_list),
                }
            }

    def generate_alert(
        self,
        agent_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metric_value: float,
        threshold: float
    ) -> HealthAlert:
        """Generate a health alert"""
        alert_id = f"{agent_id}_{int(time.time() * 1000)}"
        alert = HealthAlert(
            alert_id=alert_id,
            agent_id=agent_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=time.time(),
            metric_value=metric_value,
            threshold=threshold
        )

        with self.lock:
            self.alerts.append(alert)

        return alert

    def check_all_agents(self) -> List[Dict]:
        """Check health of all monitored agents"""
        with self.lock:
            agent_ids = list(self.agent_metrics.keys())

        results = []
        for agent_id in agent_ids:
            health = self.check_agent_health(agent_id)
            results.append(health)

        return results

    def get_alerts(self, limit: Optional
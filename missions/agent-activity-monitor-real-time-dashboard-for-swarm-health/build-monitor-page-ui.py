#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build monitor page UI
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T22:01:53.883Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build monitor page UI
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2024

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire swarm.
"""

import argparse
import json
import random
import time
from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
import sys


class AgentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class AgentMetrics:
    agent_id: str
    status: str
    uptime_seconds: int
    tasks_completed: int
    tasks_failed: int
    tasks_pending: int
    avg_response_time_ms: float
    error_rate_percent: float
    cpu_usage_percent: float
    memory_usage_percent: float
    last_heartbeat: str
    throughput_tasks_per_min: float


@dataclass
class SwarmMetrics:
    timestamp: str
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    critical_agents: int
    offline_agents: int
    total_tasks_completed: int
    total_tasks_failed: int
    total_tasks_pending: int
    avg_error_rate_percent: float
    avg_response_time_ms: float
    avg_cpu_usage_percent: float
    avg_memory_usage_percent: float
    overall_throughput_tasks_per_min: float
    agents: list = field(default_factory=list)


class MetricsCollector:
    def __init__(self, num_agents: int = 5):
        self.num_agents = num_agents
        self.agents = {f"agent_{i:03d}": self._generate_agent_state() for i in range(num_agents)}
        self.lock = threading.Lock()

    def _generate_agent_state(self) -> dict:
        return {
            "uptime_seconds": random.randint(3600, 86400),
            "tasks_completed": random.randint(100, 5000),
            "tasks_failed": random.randint(0, 50),
            "tasks_pending": random.randint(0, 100),
            "avg_response_time_ms": round(random.uniform(10, 500), 2),
            "cpu_usage_percent": round(random.uniform(5, 95), 1),
            "memory_usage_percent": round(random.uniform(10, 90), 1),
        }

    def _calculate_status(self, agent_id: str, state: dict) -> str:
        error_rate = (
            state["tasks_failed"] / max(state["tasks_completed"] + state["tasks_failed"], 1) * 100
        )
        cpu = state["cpu_usage_percent"]
        memory = state["memory_usage_percent"]

        if cpu > 90 or memory > 85 or error_rate > 20:
            return AgentStatus.CRITICAL.value
        elif cpu > 75 or memory > 70 or error_rate > 10:
            return AgentStatus.DEGRADED.value
        elif random.random() > 0.95:
            return AgentStatus.OFFLINE.value
        return AgentStatus.HEALTHY.value

    def _calculate_error_rate(self, state: dict) -> float:
        total = state["tasks_completed"] + state["tasks_failed"]
        if total == 0:
            return 0.0
        return round((state["tasks_failed"] / total) * 100, 2)

    def _calculate_throughput(self, state: dict, interval_minutes: int = 1) -> float:
        # Estimate throughput as completed tasks / uptime in minutes
        uptime_minutes = max(state["uptime_seconds"] / 60, 1)
        return round(state["tasks_completed"] / uptime_minutes, 2)

    def collect_metrics(self) -> SwarmMetrics:
        with self.lock:
            # Update agent states with small random changes
            for agent_id in self.agents:
                state = self.agents[agent_id]
                state["tasks_completed"] += random.randint(0, 20)
                state["tasks_failed"] += random.randint(0, 3)
                state["tasks_pending"] = max(0, state["tasks_pending"] + random.randint(-5, 10))
                state["cpu_usage_percent"] = round(
                    max(0, min(100, state["cpu_usage_percent"] + random.uniform(-10, 10))), 1
                )
                state["memory_usage_percent"] = round(
                    max(0, min(100, state["memory_usage_percent"] + random.uniform(-5, 5))), 1
                )
                state["avg_response_time_ms"] = round(
                    max(1, state["avg_response_time_ms"] + random.uniform(-50, 50)), 2
                )

            agent_metrics_list = []
            healthy_count = 0
            degraded_count = 0
            critical_count = 0
            offline_count = 0

            for agent_id, state in self.agents.items():
                status = self._calculate_status(agent_id, state)
                error_rate = self._calculate_error_rate(state)
                throughput = self._calculate_throughput(state)

                if status == AgentStatus.HEALTHY.value:
                    healthy_count += 1
                elif status == AgentStatus.DEGRADED.value:
                    degraded_count += 1
                elif status == AgentStatus.CRITICAL.value:
                    critical_count += 1
                else:
                    offline_count += 1

                metrics = AgentMetrics(
                    agent_id=agent_id,
                    status=status,
                    uptime_seconds=state["uptime_seconds"],
                    tasks_completed=state["tasks_completed"],
                    tasks_failed=state["tasks_failed"],
                    tasks_pending=state["tasks_pending"],
                    avg_response_time_ms=state["avg_response_time_ms"],
                    error_rate_percent=error_rate,
                    cpu_usage_percent=state["cpu_usage_percent"],
                    memory_usage_percent=state["memory_usage_percent"],
                    last_heartbeat=datetime.utcnow().isoformat() + "Z",
                    throughput_tasks_per_min=throughput,
                )
                agent_metrics_list.append(metrics)

            # Calculate swarm-level metrics
            total_completed = sum(m.tasks_completed for m in agent_metrics_list)
            total_failed = sum(m.tasks_failed for m in agent_metrics_list)
            total_pending = sum(m.tasks_pending for m in agent_metrics_list)
            avg_error_rate = (
                sum(m.error_rate_percent for m in agent_metrics_list) / len(agent_metrics_list)
            )
            avg_response_time = (
                sum(m.avg_response_time_ms for m in agent_metrics_list) / len(agent_metrics_list)
            )
            avg_cpu = sum(m.cpu_usage_percent for m in agent_metrics_list) / len(agent_metrics_list)
            avg_memory = (
                sum(m.memory_usage_percent for m in agent_metrics_list) / len(agent_metrics_list)
            )
            overall_throughput = sum(m.throughput_tasks_per_min for m in agent_metrics_list)

            swarm_metrics = SwarmMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                total_agents=len(agent_metrics_list),
                healthy_agents=healthy_count,
                degraded_agents=degraded_count,
                critical_agents=critical_count,
                offline_agents=offline_count,
                total_tasks_completed=total_completed,
                total_tasks_failed=total_failed,
                total_tasks_pending=total_pending,
                avg_error_rate_percent=round(avg_error_rate, 2),
                avg_response_time_ms=round(avg_response_time, 2),
                avg_cpu_usage_percent=round(avg_cpu, 1),
                avg_memory_usage_percent=round(avg_memory, 1),
                overall_throughput_tasks_per_min=round(overall_throughput, 2),
                agents=agent_metrics_list,
            )

            return swarm_metrics


class MonitorPageUI:
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.running = False

    def _format_uptime(self, seconds: int) -> str:
        """Format seconds into human-readable uptime string."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    def _get_status_color(self, status: str) -> str:
        """Return color code for status."""
        colors = {
            AgentStatus.HEALTHY.value: "🟢",
            AgentStatus.DEGRADED.value: "🟡",
            AgentStatus.CRITICAL.value: "🔴",
            AgentStatus.OFFLINE.value: "⚫",
        }
        return colors.get(status, "❓")

    def _render_header(self) -> str:
        """Render the dashboard header."""
        return "\n" + "=" * 120 + "\n" + "AGENT ACTIVITY MONITOR - REAL-TIME SWARM HEALTH DASHBOARD".center(120) + "\n" + "=" * 120 + "\n"

    def _render_swarm_summary(self, metrics: SwarmMetrics) -> str:
        """Render swarm-level summary statistics."""
        lines = []
        lines.append("┌" + "─" * 118 + "┐")
        lines.append("│" + f"SWARM SUMMARY (Updated: {metrics.timestamp})".ljust(118) + "│")
        lines.append("├" + "─" * 118 + "┤")

        summary_line = f"│ Total Agents: {metrics.total_agents} | Healthy: {metrics.healthy_agents} 🟢 | Degraded: {metrics.degraded_agents} 🟡 | Critical: {metrics.critical_agents} 🔴 | Offline: {metrics.offline_agents} ⚫"
        lines.append(summary_line.ljust(119) + "│")

        summary_line2 = f"│ Total Tasks: {metrics.total_tasks_completed} ✓ | Failed: {metrics.total_tasks_failed} ✗ | Pending: {metrics.total_tasks_pending} ⧗ | Avg Error Rate: {metrics.avg_error_rate_percent}%"
        lines.append(summary_line2.ljust(119) + "│")

        summary_line3 = f"│ Avg Response Time: {metrics.avg_response_time_ms}ms | Avg CPU: {metrics.avg_cpu_usage_percent}% | Avg Memory: {metrics.avg_memory_usage_percent}% | Throughput: {metrics.overall_throughput_tasks_per_min} tasks/min"
        lines.append(summary_line3.ljust(119) + "│")

        lines.append("└" + "─" * 118 + "┘")
        return "\n".join(lines)

    def _render_agent_table(self, metrics: SwarmMetrics) -> str:
        """Render detailed agent metrics table."""
        lines = []
        lines.append("┌" + "─" * 118 + "┐")
        lines.append("│" + "DETAILED AGENT METRICS".ljust(118) + "│")
        lines.append("├" + "─" * 118 + "┤")

        # Header row
        header = "│ Status │ Agent ID    │ Uptime      │ Tasks OK │ Tasks Fail │ Tasks Pend │ Response │ Error % │ CPU  % │ Mem  % │ Throughput │"
        lines.append(header)
        lines.append("├" + "─" * 118 + "┤")

        # Agent rows
        for agent in metrics.agents:
            status_icon = self._get_status_color(agent.status)
            uptime_str = self._format_uptime(agent.uptime_seconds)
            row = f"│ {status_icon}      │ {agent.agent_id} │ {uptime_str:11} │ {agent.tasks_completed:8} │ {agent.tasks_failed:10} │ {agent.tasks_pending:10} │ {agent.avg_response_time_ms:7.1f}ms │ {agent.error_rate_percent:6.2f}% │ {agent.cpu_usage_percent:5.1f}% │ {agent.memory_usage_percent:5.1f}% │ {agent.throughput_tasks_per_min:9.2f}    │"
            lines.append(row)

        lines.append("└" + "─" * 118 + "┘")
        return "\n".join(lines)

    def render_dashboard(self, metrics: SwarmMetrics) -> str:
        """Render the complete dashboard."""
        output = []
        output.append(self._render_header())
        output.append(self._render_swarm_summary(metrics))
        output.append("")
        output.append(self._render_agent_table(metrics))
        return "\n".join(output)

    def print_dashboard(self, metrics: SwarmMetrics) -> None:
        """Print the dashboard to stdout."""
        print("\033[2J\033[H")  # Clear screen
        print(self.render_dashboard(metrics))

    def start_live_monitoring(self, refresh_interval: float = 2.0) -> None:
        """Start live monitoring with periodic updates."""
        self.running = True
        try:
            while self.running:
                metrics = self.collector.collect_metrics()
                self.print_dashboard(metrics)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            self.stop_live_monitoring()

    def stop_live_monitoring(self) -> None:
        """Stop live monitoring."""
        self.running = False
        print("\n\nMonitoring stopped.")

    def export_metrics_json(self, metrics: SwarmMetrics, filepath: str) -> None:
        """Export metrics to JSON file."""
        data = asdict(metrics)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Metrics exported to {filepath}")

    def get_metrics_snapshot(self) -> SwarmMetrics:
        """Get a single snapshot of current metrics."""
        return self.collector.collect_metrics()


def main():
    parser = argparse.ArgumentParser(
        description="Agent Activity Monitor - Real-Time Dashboard for Swarm Health"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=5,
        help="Number of agents to monitor (default: 5)"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "snapshot", "export"],
        default="snapshot",
        help="Dashboard mode: live (continuous), snapshot (single), or export (JSON file)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Refresh interval in seconds for live mode (default
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:44:07.817Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2025-01-15

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire swarm. Provides live health checks, alert
generation, and comprehensive metrics aggregation.
"""

import argparse
import json
import random
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(Enum):
    """Agent operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TaskMetric:
    """Individual task execution metric."""
    task_id: str
    agent_id: str
    status: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AgentMetrics:
    """Aggregated metrics for a single agent."""
    agent_id: str
    status: str = AgentStatus.HEALTHY.value
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_running: int = 0
    error_rate: float = 0.0
    avg_task_duration_ms: float = 0.0
    last_heartbeat: Optional[float] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime_seconds: float = 0.0
    recent_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SwarmMetrics:
    """Aggregated metrics for entire swarm."""
    timestamp: float
    total_agents: int = 0
    healthy_agents: int = 0
    degraded_agents: int = 0
    unhealthy_agents: int = 0
    offline_agents: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_tasks_running: int = 0
    average_error_rate: float = 0.0
    average_task_duration_ms: float = 0.0
    swarm_throughput_tasks_per_sec: float = 0.0
    critical_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AgentActivityMonitor:
    """Real-time monitoring system for swarm health and performance."""

    def __init__(
        self,
        error_rate_threshold: float = 0.1,
        heartbeat_timeout_seconds: int = 10,
        max_cpu_usage: float = 80.0,
        max_memory_usage: float = 85.0,
        metrics_window_seconds: int = 60,
    ):
        """Initialize the monitor with configurable thresholds."""
        self.error_rate_threshold = error_rate_threshold
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.max_cpu_usage = max_cpu_usage
        self.max_memory_usage = max_memory_usage
        self.metrics_window_seconds = metrics_window_seconds

        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.task_metrics: deque = deque(maxlen=10000)
        self.alerts: deque = deque(maxlen=1000)
        self.lock = threading.RLock()
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def record_task(
        self,
        task_id: str,
        agent_id: str,
        status: TaskStatus,
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a task execution metric."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)

            metric = TaskMetric(
                task_id=task_id,
                agent_id=agent_id,
                status=status.value,
                start_time=time.time() - (duration_ms / 1000.0),
                end_time=time.time(),
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
            )
            self.task_metrics.append(metric)

            agent = self.agent_metrics[agent_id]
            if status == TaskStatus.COMPLETED and success:
                agent.tasks_completed += 1
            elif status == TaskStatus.FAILED or not success:
                agent.tasks_failed += 1
                if error_message:
                    agent.recent_errors.append(error_message)
                    if len(agent.recent_errors) > 10:
                        agent.recent_errors.pop(0)

            self._update_agent_error_rate(agent_id)
            self._update_agent_status(agent_id)

    def record_heartbeat(self, agent_id: str) -> None:
        """Record agent heartbeat."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)

            agent = self.agent_metrics[agent_id]
            agent.last_heartbeat = time.time()
            if agent.status == AgentStatus.OFFLINE.value:
                agent.status = AgentStatus.HEALTHY.value

    def update_agent_resources(
        self, agent_id: str, cpu_usage: float, memory_usage: float
    ) -> None:
        """Update agent resource metrics."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)

            agent = self.agent_metrics[agent_id]
            agent.cpu_usage = cpu_usage
            agent.memory_usage = memory_usage
            self._update_agent_status(agent_id)

    def set_agent_uptime(self, agent_id: str, uptime_seconds: float) -> None:
        """Set agent uptime."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)

            self.agent_metrics[agent_id].uptime_seconds = uptime_seconds

    def _update_agent_error_rate(self, agent_id: str) -> None:
        """Calculate agent error rate."""
        agent = self.agent_metrics[agent_id]
        total = agent.tasks_completed + agent.tasks_failed
        if total > 0:
            agent.error_rate = agent.tasks_failed / total
        else:
            agent.error_rate = 0.0

    def _update_agent_status(self, agent_id: str) -> None:
        """Determine agent status based on metrics."""
        agent = self.agent_metrics[agent_id]
        current_time = time.time()

        if agent.last_heartbeat is None:
            agent.status = AgentStatus.OFFLINE.value
            return

        if (
            current_time - agent.last_heartbeat
            > self.heartbeat_timeout_seconds
        ):
            agent.status = AgentStatus.OFFLINE.value
            return

        issue_count = 0
        if agent.error_rate > self.error_rate_threshold:
            issue_count += 1
        if agent.cpu_usage > self.max_cpu_usage:
            issue_count += 1
        if agent.memory_usage > self.max_memory_usage:
            issue_count += 1

        if issue_count >= 2:
            agent.status = AgentStatus.UNHEALTHY.value
        elif issue_count == 1:
            agent.status = AgentStatus.DEGRADED.value
        else:
            agent.status = AgentStatus.HEALTHY.value

    def _calculate_avg_task_duration(self, agent_id: str) -> float:
        """Calculate average task duration for an agent."""
        cutoff_time = time.time() - self.metrics_window_seconds
        durations = [
            m.duration_ms
            for m in self.task_metrics
            if m.agent_id == agent_id and m.end_time is not None and m.end_time > cutoff_time
        ]
        return sum(durations) / len(durations) if durations else 0.0

    def _generate_alerts(self) -> List[str]:
        """Generate alerts based on current metrics."""
        alerts = []

        for agent_id, agent in self.agent_metrics.items():
            if agent.status == AgentStatus.UNHEALTHY.value:
                alerts.append(
                    f"CRITICAL: Agent {agent_id} is UNHEALTHY "
                    f"(CPU: {agent.cpu_usage:.1f}%, Memory: {agent.memory_usage:.1f}%, "
                    f"Error Rate: {agent.error_rate:.2%})"
                )
            elif agent.status == AgentStatus.OFFLINE.value:
                alerts.append(
                    f"CRITICAL: Agent {agent_id} is OFFLINE "
                    f"(No heartbeat for {time.time() - (agent.last_heartbeat or 0):.0f}s)"
                )
            elif agent.status == AgentStatus.DEGRADED.value:
                alerts.append(
                    f"WARNING: Agent {agent_id} is DEGRADED "
                    f"(CPU: {agent.cpu_usage:.1f}%, Memory: {agent.memory_usage:.1f}%, "
                    f"Error Rate: {agent.error_rate:.2%})"
                )

            if agent.tasks_failed > 10:
                recent_failures = agent.recent_errors[-3:]
                alerts.append(
                    f"WARNING: Agent {agent_id} has {agent.tasks_failed} failed tasks. "
                    f"Recent errors: {'; '.join(recent_failures[:2])}"
                )

        return alerts

    def get_agent_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for specific agent or all agents."""
        with self.lock:
            if agent_id:
                if agent_id in self.agent_metrics:
                    agent = self.agent_metrics[agent_id]
                    agent.avg_task_duration_ms = self._calculate_avg_task_duration(
                        agent_id
                    )
                    return {"agent": agent.to_dict()}
                return {}
            else:
                for aid in self.agent_metrics:
                    self.agent_metrics[aid].avg_task_duration_ms = (
                        self._calculate_avg_task_duration(aid)
                    )
                return {
                    "agents": [
                        agent.to_dict() for agent in self.agent_metrics.values()
                    ]
                }

    def get_swarm_metrics(self) -> SwarmMetrics:
        """Get aggregated swarm metrics."""
        with self.lock:
            if not self.agent_metrics:
                return SwarmMetrics(timestamp=time.time())

            status_counts = defaultdict(int)
            total_error_rate = 0.0
            total_duration = 0.0
            duration_count = 0

            for agent in self.agent_metrics.values():
                status_counts[agent.status] += 1
                total_error_rate += agent.error_rate
                avg_dur = self._calculate_avg_task_duration(agent.agent_id)
                if avg_dur > 0:
                    total_duration += avg_dur
                    duration_count += 1

            cutoff_time = time.time() - self.metrics_window_seconds
            recent_completed = sum(
                1
                for m in self.task_metrics
                if m.end_time and m.end_time > cutoff_time and m.success
            )
            throughput = (
                recent_completed / self.metrics_window_seconds
                if self.metrics_window_seconds > 0
                else 0.0
            )

            alerts = self._generate_alerts()
            for alert in alerts:
                self.alerts.append(
                    {
                        "timestamp": time.time(),
                        "message": alert,
                    }
                )

            return SwarmMetrics(
                timestamp=time.time(),
                total_agents=len(self.agent_metrics),
                healthy_agents=status_counts[AgentStatus.HEALTHY.value],
                degraded_agents=status_counts[AgentStatus.DEGRADED.value],
                unhealthy_agents=status_counts[AgentStatus.UNHEALTHY.value],
                offline_agents=status_counts[AgentStatus.OFFLINE.value],
                total_tasks_completed=sum(
                    a.tasks_completed for a in self.agent_metrics.values()
                ),
                total_tasks_failed=sum(
                    a.tasks_failed for a in self.agent_metrics.values()
                ),
                total_tasks_running=sum(
                    a.tasks_running for a in self.agent_metrics.values()
                ),
                average_error_rate=(
                    total_error_rate / len(self.agent_metrics)
                    if self.agent_metrics
                    else 0.0
                ),
                average_task_duration_ms=(
                    total_duration / duration_count if duration_count > 0 else 0.0
                ),
                swarm_throughput_tasks_per_sec=throughput,
                critical_alerts=[a for a in alerts if "CRITICAL" in a],
            )

    def get_dashboard_json(self) -> str:
        """Get formatted dashboard as JSON."""
        swarm = self.get_swarm_metrics()
        agents = self.get_agent_metrics()

        dashboard = {
            "swarm": swarm.to_dict(),
            "agents": agents.get("agents", []),
            "recent_alerts": list(self.alerts)[-20:],
            "timestamp": datetime.fromtimestamp(swarm.timestamp).isoformat(),
        }

        return json.dumps(dashboard, indent=2)

    def start_monitoring_loop(self, update_interval: float = 5.0) -> None:
        """Start background monitoring thread."""
        if self.running:
            return

        self.running = True

        def monitor_loop():
            while self.running:
                try:
                    with self.lock:
                        self._generate_alerts()
                    time.sleep(update_interval)
                except Exception as e:
                    print(f"Monitor loop error: {e}", file=sys.stderr)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring_loop(self) -> None:
        """Stop background monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)


def generate_sample_data(monitor: AgentActivityMonitor, num_agents: int = 5) -> None:
    """Generate sample data for demonstration."""
    agent_ids = [f"agent-{i:03d}" for i in range(num_agents)]

    for agent_id in agent_ids:
        monitor.record_heartbeat(agent_id)
        monitor.set_agent_uptime(agent_id, random.uniform(3600, 86400))

    task_id_counter = 0
    for _ in range(100):
        for agent_id in agent_ids:
            task_id = f"task-{task_id_counter:06d}"
            task_id_counter += 1

            status = random.choices(
                [TaskStatus.COMPLETED, TaskStatus.FAILED],
                weights=[0.9, 0.1],
            )[0]

            duration_ms = random.gauss(500, 150)
            duration_ms = max(10, duration_ms)

            success = status == TaskStatus.COMPLETED
            error_msg = None
            if not success:
                error_msg = random.choice(
                    [
                        "Timeout",
                        "Resource exhausted",
                        "Invalid input",
                        "Network error",
                    ]
                )

            monitor.record_task(
                task_id=task_id,
                agent_id=agent_id,
                status=status,
                duration_ms=duration_ms,
                success=success,
                error_message=error_msg,
            )

            cpu = random.gauss(45, 15)
            cpu = min(100, max(0, cpu))

            memory = random.gauss(50, 12)
            memory = min(100, max(0, memory))

            monitor.update_agent_resources(agent_id, cpu, memory)


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Activity Monitor: Real-Time Dashboard for Swarm Health",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --agents 5
  python3 solution.py --agents 10 --error-threshold 0.15
  python3 solution.py --agents 3 --heartbeat-timeout 20 --demo
        """,
    )

    parser.add_argument(
        "--agents",
        type=int,
        default=5,
        help="Number of agents to simulate (default: 5)",
    )

    parser.add_argument(
        "--error-threshold",
        type=float,
        default=0.1,
        help="Error rate threshold for alerting (default: 0.1)",
    )

    parser.add_argument(
        "--heartbeat-timeout",
        type=int,
        default=10,
        help="Heartbeat timeout in seconds (default: 10)",
    )

    parser.add_argument(
        "--max-cpu",
        type=float,
        default=80.0,
        help="Maximum CPU usage threshold (default: 80.0)",
    )

    parser.add_argument(
        "--max-memory",
        type=float,
        default=85.0,
        help="Maximum memory usage threshold (default: 85.0)",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with generated sample data",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Monitoring update interval in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    monitor = AgentActivityMonitor(
        error_rate_threshold=args.error_threshold,
        heartbeat_timeout_seconds=args.heartbeat_timeout,
        max_cpu_usage=args.max_cpu,
        max_memory_usage=args.max_memory,
    )

    print("=" * 80)
    print("AGENT ACTIVITY MONITOR - SWARM HEALTH DASHBOARD")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  Agents: {args.agents}")
    print(f"  Error Threshold: {args.error_threshold:.1%}")
    print(f"  Heartbeat Timeout: {args.heartbeat_timeout}s")
    print(f"  Max CPU: {args.max_cpu}%")
    print(f"  Max Memory: {args.max_memory}%")
    print()

    if args.demo:
        print("Generating sample data...")
        generate_sample_data(monitor, args.agents)
        time.sleep(1)

    monitor.start_monitoring_loop(update_interval=args.interval)

    try:
        iteration = 0
        while True:
            print(f"\n{'='*80}")
            print(f"Dashboard Update #{iteration} - {datetime.now().isoformat()}")
            print(f"{'='*80}")

            dashboard_json = monitor.get_dashboard_json()
            print(dashboard_json)

            iteration += 1
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nShutting down monitor...")
        monitor.stop_monitoring_loop()
        print("Monitor stopped.")


if __name__ == "__main__":
    main()
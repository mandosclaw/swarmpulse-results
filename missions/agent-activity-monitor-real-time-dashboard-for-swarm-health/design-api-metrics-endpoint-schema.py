#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design API metrics endpoint schema
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:14:48.265Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Design API metrics endpoint schema
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2024

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire swarm.
"""

import json
import time
import random
import argparse
import sys
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class AgentStatus(Enum):
    """Agent operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class MetricThreshold:
    """Configurable thresholds for metrics."""
    error_rate_critical: float = 0.1
    error_rate_warning: float = 0.05
    cpu_critical: float = 90.0
    cpu_warning: float = 75.0
    memory_critical: float = 85.0
    memory_warning: float = 70.0
    response_time_critical_ms: float = 5000.0
    response_time_warning_ms: float = 2000.0
    task_timeout_seconds: int = 300


@dataclass
class TaskMetric:
    """Individual task execution metric."""
    task_id: str
    agent_id: str
    status: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AgentHealthMetric:
    """Agent health and performance metric."""
    agent_id: str
    status: str
    uptime_seconds: float
    cpu_percent: float
    memory_percent: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    error_rate: float
    avg_response_time_ms: float
    last_heartbeat: float
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SwarmMetric:
    """Overall swarm health metric."""
    timestamp: float
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    critical_agents: int
    offline_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    pending_tasks: int
    swarm_error_rate: float
    swarm_cpu_avg: float
    swarm_memory_avg: float
    swarm_throughput: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collects and aggregates metrics from swarm agents."""

    def __init__(self, thresholds: Optional[MetricThreshold] = None):
        """Initialize metrics collector."""
        self.thresholds = thresholds or MetricThreshold()
        self.agent_metrics: Dict[str, AgentHealthMetric] = {}
        self.task_metrics: List[TaskMetric] = []
        self.metric_history: List[SwarmMetric] = []
        self.lock_time: float = time.time()

    def add_agent_metric(self, metric: AgentHealthMetric) -> None:
        """Add or update agent metric."""
        self.agent_metrics[metric.agent_id] = metric

    def add_task_metric(self, metric: TaskMetric) -> None:
        """Add task metric."""
        self.task_metrics.append(metric)
        if len(self.task_metrics) > 10000:
            self.task_metrics = self.task_metrics[-10000:]

    def get_agent_status(self, agent_id: str) -> Optional[AgentHealthMetric]:
        """Get current status of a single agent."""
        return self.agent_metrics.get(agent_id)

    def get_all_agent_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        return [metric.to_dict() for metric in self.agent_metrics.values()]

    def calculate_swarm_metric(self) -> SwarmMetric:
        """Calculate overall swarm metrics."""
        timestamp = time.time()
        agents = list(self.agent_metrics.values())

        if not agents:
            return SwarmMetric(
                timestamp=timestamp,
                total_agents=0,
                healthy_agents=0,
                degraded_agents=0,
                critical_agents=0,
                offline_agents=0,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                running_tasks=0,
                pending_tasks=0,
                swarm_error_rate=0.0,
                swarm_cpu_avg=0.0,
                swarm_memory_avg=0.0,
                swarm_throughput=0.0,
            )

        healthy_count = sum(1 for a in agents if a.status == AgentStatus.HEALTHY.value)
        degraded_count = sum(1 for a in agents if a.status == AgentStatus.DEGRADED.value)
        critical_count = sum(1 for a in agents if a.status == AgentStatus.CRITICAL.value)
        offline_count = sum(1 for a in agents if a.status == AgentStatus.OFFLINE.value)

        cpu_avg = sum(a.cpu_percent for a in agents) / len(agents)
        memory_avg = sum(a.memory_percent for a in agents) / len(agents)

        total_failed = sum(a.failed_tasks for a in agents)
        total_completed = sum(a.completed_tasks for a in agents)
        total_tasks = total_completed + total_failed
        error_rate = (
            total_failed / total_tasks if total_tasks > 0 else 0.0
        )

        running = sum(a.active_tasks for a in agents)

        seconds_since_lock = time.time() - self.lock_time
        throughput = (
            total_completed / seconds_since_lock if seconds_since_lock > 0 else 0.0
        )

        swarm_metric = SwarmMetric(
            timestamp=timestamp,
            total_agents=len(agents),
            healthy_agents=healthy_count,
            degraded_agents=degraded_count,
            critical_agents=critical_count,
            offline_agents=offline_count,
            total_tasks=total_tasks,
            completed_tasks=total_completed,
            failed_tasks=total_failed,
            running_tasks=running,
            pending_tasks=0,
            swarm_error_rate=error_rate,
            swarm_cpu_avg=cpu_avg,
            swarm_memory_avg=memory_avg,
            swarm_throughput=throughput,
        )

        self.metric_history.append(swarm_metric)
        if len(self.metric_history) > 1000:
            self.metric_history = self.metric_history[-1000:]

        return swarm_metric

    def get_agent_health_summary(self) -> Dict[str, Any]:
        """Get health summary grouped by status."""
        by_status = defaultdict(list)
        for agent in self.agent_metrics.values():
            by_status[agent.status].append(agent.agent_id)

        return {
            AgentStatus.HEALTHY.value: by_status.get(AgentStatus.HEALTHY.value, []),
            AgentStatus.DEGRADED.value: by_status.get(AgentStatus.DEGRADED.value, []),
            AgentStatus.CRITICAL.value: by_status.get(AgentStatus.CRITICAL.value, []),
            AgentStatus.OFFLINE.value: by_status.get(AgentStatus.OFFLINE.value, []),
        }

    def get_task_performance(self) -> Dict[str, Any]:
        """Get task performance statistics."""
        if not self.task_metrics:
            return {
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "avg_cpu_usage": 0.0,
                "avg_memory_usage": 0.0,
            }

        successful = [t for t in self.task_metrics if t.success]
        total = len(self.task_metrics)

        durations = [t.duration_ms for t in successful]
        cpu_usages = [t.cpu_usage for t in successful]
        memory_usages = [t.memory_usage for t in successful]

        return {
            "total_tasks": total,
            "success_rate": len(successful) / total if total > 0 else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "max_duration_ms": max(durations) if durations else 0.0,
            "min_duration_ms": min(durations) if durations else 0.0,
            "avg_cpu_usage": sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0.0,
            "avg_memory_usage": (
                sum(memory_usages) / len(memory_usages) if memory_usages else 0.0
            ),
        }

    def get_metrics_endpoint_schema(self) -> Dict[str, Any]:
        """Generate complete metrics endpoint schema."""
        swarm_metric = self.calculate_swarm_metric()

        return {
            "status": "success",
            "timestamp": swarm_metric.timestamp,
            "swarm": swarm_metric.to_dict(),
            "agents": {
                "summary": self.get_agent_health_summary(),
                "details": self.get_all_agent_status(),
            },
            "tasks": self.get_task_performance(),
            "thresholds": asdict(self.thresholds),
        }


def generate_mock_agents(count: int) -> List[AgentHealthMetric]:
    """Generate mock agent metrics for demonstration."""
    agents = []
    for i in range(count):
        agent_id = f"agent-{i:04d}"
        cpu = random.uniform(10, 95)
        memory = random.uniform(20, 90)

        if random.random() > 0.85:
            status = AgentStatus.OFFLINE.value
        elif cpu > 85 or memory > 85:
            status = AgentStatus.CRITICAL.value
        elif cpu > 70 or memory > 70:
            status = AgentStatus.DEGRADED.value
        else:
            status = AgentStatus.HEALTHY.value

        agent = AgentHealthMetric(
            agent_id=agent_id,
            status=status,
            uptime_seconds=random.uniform(3600, 864000),
            cpu_percent=cpu,
            memory_percent=memory,
            active_tasks=random.randint(0, 50),
            completed_tasks=random.randint(100, 5000),
            failed_tasks=random.randint(0, 100),
            error_rate=random.uniform(0.0, 0.1),
            avg_response_time_ms=random.uniform(100, 3000),
            last_heartbeat=time.time() - random.randint(0, 60),
        )
        agents.append(agent)

    return agents


def generate_mock_tasks(agent_ids: List[str], count: int) -> List[TaskMetric]:
    """Generate mock task metrics for demonstration."""
    tasks = []
    for i in range(count):
        task_id = f"task-{i:06d}"
        agent_id = random.choice(agent_ids)
        start_time = time.time() - random.uniform(10, 3600)
        duration = random.uniform(100, 4000)
        end_time = start_time + (duration / 1000.0)
        success = random.random() > 0.08

        task = TaskMetric(
            task_id=task_id,
            agent_id=agent_id,
            status=TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration,
            cpu_usage=random.uniform(5, 95),
            memory_usage=random.uniform(10, 80),
            success=success,
            error_message=None if success else "Task execution failed",
        )
        tasks.append(task)

    return tasks


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SwarmPulse Agent Activity Monitor - Metrics Endpoint Schema"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=50,
        help="Number of agents to simulate (default: 50)",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=500,
        help="Number of task metrics to generate (default: 500)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format (default: pretty)",
    )
    parser.add_argument(
        "--error-rate-critical",
        type=float,
        default=0.1,
        help="Critical error rate threshold (default: 0.1)",
    )
    parser.add_argument(
        "--error-rate-warning",
        type=float,
        default=0.05,
        help="Warning error rate threshold (default: 0.05)",
    )
    parser.add_argument(
        "--cpu-critical",
        type=float,
        default=90.0,
        help="Critical CPU threshold (default: 90.0)",
    )
    parser.add_argument(
        "--memory-critical",
        type=float,
        default=85.0,
        help="Critical memory threshold (default: 85.0)",
    )

    args = parser.parse_args()

    thresholds = MetricThreshold(
        error_rate_critical=args.error_rate_critical,
        error_rate_warning=args.error_rate_warning,
        cpu_critical=args.cpu_critical,
        memory_critical=args.memory_critical,
    )

    collector = MetricsCollector(thresholds=thresholds)

    print(f"Generating {args.agents} mock agents...", file=sys.stderr)
    agents = generate_mock_agents(args.agents)
    for agent in agents:
        collector.add_agent_metric(agent)

    agent_ids = [agent.agent_id for agent in agents]

    print(f"Generating {args.tasks} mock task metrics...", file=sys.stderr)
    tasks = generate_mock_tasks(agent_ids, args.tasks)
    for task in tasks:
        collector.add_task_metric(task)

    print("Calculating swarm metrics...", file=sys.stderr)
    schema = collector.get_metrics_endpoint_schema()

    if args.output == "json":
        print(json.dumps(schema, indent=None, separators=(',', ':')))
    else:
        print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
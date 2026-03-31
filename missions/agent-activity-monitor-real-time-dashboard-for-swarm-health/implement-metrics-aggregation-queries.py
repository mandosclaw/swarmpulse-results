#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement metrics aggregation queries
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:43:34.043Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Metrics Aggregation Queries for Agent Activity Monitor
Mission: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2025-01-20

Real-time monitoring dashboard implementation tracking agent health, task throughput,
error rates, and performance metrics across the entire swarm.
"""

import argparse
import json
import time
import statistics
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple, Any
from enum import Enum


class MetricType(Enum):
    """Enumeration of metric types in the swarm."""
    TASK_THROUGHPUT = "task_throughput"
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    TASK_COMPLETION = "task_completion"
    QUEUE_DEPTH = "queue_depth"


class HealthStatus(Enum):
    """Health status levels for agents."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class AgentMetric:
    """Single metric data point from an agent."""
    agent_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AgentHealthSnapshot:
    """Current health snapshot of an agent."""
    agent_id: str
    status: HealthStatus
    timestamp: datetime
    metrics: Dict[str, float]
    last_heartbeat: datetime
    uptime_seconds: float


@dataclass
class SwarmMetricsSnapshot:
    """Aggregated metrics for entire swarm."""
    timestamp: datetime
    agent_count: int
    healthy_count: int
    warning_count: int
    critical_count: int
    offline_count: int
    avg_throughput: float
    avg_error_rate: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    total_tasks_completed: int
    total_errors: int
    avg_cpu_usage: float
    avg_memory_usage: float


class MetricsAggregator:
    """Aggregates and queries metrics across swarm agents."""

    def __init__(self, max_history_size: int = 10000, retention_seconds: int = 3600):
        """
        Initialize metrics aggregator.
        
        Args:
            max_history_size: Maximum metrics to keep in memory per agent
            retention_seconds: Seconds to retain historical data
        """
        self.max_history_size = max_history_size
        self.retention_seconds = retention_seconds
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.agent_heartbeats: Dict[str, datetime] = {}
        self.agent_start_times: Dict[str, datetime] = {}
        self.lock = threading.RLock()

    def record_metric(self, metric: AgentMetric) -> None:
        """Record a metric from an agent."""
        with self.lock:
            agent_key = f"{metric.agent_id}:{metric.metric_type.value}"
            self.metrics[agent_key].append(metric)
            self.agent_heartbeats[metric.agent_id] = metric.timestamp
            
            if metric.agent_id not in self.agent_start_times:
                self.agent_start_times[metric.agent_id] = metric.timestamp
            
            self._cleanup_old_metrics(metric.timestamp)

    def _cleanup_old_metrics(self, current_time: datetime) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = current_time - timedelta(seconds=self.retention_seconds)
        for key in list(self.metrics.keys()):
            while self.metrics[key] and self.metrics[key][0].timestamp < cutoff_time:
                self.metrics[key].popleft()

    def get_agent_metrics(self, agent_id: str, metric_type: MetricType = None, 
                         minutes: int = 5) -> List[AgentMetric]:
        """
        Retrieve metrics for a specific agent.
        
        Args:
            agent_id: ID of the agent
            metric_type: Optional specific metric type to filter
            minutes: Look back this many minutes
            
        Returns:
            List of matching metrics
        """
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            results = []
            
            if metric_type:
                key = f"{agent_id}:{metric_type.value}"
                metrics_list = self.metrics.get(key, [])
                results = [m for m in metrics_list if m.timestamp >= cutoff_time]
            else:
                for key in self.metrics:
                    if key.startswith(f"{agent_id}:"):
                        metrics_list = self.metrics[key]
                        results.extend([m for m in metrics_list if m.timestamp >= cutoff_time])
            
            return results

    def get_agent_health(self, agent_id: str, timeout_seconds: int = 30) -> AgentHealthSnapshot:
        """
        Calculate health status for a specific agent.
        
        Args:
            agent_id: ID of the agent
            timeout_seconds: Seconds without heartbeat to mark offline
            
        Returns:
            Health snapshot for the agent
        """
        with self.lock:
            now = datetime.now()
            last_heartbeat = self.agent_heartbeats.get(agent_id, now)
            start_time = self.agent_start_times.get(agent_id, now)
            uptime = (now - start_time).total_seconds()
            
            is_offline = (now - last_heartbeat).total_seconds() > timeout_seconds
            
            metrics = {}
            error_rate = 0.0
            throughput = 0.0
            latency_values = []
            
            for metric_type in MetricType:
                key = f"{agent_id}:{metric_type.value}"
                recent_metrics = list(self.metrics.get(key, []))[-100:]
                
                if recent_metrics:
                    values = [m.value for m in recent_metrics]
                    metrics[metric_type.value] = statistics.mean(values)
                    
                    if metric_type == MetricType.ERROR_RATE:
                        error_rate = metrics[metric_type.value]
                    elif metric_type == MetricType.TASK_THROUGHPUT:
                        throughput = metrics[metric_type.value]
                    elif metric_type == MetricType.LATENCY:
                        latency_values = values
            
            # Determine health status
            if is_offline:
                status = HealthStatus.OFFLINE
            elif error_rate > 10 or throughput < 1:
                status = HealthStatus.CRITICAL
            elif error_rate > 5 or throughput < 5:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return AgentHealthSnapshot(
                agent_id=agent_id,
                status=status,
                timestamp=now,
                metrics=metrics,
                last_heartbeat=last_heartbeat,
                uptime_seconds=uptime
            )

    def get_swarm_metrics(self, timeout_seconds: int = 30) -> SwarmMetricsSnapshot:
        """
        Calculate aggregated metrics for entire swarm.
        
        Args:
            timeout_seconds: Seconds without heartbeat to mark offline
            
        Returns:
            Aggregated swarm metrics snapshot
        """
        with self.lock:
            now = datetime.now()
            
            # Get all unique agents
            agent_ids = set()
            for key in self.metrics:
                agent_id = key.split(":")[0]
                agent_ids.add(agent_id)
            
            agent_ids.update(self.agent_heartbeats.keys())
            
            # Collect health snapshots
            health_snapshots = []
            for agent_id in agent_ids:
                health = self.get_agent_health(agent_id, timeout_seconds)
                health_snapshots.append(health)
            
            # Count statuses
            healthy_count = sum(1 for h in health_snapshots if h.status == HealthStatus.HEALTHY)
            warning_count = sum(1 for h in health_snapshots if h.status == HealthStatus.WARNING)
            critical_count = sum(1 for h in health_snapshots if h.status == HealthStatus.CRITICAL)
            offline_count = sum(1 for h in health_snapshots if h.status == HealthStatus.OFFLINE)
            
            # Calculate averages
            throughputs = [h.metrics.get("task_throughput", 0) for h in health_snapshots]
            error_rates = [h.metrics.get("error_rate", 0) for h in health_snapshots]
            latencies = [h.metrics.get("latency", 0) for h in health_snapshots]
            cpu_usages = [h.metrics.get("cpu_usage", 0) for h in health_snapshots]
            memory_usages = [h.metrics.get("memory_usage", 0) for h in health_snapshots]
            
            # Collect all latency values for percentiles
            all_latencies = []
            for key in self.metrics:
                if "latency" in key:
                    all_latencies.extend([m.value for m in self.metrics[key]])
            
            p95_latency = 0.0
            p99_latency = 0.0
            if all_latencies:
                sorted_latencies = sorted(all_latencies)
                p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            
            # Count totals
            total_tasks = sum(len(list(self.metrics.get(f"{aid}:task_completion", [])))
                            for aid in agent_ids)
            total_errors = sum(len(list(self.metrics.get(f"{aid}:error_rate", [])))
                             for aid in agent_ids)
            
            return SwarmMetricsSnapshot(
                timestamp=now,
                agent_count=len(agent_ids),
                healthy_count=healthy_count,
                warning_count=warning_count,
                critical_count=critical_count,
                offline_count=offline_count,
                avg_throughput=statistics.mean(throughputs) if throughputs else 0.0,
                avg_error_rate=statistics.mean(error_rates) if error_rates else 0.0,
                avg_latency=statistics.mean(latencies) if latencies else 0.0,
                p95_latency=p95_latency,
                p99_latency=p99_latency,
                total_tasks_completed=total_tasks,
                total_errors=total_errors,
                avg_cpu_usage=statistics.mean(cpu_usages) if cpu_usages else 0.0,
                avg_memory_usage=statistics.mean(memory_usages) if memory_usages else 0.0
            )

    def query_metrics_by_threshold(self, metric_type: MetricType, 
                                  threshold: float, operator: str = "greater",
                                  minutes: int = 5) -> Dict[str, List[AgentMetric]]:
        """
        Query metrics matching a threshold condition.
        
        Args:
            metric_type: Type of metric to query
            threshold: Threshold value
            operator: Comparison operator ("greater", "less", "equal")
            minutes: Look back window in minutes
            
        Returns:
            Dictionary mapping agent IDs to matching metrics
        """
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            results = defaultdict(list)
            
            for key in self.metrics:
                if metric_type.value in key:
                    agent_id = key.split(":")[0]
                    for metric in self.metrics[key]:
                        if metric.timestamp >= cutoff_time:
                            if self._check_threshold(metric.value, threshold, operator):
                                results[agent_id].append(metric)
            
            return dict(results)

    def _check_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Check if value meets threshold condition."""
        if operator == "greater":
            return value > threshold
        elif operator == "less":
            return value < threshold
        elif operator == "equal":
            return value == threshold
        return False

    def get_agent_comparison(self, agent_ids: List[str], 
                            metric_type: MetricType) -> Dict[str, Dict[str, float]]:
        """
        Compare specific metric across multiple agents.
        
        Args:
            agent_ids: List of agent IDs to compare
            metric_type: Metric type to compare
            
        Returns:
            Dictionary with stats for each agent
        """
        with self.lock:
            results = {}
            for agent_id in agent_ids:
                metrics = self.get_agent_metrics(agent_id, metric_type, minutes=5)
                if metrics:
                    values = [m.value for m in metrics]
                    results[agent_id] = {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                        "count": len(values)
                    }
                else:
                    results[agent_id] = {
                        "mean": 0.0,
                        "median": 0.0,
                        "min": 0.0,
                        "max": 0.0,
                        "stdev": 0.0,
                        "count": 0
                    }
            
            return results


class MonitoringDashboard:
    """Real-time monitoring dashboard with periodic aggregation."""

    def __init__(self, aggregator: MetricsAggregator, update_interval: int = 5):
        """
        Initialize dashboard.
        
        Args:
            aggregator: MetricsAggregator instance
            update_interval: Seconds between dashboard updates
        """
        self.aggregator = aggregator
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.snapshots = deque(maxlen=720)  # Keep 1 hour of 5-second snapshots

    def start(self) -> None:
        """Start the monitoring dashboard."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the monitoring dashboard."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                snapshot = self.aggregator.get_swarm_metrics()
                self.snapshots.append(snapshot)
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(self.update_interval)

    def get_current_dashboard(self) -> Dict[str, Any]:
        """Get current dashboard state."""
        if not self.snapshots:
            return {"status": "no_data"}
        
        latest = self.snapshots[-1]
        
        return {
            "timestamp": latest.timestamp.isoformat(),
            "swarm": {
                "total_agents": latest.agent_count,
                "healthy": latest.healthy_count,
                "warning": latest.warning_count,
                "critical": latest.critical_count,
                "offline": latest.offline_count
            },
            "performance": {
                "avg_throughput_tasks_per_min": round(latest.avg_throughput, 2),
                "avg_error_rate_percent": round(latest.avg_error_rate, 2),
                "avg_latency_ms": round(latest.avg_latency, 2),
                "p95_latency_ms": round(latest.p95_latency, 2),
                "p99_latency_ms": round(latest.p99_latency, 2),
                "total_tasks_completed": latest.total_tasks_completed,
                "total_errors": latest.total_errors
            },
            "resources": {
                "avg_cpu_usage_percent": round(latest.avg_cpu_usage, 2),
                "avg_memory_usage_percent": round(latest.avg_memory_usage, 2)
            }
        }

    def get_historical_data(self, minutes: int = 60) -> Dict[str, Any]:
        """Get historical dashboard data."""
        lookback = datetime.now() - timedelta(minutes=minutes)
        relevant_snapshots = [s for s in self.snapshots 
                            if s.timestamp >= lookback]
        
        if not relevant_snapshots:
            return {"status": "no_historical_data"}
        
        timestamps = [s.timestamp.isoformat() for s in relevant_snapshots]
        throughputs = [s.avg_throughput for s in relevant_snapshots]
        error_rates = [s.avg_error_rate for s in relevant_snapshots]
        latencies = [s.avg_latency for s in relevant_snapshots]
        healthy_counts = [s.healthy_count for s in relevant_snapshots]
        
        return {
            "timestamps": timestamps,
            "throughput": throughputs,
            "error_rate": error_rates,
            "latency": latencies,
            "healthy_agents": healthy_counts
        }


def generate_synthetic_metrics(aggregator: MetricsAggregator, 
                              num_agents: int = 5,
                              duration_seconds: int = 30) -> None:
    """Generate synthetic metrics for testing."""
    import random
    
    agent_ids = [f"agent-{i:03d}" for i in range(num_agents)]
    start_time = datetime.now()
    
    while (datetime.now() - start_time).total_seconds() < duration_seconds:
        for agent_id in agent_ids:
            current_time = datetime.now()
            
            # Generate metrics with some variance
            base_throughput = random.uniform(10, 100)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.TASK_THROUGHPUT,
                value=base_throughput,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
            
            error_rate = random.uniform(0.1, 5.0)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.ERROR_RATE,
                value=error_rate,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
            
            latency = random.uniform(10, 500)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.LATENCY,
                value=latency,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
            
            cpu = random.uniform(10, 80)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.CPU_USAGE,
                value=cpu,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
            
            memory = random.uniform(20, 70)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.MEMORY_USAGE,
                value=memory,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
            
            queue = random.uniform(0, 50)
            metric = AgentMetric(
                agent_id=agent_id,
                metric_type=MetricType.QUEUE_DEPTH,
                value=queue,
                timestamp=current_time
            )
            aggregator.record_metric(metric)
        
        time.sleep(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Activity Monitor - Metrics Aggregation Queries"
    )
    parser.add_argument(
        "--mode",
        choices=["dashboard", "query", "health", "compare", "threshold"],
        default="dashboard",
        help="Operating mode"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=5,
        help="Number of synthetic agents to simulate"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration to collect metrics (seconds)"
    )
    parser.add_argument(
        "--update-interval",
        type=int,
        default=5,
        help="Dashboard update interval (seconds)"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Specific agent ID to query"
    )
    parser.add_argument(
        "--metric-type",
        type=str,
        choices=["task_throughput", "error_rate", "latency", 
                "cpu_usage", "memory_usage", "queue_depth"],
        help="Metric type to query"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Threshold value for threshold queries"
    )
    parser.add_argument(
        "--operator",
        type=str,
        default="greater",
        choices=["greater", "less", "equal"],
        help="Threshold comparison operator"
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="json",
        choices=["json", "pretty"],
        help="Output format"
    )
    
    args = parser.parse_args()
    
    # Initialize aggregator
    aggregator = MetricsAggregator(max_history_size=10000, retention_seconds=3600)
    
    # Start metrics generation in background
    gen_thread = threading.Thread(
        target=generate_synthetic_metrics,
        args=(aggregator, args.agents, args.duration),
        daemon=True
    )
    gen_thread.start()
    
    # Initialize dashboard
    dashboard = MonitoringDashboard(aggregator, update_interval=args.update_interval)
    dashboard.start()
    
    # Give metrics time to accumulate
    time.sleep(3)
    
    # Process request based on mode
    if args.mode == "dashboard":
        print("=== CURRENT DASHBOARD ===")
        dashboard_data = dashboard.get_current_dashboard()
        if args.output_format == "pretty":
            print(json.dumps(dashboard_data, indent=2))
        else:
            print(json.dumps(dashboard_data))
        
        print("\n=== HISTORICAL DATA (Last 60 seconds) ===")
        historical = dashboard.get_historical_data(minutes=1)
        if args.output_format == "pretty":
            print(json.dumps(historical, indent=2, default=str))
        else:
            print(json.dumps(historical, default=str))
    
    elif args.mode == "health" and args.agent_id:
        health = aggregator.get_agent_health(args.agent_id)
        output = {
            "agent_id": health.agent_id,
            "status": health.status.value,
            "timestamp": health.timestamp.isoformat(),
            "uptime_seconds": round(health.uptime_seconds, 2),
            "last_heartbeat": health.last_heartbeat.isoformat(),
            "metrics": {k: round(v, 2) for k, v in health.metrics.items()}
        }
        if args.output_format == "pretty":
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
    
    elif args.mode == "query" and args.agent_id and args.metric_type:
        metrics = aggregator.get_agent_metrics(args.agent_id, 
                                              MetricType[args.metric_type.upper()],
                                              minutes=5)
        output = {
            "agent_id": args.agent_id,
            "metric_type": args.metric_type,
            "count": len(metrics),
            "data": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": round(m.value, 2)
                }
                for m in metrics[-50:]
            ]
        }
        if args.output_format == "pretty":
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
    
    elif args.mode == "threshold" and args.metric_type and args.threshold is not None:
        results = aggregator.query_metrics_by_threshold(
            MetricType[args.metric_type.upper()],
            args.threshold,
            args.operator,
            minutes=5
        )
        output = {
            "metric_type": args.metric_type,
            "threshold": args.threshold,
            "operator": args.operator,
            "agents_matching": len(results),
            "agents": {
                agent_id: {
                    "count": len(metrics),
                    "recent_values": [round(m.value, 2) for m in metrics[-5:]]
                }
                for agent_id, metrics in results.items()
            }
        }
        if args.output_format == "pretty":
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
    
    elif args.mode == "compare" and args.metric_type:
        agent_ids = [f"agent-{i:03d}" for i in range(args.agents)]
        comparison = aggregator.get_agent_comparison(agent_ids, 
                                                     MetricType[args.metric_type.upper()])
        output = {
            "metric_type": args.metric_type,
            "agents": {
                agent_id: {k: round(v, 2) for k, v in stats.items()}
                for agent_id, stats in comparison.items()
            }
        }
        if args.output_format == "pretty":
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
    
    else:
        print("Invalid mode or missing required arguments")
        print("Examples:")
        print("  python solution.py --mode dashboard")
        print("  python solution.py --mode health --agent-id agent-000")
        print("  python solution.py --mode query --agent-id agent-000 --metric-type latency")
        print("  python solution.py --mode threshold --metric-type error_rate --threshold 5.0 --operator greater")
        print("  python solution.py --mode compare --metric-type task_throughput")
    
    dashboard.stop()
    gen_thread.join(timeout=5)


if __name__ == "__main__":
    main()
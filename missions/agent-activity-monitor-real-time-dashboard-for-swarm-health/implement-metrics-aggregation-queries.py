#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement metrics aggregation queries
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T22:01:54.729Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Metrics Aggregation Queries
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2024

Real-time monitoring dashboard tracking agent health, task throughput, 
error rates, and performance metrics across the entire swarm.
"""

import argparse
import json
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
import threading


@dataclass
class AgentMetric:
    """Represents a single agent metric snapshot."""
    agent_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    task_count: int
    completed_tasks: int
    failed_tasks: int
    error_rate: float
    avg_task_duration: float
    uptime_seconds: float
    status: str


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across the swarm."""
    timestamp: float
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    swarm_error_rate: float
    avg_cpu_usage: float
    avg_memory_usage: float
    max_cpu_usage: float
    max_memory_usage: float
    avg_task_duration: float
    total_uptime: float
    agent_details: List[Dict[str, Any]]
    health_status: str
    alerts: List[str]


class MetricsStore:
    """In-memory store for agent metrics with time-window aggregation."""
    
    def __init__(self, window_size_seconds: int = 300):
        self.metrics: Dict[str, List[AgentMetric]] = defaultdict(list)
        self.window_size = window_size_seconds
        self.lock = threading.Lock()
    
    def add_metric(self, metric: AgentMetric) -> None:
        """Add a metric snapshot for an agent."""
        with self.lock:
            self.metrics[metric.agent_id].append(metric)
            self._cleanup_old_metrics()
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than the window size."""
        cutoff_time = time.time() - self.window_size
        for agent_id in self.metrics:
            self.metrics[agent_id] = [
                m for m in self.metrics[agent_id] 
                if m.timestamp > cutoff_time
            ]
    
    def get_agent_metrics(self, agent_id: str) -> List[AgentMetric]:
        """Get all metrics for a specific agent within the window."""
        with self.lock:
            return self.metrics.get(agent_id, [])
    
    def get_all_agents(self) -> List[str]:
        """Get list of all agents with metrics."""
        with self.lock:
            return list(self.metrics.keys())
    
    def get_latest_metrics(self) -> Dict[str, AgentMetric]:
        """Get the latest metric for each agent."""
        with self.lock:
            latest = {}
            for agent_id, metrics_list in self.metrics.items():
                if metrics_list:
                    latest[agent_id] = metrics_list[-1]
            return latest


class MetricsAggregator:
    """Aggregates metrics across swarm for dashboard reporting."""
    
    def __init__(self, store: MetricsStore):
        self.store = store
    
    def aggregate_swarm_metrics(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        error_threshold: float = 10.0
    ) -> AggregatedMetrics:
        """
        Aggregate all agent metrics into swarm-level statistics.
        
        Args:
            cpu_threshold: Alert threshold for CPU usage percentage
            memory_threshold: Alert threshold for memory usage percentage
            error_threshold: Alert threshold for error rate percentage
        
        Returns:
            AggregatedMetrics containing swarm-wide statistics
        """
        latest_metrics = self.store.get_latest_metrics()
        
        if not latest_metrics:
            return self._empty_aggregation()
        
        agents = list(latest_metrics.values())
        
        # Calculate aggregated values
        active_agents = len([a for a in agents if a.status == "healthy"])
        total_tasks = sum(a.task_count for a in agents)
        completed_tasks = sum(a.completed_tasks for a in agents)
        failed_tasks = sum(a.failed_tasks for a in agents)
        
        # Calculate error rate
        swarm_error_rate = (
            (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )
        
        # CPU and memory stats
        cpu_usages = [a.cpu_usage for a in agents]
        memory_usages = [a.memory_usage for a in agents]
        task_durations = [a.avg_task_duration for a in agents if a.avg_task_duration > 0]
        uptimes = [a.uptime_seconds for a in agents]
        
        avg_cpu = statistics.mean(cpu_usages) if cpu_usages else 0
        avg_memory = statistics.mean(memory_usages) if memory_usages else 0
        max_cpu = max(cpu_usages) if cpu_usages else 0
        max_memory = max(memory_usages) if memory_usages else 0
        avg_task_duration = statistics.mean(task_durations) if task_durations else 0
        total_uptime = sum(uptimes) if uptimes else 0
        
        # Generate alerts
        alerts = self._generate_alerts(
            agents, avg_cpu, avg_memory, swarm_error_rate,
            cpu_threshold, memory_threshold, error_threshold
        )
        
        # Determine overall health status
        health_status = self._determine_health_status(
            active_agents, len(agents), swarm_error_rate, max_cpu, max_memory
        )
        
        # Prepare agent details
        agent_details = [
            {
                "agent_id": a.agent_id,
                "status": a.status,
                "cpu_usage": round(a.cpu_usage, 2),
                "memory_usage": round(a.memory_usage, 2),
                "task_count": a.task_count,
                "error_rate": round(a.error_rate, 2),
                "uptime_seconds": a.uptime_seconds
            }
            for a in agents
        ]
        
        return AggregatedMetrics(
            timestamp=time.time(),
            total_agents=len(agents),
            active_agents=active_agents,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            swarm_error_rate=round(swarm_error_rate, 2),
            avg_cpu_usage=round(avg_cpu, 2),
            avg_memory_usage=round(avg_memory, 2),
            max_cpu_usage=round(max_cpu, 2),
            max_memory_usage=round(max_memory, 2),
            avg_task_duration=round(avg_task_duration, 2),
            total_uptime=total_uptime,
            agent_details=agent_details,
            health_status=health_status,
            alerts=alerts
        )
    
    def _generate_alerts(
        self,
        agents: List[AgentMetric],
        avg_cpu: float,
        avg_memory: float,
        error_rate: float,
        cpu_threshold: float,
        memory_threshold: float,
        error_threshold: float
    ) -> List[str]:
        """Generate alerts based on threshold violations."""
        alerts = []
        
        # Swarm-level alerts
        if avg_cpu > cpu_threshold:
            alerts.append(f"⚠️ High average CPU usage: {avg_cpu:.2f}%")
        
        if avg_memory > memory_threshold:
            alerts.append(f"⚠️ High average memory usage: {avg_memory:.2f}%")
        
        if error_rate > error_threshold:
            alerts.append(f"⚠️ High swarm error rate: {error_rate:.2f}%")
        
        # Agent-level alerts
        unhealthy_agents = [a for a in agents if a.status != "healthy"]
        if unhealthy_agents:
            agent_ids = ", ".join([a.agent_id for a in unhealthy_agents])
            alerts.append(f"⚠️ Unhealthy agents detected: {agent_ids}")
        
        high_cpu_agents = [a for a in agents if a.cpu_usage > cpu_threshold]
        if high_cpu_agents:
            agent_ids = ", ".join([a.agent_id for a in high_cpu_agents])
            alerts.append(f"⚠️ Agents with high CPU: {agent_ids}")
        
        high_memory_agents = [a for a in agents if a.memory_usage > memory_threshold]
        if high_memory_agents:
            agent_ids = ", ".join([a.agent_id for a in high_memory_agents])
            alerts.append(f"⚠️ Agents with high memory: {agent_ids}")
        
        return alerts
    
    def _determine_health_status(
        self,
        active_agents: int,
        total_agents: int,
        error_rate: float,
        max_cpu: float,
        max_memory: float
    ) -> str:
        """Determine overall swarm health status."""
        if active_agents == 0:
            return "CRITICAL"
        
        active_percentage = (active_agents / total_agents * 100) if total_agents > 0 else 0
        
        if active_percentage < 50 or error_rate > 20 or max_cpu > 95 or max_memory > 95:
            return "CRITICAL"
        elif active_percentage < 75 or error_rate > 10 or max_cpu > 85 or max_memory > 85:
            return "WARNING"
        else:
            return "HEALTHY"
    
    def _empty_aggregation(self) -> AggregatedMetrics:
        """Return an empty aggregation when no metrics available."""
        return AggregatedMetrics(
            timestamp=time.time(),
            total_agents=0,
            active_agents=0,
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            swarm_error_rate=0,
            avg_cpu_usage=0,
            avg_memory_usage=0,
            max_cpu_usage=0,
            max_memory_usage=0,
            avg_task_duration=0,
            total_uptime=0,
            agent_details=[],
            health_status="NO_DATA",
            alerts=[]
        )
    
    def get_agent_timeseries(self, agent_id: str) -> Dict[str, Any]:
        """Get time-series data for a specific agent."""
        metrics = self.store.get_agent_metrics(agent_id)
        
        if not metrics:
            return {"agent_id": agent_id, "data": []}
        
        timestamps = [m.timestamp for m in metrics]
        cpu_usages = [m.cpu_usage for m in metrics]
        memory_usages = [m.memory_usage for m in metrics]
        error_rates = [m.error_rate for m in metrics]
        task_counts = [m.task_count for m in metrics]
        
        return {
            "agent_id": agent_id,
            "timestamps": timestamps,
            "cpu_usages": cpu_usages,
            "memory_usages": memory_usages,
            "error_rates": error_rates,
            "task_counts": task_counts,
            "metric_count": len(metrics)
        }
    
    def get_percentile_stats(self, percentile: float = 95.0) -> Dict[str, float]:
        """Get percentile statistics across all agents."""
        latest_metrics = self.store.get_latest_metrics()
        
        if not latest_metrics:
            return {}
        
        agents = list(latest_metrics.values())
        
        cpu_usages = [a.cpu_usage for a in agents]
        memory_usages = [a.memory_usage for a in agents]
        error_rates = [a.error_rate for a in agents]
        task_durations = [a.avg_task_duration for a in agents if a.avg_task_duration > 0]
        
        return {
            "cpu_percentile": round(statistics.quantiles(cpu_usages, n=100)[int(percentile)-1], 2) if cpu_usages else 0,
            "memory_percentile": round(statistics.quantiles(memory_usages, n=100)[int(percentile)-1], 2) if memory_usages else 0,
            "error_rate_percentile": round(statistics.quantiles(error_rates, n=100)[int(percentile)-1], 2) if error_rates else 0,
            "task_duration_percentile": round(statistics.quantiles(task_durations, n=100)[int(percentile)-1], 2) if task_durations else 0,
            "percentile": percentile
        }


class MetricsSimulator:
    """Simulates agent metrics for demonstration."""
    
    def __init__(self, num_agents: int = 5):
        self.num_agents = num_agents
        self.agents = [f"agent-{i:03d}" for i in range(num_agents)]
    
    def generate_metrics(self) -> List[AgentMetric]:
        """Generate simulated metrics for all agents."""
        metrics = []
        current_time = time.time()
        
        for agent_id in self.agents:
            # Simulate realistic metric variations
            cpu_usage = random.gauss(45, 15)
            memory_usage = random.gauss(55, 12)
            cpu_usage = max(5, min(100, cpu_usage))
            memory_usage = max(10, min(100, memory_usage))
            
            task_count = random.randint(10, 100)
            failed_count = max(0, int(task_count * random.gauss(0.02, 0.01)))
            completed_count = task_count - failed_count
            
            error_rate = (failed_count / task_count * 100) if task_count > 0 else 0
            status = "healthy" if error_rate < 10 and cpu_usage < 80 else "degraded"
            
            metric = AgentMetric(
                agent_id=agent_id,
                timestamp=current_time,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                task_count=task_count,
                completed_tasks=completed_count,
                failed_tasks=failed_count,
                error_rate=error_rate,
                avg_task_duration=random.gauss(500, 100),
                uptime_seconds=random.randint(3600, 86400),
                status=status
            )
            metrics.append(metric)
        
        return metrics


def print_dashboard(aggregated: AggregatedMetrics) -> None:
    """Print a formatted dashboard view."""
    print("\n" + "="*80)
    print("🚀 SWARM HEALTH DASHBOARD".center(80))
    print("="*80)
    
    print(f"\n📊 Overall Status: {aggregated.health_status}")
    print(f"⏰ Timestamp:
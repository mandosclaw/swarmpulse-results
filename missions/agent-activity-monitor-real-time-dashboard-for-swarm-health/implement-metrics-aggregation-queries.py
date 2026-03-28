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
        
        # Sw
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:15:37.781Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Agent Activity Monitor - Real-Time Dashboard for Swarm Health
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2025-01-20
Description: Real-time monitoring dashboard tracking agent health, task throughput,
error rates, and performance metrics across the entire swarm.
"""

import argparse
import json
import time
import random
import threading
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from collections import deque
import sys


@dataclass
class AgentMetrics:
    """Individual agent metrics snapshot"""
    agent_id: str
    status: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    error_rate: float
    avg_task_duration: float
    last_heartbeat: str
    uptime_seconds: int


@dataclass
class SwarmMetrics:
    """Aggregated swarm-wide metrics"""
    timestamp: str
    total_agents: int
    active_agents: int
    healthy_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    swarm_cpu_avg: float
    swarm_memory_avg: float
    swarm_error_rate: float
    overall_health_score: float
    throughput_tasks_per_minute: float


class AgentSimulator:
    """Simulates agent activity for testing"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.status = "healthy"
        self.cpu_usage = random.uniform(10, 40)
        self.memory_usage = random.uniform(20, 60)
        self.active_tasks = random.randint(0, 8)
        self.completed_tasks = random.randint(100, 1000)
        self.failed_tasks = random.randint(0, 50)
        self.start_time = datetime.now() - timedelta(seconds=random.randint(3600, 86400))
        self.last_heartbeat = datetime.now()
        self.task_durations = deque([random.uniform(0.5, 5.0) for _ in range(10)], maxlen=100)
        
    def simulate_activity(self):
        """Simulate agent activity changes"""
        # Randomly vary metrics
        self.cpu_usage = max(5, min(95, self.cpu_usage + random.uniform(-5, 5)))
        self.memory_usage = max(10, min(95, self.memory_usage + random.uniform(-3, 3)))
        self.active_tasks = max(0, min(16, self.active_tasks + random.randint(-1, 1)))
        
        # Simulate task completion
        if random.random() < 0.7:
            self.completed_tasks += random.randint(1, 3)
            self.task_durations.append(random.uniform(0.5, 5.0))
        
        # Simulate occasional failures
        if random.random() < 0.05:
            self.failed_tasks += 1
        
        # Simulate status changes
        error_rate = self.get_error_rate()
        if error_rate > 0.15:
            self.status = "degraded"
        elif self.cpu_usage > 85 or self.memory_usage > 85:
            self.status = "degraded"
        elif error_rate > 0.05:
            self.status = "warning"
        else:
            self.status = "healthy"
        
        self.last_heartbeat = datetime.now()
    
    def get_metrics(self) -> AgentMetrics:
        """Get current agent metrics"""
        uptime = int((datetime.now() - self.start_time).total_seconds())
        error_rate = self.get_error_rate()
        avg_duration = statistics.mean(self.task_durations) if self.task_durations else 0
        
        return AgentMetrics(
            agent_id=self.agent_id,
            status=self.status,
            cpu_usage=round(self.cpu_usage, 2),
            memory_usage=round(self.memory_usage, 2),
            active_tasks=self.active_tasks,
            completed_tasks=self.completed_tasks,
            failed_tasks=self.failed_tasks,
            error_rate=round(error_rate, 4),
            avg_task_duration=round(avg_duration, 2),
            last_heartbeat=self.last_heartbeat.isoformat(),
            uptime_seconds=uptime
        )
    
    def get_error_rate(self) -> float:
        """Calculate error rate"""
        total = self.completed_tasks + self.failed_tasks
        if total == 0:
            return 0.0
        return self.failed_tasks / total


class SwarmMonitor:
    """Real-time swarm monitoring system"""
    
    def __init__(self, num_agents: int = 10, history_size: int = 100):
        self.agents: Dict[str, AgentSimulator] = {
            f"agent-{i:03d}": AgentSimulator(f"agent-{i:03d}")
            for i in range(num_agents)
        }
        self.metrics_history: deque = deque(maxlen=history_size)
        self.running = False
        self.monitor_thread = None
        self.update_interval = 2  # seconds
        
    def update_agents(self):
        """Update all agent metrics"""
        for agent in self.agents.values():
            agent.simulate_activity()
    
    def get_swarm_metrics(self) -> SwarmMetrics:
        """Calculate aggregated swarm metrics"""
        agent_metrics_list = [agent.get_metrics() for agent in self.agents.values()]
        
        total_agents = len(agent_metrics_list)
        active_agents = sum(1 for m in agent_metrics_list if m.status != "offline")
        healthy_agents = sum(1 for m in agent_metrics_list if m.status == "healthy")
        
        total_tasks = sum(m.completed_tasks + m.failed_tasks for m in agent_metrics_list)
        completed_tasks = sum(m.completed_tasks for m in agent_metrics_list)
        failed_tasks = sum(m.failed_tasks for m in agent_metrics_list)
        
        cpu_values = [m.cpu_usage for m in agent_metrics_list if m.status != "offline"]
        memory_values = [m.memory_usage for m in agent_metrics_list if m.status != "offline"]
        error_rates = [m.error_rate for m in agent_metrics_list if m.status != "offline"]
        
        swarm_cpu_avg = statistics.mean(cpu_values) if cpu_values else 0
        swarm_memory_avg = statistics.mean(memory_values) if memory_values else 0
        swarm_error_rate = statistics.mean(error_rates) if error_rates else 0
        
        # Health score: 0-100, based on agent health and error rate
        health_components = [
            (healthy_agents / total_agents) * 60,  # 60% weight: agent health
            max(0, (1 - swarm_error_rate) * 20),   # 20% weight: error rate
            max(0, (100 - swarm_cpu_avg) / 100 * 10),  # 10% weight: CPU headroom
            max(0, (100 - swarm_memory_avg) / 100 * 10)  # 10% weight: memory headroom
        ]
        overall_health_score = sum(health_components)
        
        # Calculate throughput (tasks per minute)
        if self.metrics_history:
            time_span = 60  # last 60 seconds worth of data
            recent_completed = 0
            for prev_metrics in list(self.metrics_history)[-time_span:]:
                recent_completed += prev_metrics.completed_tasks
            throughput = recent_completed / (len(list(self.metrics_history)) / 30)  # normalize to 1 minute
        else:
            throughput = 0
        
        return SwarmMetrics(
            timestamp=datetime.now().isoformat(),
            total_agents=total_agents,
            active_agents=active_agents,
            healthy_agents=healthy_agents,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            swarm_cpu_avg=round(swarm_cpu_avg, 2),
            swarm_memory_avg=round(swarm_memory_avg, 2),
            swarm_error_rate=round(swarm_error_rate, 4),
            overall_health_score=round(overall_health_score, 2),
            throughput_tasks_per_minute=round(throughput, 2)
        )
    
    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.update_agents()
                swarm_metrics = self.get_swarm_metrics()
                self.metrics_history.append(asdict(swarm_metrics))
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in monitor loop: {e}", file=sys.stderr)
    
    def start(self):
        """Start the monitoring system"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """Stop the monitoring system"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def get_dashboard_data(self, num_agents_to_show: int = None) -> Dict:
        """Get current dashboard data"""
        if not self.metrics_history:
            return {"error": "No metrics collected yet"}
        
        latest_swarm = self.metrics_history[-1]
        agent_metrics_list = [agent.get_metrics() for agent in self.agents.values()]
        
        # Sort agents by status and error rate
        agent_metrics_list.sort(
            key=lambda m: (m.status != "healthy", m.error_rate, m.cpu_usage),
            reverse=True
        )
        
        if num_agents_to_show:
            agent_metrics_list = agent_metrics_list[:num_agents_to_show]
        
        # Calculate trends
        history = list(self.metrics_history)
        health_trend = "stable"
        if len(history) >= 2:
            prev_health = history[-2].get("overall_health_score", 0)
            curr_health = history[-1].get("overall_health_score", 0)
            if curr_health > prev_health + 2:
                health_trend = "improving"
            elif curr_health < prev_health - 2:
                health_trend = "degrading"
        
        return {
            "dashboard": {
                "timestamp": latest_swarm.get("timestamp"),
                "health_trend": health_trend,
                "summary": {
                    "total_agents": latest_swarm.get("total_agents"),
                    "active_agents": latest_swarm.get("active_agents"),
                    "healthy_agents": latest_swarm.get("healthy_agents"),
                    "overall_health_score": latest_swarm.get("overall_health_score"),
                    "total_tasks": latest_swarm.get("total_tasks"),
                    "completed_tasks": latest_swarm.get("completed_tasks"),
                    "failed_tasks": latest_swarm.get("failed_tasks"),
                    "swarm_error_rate": latest_swarm.get("swarm_error_rate"),
                    "swarm_cpu_avg": latest_swarm.get("swarm_cpu_avg"),
                    "swarm_memory_avg": latest_swarm.get("swarm_memory_avg"),
                    "throughput_tasks_per_minute": latest_swarm.get("throughput_tasks_per_minute")
                },
                "agents": [asdict(m) for m in agent_metrics_list],
                "alerts": self._generate_alerts(latest_swarm, agent_metrics_list)
            }
        }
    
    def _generate_alerts(self, swarm_metrics: Dict, agent_list: List[AgentMetrics]) -> List[str]:
        """Generate alerts based on thresholds"""
        alerts = []
        
        if swarm_metrics.get("overall_health_score", 100) < 50:
            alerts.append("CRITICAL: Overall swarm health below 50%")
        
        if swarm_metrics.get("swarm_error_rate", 0) > 0.1:
            alerts.append("WARNING: Swarm error rate exceeds 10%")
        
        if swarm_metrics.get("swarm_cpu_avg", 0) > 80:
            alerts.append("WARNING: Swarm average CPU usage above 80%")
        
        if swarm_metrics.get("swarm_memory_avg", 0) > 80:
            alerts.append("WARNING: Swarm average memory usage above 80%")
        
        degraded_count = sum(1 for m in agent_list if m.status == "degraded")
        if degraded_count > len(agent_list) * 0.2:
            alerts.append(f"WARNING: {degraded_count} agents in degraded state")
        
        return alerts
    
    def get_metrics_history(self, minutes: int = 5) -> List[Dict]:
        """Get metrics history for the specified time period"""
        history = list(self.metrics_history)
        
        # Filter based on update interval
        num_samples = max(1, int(minutes * 60 / self.update_interval))
        step = max(1, len(history) // num_samples)
        
        return history[::step] if step > 1 else history


def print_dashboard(monitor: SwarmMonitor, color: bool = False):
    """Print a formatted dashboard"""
    dashboard_data = monitor.get_dashboard_data(num_agents_to_show=5)
    dashboard = dashboard_data.get("dashboard", {})
    
    # ANSI color codes
    colors = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m"
    } if color else {k: "" for k in ["reset", "bold", "green", "yellow", "red", "cyan"]}
    
    print(f"\n{colors['bold']}{'='*80}")
    print(f"SWARM HEALTH DASHBOARD - {dashboard.get('timestamp', 'N/A')}")
    print(f"{'='*80}{colors['reset']}\n")
    
    summary = dashboard.get("summary", {})
    health = summary.get("overall_health_score", 0)
    health_color = colors["green"] if health >= 75 else colors["yellow"] if health >= 50 else colors["red"]
    
    print(f"{colors['bold']}SUMMARY{colors['reset']}")
    print(f"  Health Score:        {health_color}{health}/100{colors['reset']}")
    print(f"  Health Trend:        {dashboard.get('health_trend', 'N/A')}")
    print(f"  Active Agents:       {summary.get('active_agents', 0)}/{summary.get('total_agents', 0)}")
    print(f"  Healthy Agents:      {summary.get('healthy_agents', 0)}/{summary.get('total_agents', 0)}")
    print(f"  Error Rate:          {summary.get('swarm_error_rate', 0):.2%}")
    print(f"  CPU Avg:             {summary.get('swarm_cpu_avg', 0):.1f}%")
    print(f"  Memory Avg:
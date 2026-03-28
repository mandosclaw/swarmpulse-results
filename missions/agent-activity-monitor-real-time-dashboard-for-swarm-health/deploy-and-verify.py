#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T22:02:07.845Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Deploy and verify - Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Mission: Real-time monitoring dashboard tracking agent health, task throughput, error rates, and performance metrics
Agent: @bolt
Date: 2025-01-14
"""

import argparse
import json
import time
import random
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional
import statistics


@dataclass
class AgentMetrics:
    agent_id: str
    timestamp: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    error_rate: float
    avg_task_duration: float
    uptime_seconds: int
    status: str


@dataclass
class SwarmMetrics:
    timestamp: str
    total_agents: int
    healthy_agents: int
    unhealthy_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    throughput_tasks_per_sec: float
    avg_error_rate: float
    avg_cpu_usage: float
    avg_memory_usage: float
    critical_alerts: int


class AgentHealthMonitor:
    def __init__(self, num_agents: int = 5, sample_window: int = 10):
        self.num_agents = num_agents
        self.sample_window = sample_window
        self.agent_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=sample_window))
        self.agent_states: Dict[str, dict] = {}
        self.swarm_history: deque = deque(maxlen=sample_window)
        self.alerts: List[str] = []
        self.lock = threading.Lock()
        self.cpu_threshold = 85.0
        self.memory_threshold = 80.0
        self.error_rate_threshold = 0.1
        self.task_timeout = 60
        
        self._initialize_agents()
    
    def _initialize_agents(self):
        for i in range(self.num_agents):
            agent_id = f"agent_{i:03d}"
            self.agent_states[agent_id] = {
                'uptime_seconds': random.randint(3600, 86400),
                'total_completed_tasks': random.randint(100, 1000),
                'total_failed_tasks': random.randint(5, 50),
                'active_task_start_times': {},
                'status': 'healthy'
            }
    
    def _generate_agent_metrics(self, agent_id: str) -> AgentMetrics:
        state = self.agent_states[agent_id]
        
        cpu_usage = random.gauss(35, 15)
        cpu_usage = max(0, min(100, cpu_usage))
        
        memory_usage = random.gauss(45, 12)
        memory_usage = max(0, min(100, memory_usage))
        
        active_tasks = random.randint(0, 8)
        completed_this_period = random.randint(2, 15)
        failed_this_period = random.randint(0, 2)
        
        state['total_completed_tasks'] += completed_this_period
        state['total_failed_tasks'] += failed_this_period
        state['uptime_seconds'] += 5
        
        total_tasks = state['total_completed_tasks'] + state['total_failed_tasks']
        error_rate = state['total_failed_tasks'] / total_tasks if total_tasks > 0 else 0.0
        
        avg_task_duration = random.gauss(2.5, 0.8)
        avg_task_duration = max(0.1, avg_task_duration)
        
        if cpu_usage > self.cpu_threshold:
            state['status'] = 'degraded'
        elif error_rate > self.error_rate_threshold:
            state['status'] = 'warning'
        elif cpu_usage > self.cpu_threshold * 0.9 or memory_usage > self.memory_threshold * 0.9:
            state['status'] = 'warning'
        else:
            state['status'] = 'healthy'
        
        metrics = AgentMetrics(
            agent_id=agent_id,
            timestamp=datetime.utcnow().isoformat(),
            cpu_usage=round(cpu_usage, 2),
            memory_usage=round(memory_usage, 2),
            active_tasks=active_tasks,
            completed_tasks=state['total_completed_tasks'],
            failed_tasks=state['total_failed_tasks'],
            error_rate=round(error_rate, 4),
            avg_task_duration=round(avg_task_duration, 2),
            uptime_seconds=state['uptime_seconds'],
            status=state['status']
        )
        
        return metrics
    
    def collect_metrics(self) -> None:
        with self.lock:
            for agent_id in self.agent_states.keys():
                metrics = self._generate_agent_metrics(agent_id)
                self.agent_metrics[agent_id].append(asdict(metrics))
                self._check_alerts(metrics)
    
    def _check_alerts(self, metrics: AgentMetrics) -> None:
        if metrics.cpu_usage > self.cpu_threshold:
            self.alerts.append(
                f"[CRITICAL] {metrics.agent_id} CPU usage {metrics.cpu_usage}% exceeds threshold"
            )
        
        if metrics.memory_usage > self.memory_threshold:
            self.alerts.append(
                f"[CRITICAL] {metrics.agent_id} Memory usage {metrics.memory_usage}% exceeds threshold"
            )
        
        if metrics.error_rate > self.error_rate_threshold:
            self.alerts.append(
                f"[WARNING] {metrics.agent_id} Error rate {metrics.error_rate:.2%} exceeds threshold"
            )
        
        if metrics.status == 'degraded':
            self.alerts.append(
                f"[ALERT] {metrics.agent_id} transitioned to DEGRADED state"
            )
    
    def get_swarm_metrics(self) -> SwarmMetrics:
        with self.lock:
            if not self.agent_metrics:
                return None
            
            latest_metrics = {}
            for agent_id, metrics_history in self.agent_metrics.items():
                if metrics_history:
                    latest_metrics[agent_id] = metrics_history[-1]
            
            if not latest_metrics:
                return None
            
            healthy_count = sum(1 for m in latest_metrics.values() if m['status'] == 'healthy')
            unhealthy_count = len(latest_metrics) - healthy_count
            
            total_completed = sum(m['completed_tasks'] for m in latest_metrics.values())
            total_failed = sum(m['failed_tasks'] for m in latest_metrics.values())
            total_tasks = total_completed + total_failed
            
            cpu_usages = [m['cpu_usage'] for m in latest_metrics.values()]
            memory_usages = [m['memory_usage'] for m in latest_metrics.values()]
            error_rates = [m['error_rate'] for m in latest_metrics.values()]
            
            throughput = sum(m['completed_tasks'] for m in latest_metrics.values()) / 5.0
            
            critical_alerts = sum(1 for a in self.alerts if '[CRITICAL]' in a)
            
            swarm_metrics = SwarmMetrics(
                timestamp=datetime.utcnow().isoformat(),
                total_agents=len(latest_metrics),
                healthy_agents=healthy_count,
                unhealthy_agents=unhealthy_count,
                total_tasks=total_tasks,
                completed
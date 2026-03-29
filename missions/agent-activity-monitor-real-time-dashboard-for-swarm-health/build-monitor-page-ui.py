#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build monitor page UI
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:15:13.667Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build monitor page UI
MISSION: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire swarm.
"""

import argparse
import json
import time
import random
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum


class AgentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class AgentMetric:
    agent_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    task_count: int
    completed_tasks: int
    failed_tasks: int
    avg_response_time_ms: float
    error_rate: float
    status: str
    uptime_seconds: float
    last_heartbeat: float


@dataclass
class SwarmMetric:
    timestamp: float
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    unhealthy_agents: int
    offline_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_throughput_tasks_per_sec: float
    overall_error_rate: float
    avg_cpu_usage: float
    avg_memory_usage: float


class AgentActivityMonitor:
    def __init__(self, window_size: int = 300, threshold_cpu: float = 80.0,
                 threshold_memory: float = 85.0, threshold_error_rate: float = 10.0,
                 heartbeat_timeout: float = 30.0):
        self.window_size = window_size
        self.threshold_cpu = threshold_cpu
        self.threshold_memory = threshold_memory
        self.threshold_error_rate = threshold_error_rate
        self.heartbeat_timeout = heartbeat_timeout
        
        self.agents: Dict[str, Dict] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.swarm_history: deque = deque(maxlen=window_size)
        self.lock = threading.RLock()
        self.running = False
        self.monitor_thread = None
        
    def update_agent_metric(self, metric: AgentMetric) -> None:
        with self.lock:
            agent_id = metric.agent_id
            
            if agent_id not in self.agents:
                self.agents[agent_id] = {
                    'created_at': time.time(),
                    'total_tasks_processed': 0,
                    'total_tasks_failed': 0
                }
            
            status = self._determine_agent_status(metric)
            metric.status = status.value
            
            self.agents[agent_id]['last_metric'] = metric
            self.agents[agent_id]['total_tasks_processed'] += metric.completed_tasks
            self.agents[agent_id]['total_tasks_failed'] += metric.failed_tasks
            
            self.metrics_history[agent_id].append(asdict(metric))
    
    def _determine_agent_status(self, metric: AgentMetric) -> AgentStatus:
        current_time = time.time()
        heartbeat_age = current_time - metric.last_heartbeat
        
        if heartbeat_age > self.heartbeat_timeout:
            return AgentStatus.OFFLINE
        
        issues = 0
        if metric.cpu_usage > self.threshold_cpu:
            issues += 1
        if metric.memory_usage > self.threshold_memory:
            issues += 1
        if metric.error_rate > self.threshold_error_rate:
            issues += 1
        
        if issues >= 2:
            return AgentStatus.UNHEALTHY
        elif issues == 1:
            return AgentStatus.DEGRADED
        
        return AgentStatus.HEALTHY
    
    def compute_swarm_metrics(self) -> SwarmMetric:
        with self.lock:
            if not self.agents:
                return SwarmMetric(
                    timestamp=time.time(),
                    total_agents=0,
                    healthy_agents=0,
                    degraded_agents=0,
                    unhealthy_agents=0,
                    offline_agents=0,
                    total_tasks=0,
                    completed_tasks=0,
                    failed_tasks=0,
                    avg_throughput_tasks_per_sec=0.0,
                    overall_error_rate=0.0,
                    avg_cpu_usage=0.0,
                    avg_memory_usage=0.0
                )
            
            status_counts = defaultdict(int)
            total_cpu = 0.0
            total_memory = 0.0
            total_completed = 0
            total_failed = 0
            total_active_tasks = 0
            response_times = []
            
            current_time = time.time()
            
            for agent_id, agent_data in self.agents.items():
                if 'last_metric' not in agent_data:
                    continue
                
                metric = agent_data['last_metric']
                status = AgentStatus(metric.status)
                status_counts[status] += 1
                
                total_cpu += metric.cpu_usage
                total_memory += metric.memory_usage
                total_completed += metric.completed_tasks
                total_failed += metric.failed_tasks
                total_active_tasks += metric.task_count
                response_times.append(metric.avg_response_time_ms)
            
            agent_count = len([a for a in self.agents.values() if 'last_metric' in a])
            
            if agent_count == 0:
                avg_cpu = 0.0
                avg_memory = 0.0
                overall_error_rate = 0.0
                avg_throughput = 0.0
            else:
                avg_cpu = total_cpu / agent_count
                avg_memory = total_memory / agent_count
                total_tasks = total_completed + total_failed
                overall_error_rate = (total_failed / total_tasks * 100) if total_tasks > 0 else 0.0
                
                time_window = self.window_size if len(self.swarm_history) == self.window_size else 1
                avg_throughput = (total_completed / time_window) if time_window > 0 else 0.0
            
            swarm_metric = SwarmMetric(
                timestamp=current_time,
                total_agents=len(self.agents),
                healthy_agents=status_counts.get(AgentStatus.HEALTHY, 0),
                degraded_agents=status_counts.get(AgentStatus.DEGRADED, 0),
                unhealthy_agents=status_counts.get(AgentStatus.UNHEALTHY, 0),
                offline_agents=status_counts.get(AgentStatus.OFFLINE, 0),
                total_tasks=total_active_tasks,
                completed_tasks=total_completed,
                failed_tasks=total_failed,
                avg_throughput_tasks_per_sec=avg_throughput,
                overall_error_rate=overall_error_rate,
                avg_cpu_usage=avg_cpu,
                avg_memory_usage=avg_memory
            )
            
            self.swarm_history.append(asdict(swarm_metric))
            return swarm_metric
    
    def get_dashboard_data(self) -> Dict:
        with self.lock:
            swarm_metric = self.compute_swarm_metrics()
            
            agents_data = []
            for agent_id, agent_data in self.agents.items():
                if 'last_metric' in agent_data:
                    metric = agent_data['last_metric']
                    agents_data.append({
                        'agent_id': agent_id,
                        'status': metric.status,
                        'cpu_usage': round(metric.cpu_usage, 2),
                        'memory_usage': round(metric.memory_usage, 2),
                        'active_tasks': metric.task_count,
                        'completed_tasks': metric.completed_tasks,
                        'failed_tasks': metric.failed_tasks,
                        'avg_response_time_ms': round(metric.avg_response_time_ms, 2),
                        'error_rate': round(metric.error_rate, 2),
                        'uptime_seconds': round(metric.uptime_seconds, 0),
                        'timestamp': datetime.fromtimestamp(metric.timestamp).isoformat()
                    })
            
            agents_data.sort(key=lambda x: (
                {'healthy': 0, 'degraded': 1, 'unhealthy': 2, 'offline': 3}.get(x['status'], 4),
                x['agent_id']
            ))
            
            return {
                'timestamp': datetime.fromtimestamp(swarm_metric.timestamp).isoformat(),
                'swarm_health': {
                    'total_agents': swarm_metric.total_agents,
                    'healthy_agents': swarm_metric.healthy_agents,
                    'degraded_agents': swarm_metric.degraded_agents,
                    'unhealthy_agents': swarm_metric.unhealthy_agents,
                    'offline_agents': swarm_metric.offline_agents,
                    'health_percentage': round(
                        (swarm_metric.healthy_agents / swarm_metric.total_agents * 100)
                        if swarm_metric.total_agents > 0 else 0, 2
                    )
                },
                'task_metrics': {
                    'total_tasks': swarm_metric.total_tasks,
                    'completed_tasks': swarm_metric.completed_tasks,
                    'failed_tasks': swarm_metric.failed_tasks,
                    'success_rate': round(
                        (swarm_metric.completed_tasks / (swarm_metric.completed_tasks + swarm_metric.failed_tasks) * 100)
                        if (swarm_metric.completed_tasks + swarm_metric.failed_tasks) > 0 else 0, 2
                    ),
                    'avg_throughput_tasks_per_sec': round(swarm_metric.avg_throughput_tasks_per_sec, 2),
                    'overall_error_rate': round(swarm_metric.overall_error_rate, 2)
                },
                'resource_metrics': {
                    'avg_cpu_usage': round(swarm_metric.avg_cpu_usage, 2),
                    'avg_memory_usage': round(swarm_metric.avg_memory_usage, 2)
                },
                'agents': agents_data
            }
    
    def render_text_dashboard(self) -> str:
        data = self.get_dashboard_data()
        
        lines = []
        lines.append("\n" + "=" * 100)
        lines.append(f"SwarmPulse Agent Activity Monitor | {data['timestamp']}")
        lines.append("=" * 100)
        
        # Swarm Health
        swarm = data['swarm_health']
        lines.append(f"\n📊 SWARM HEALTH")
        lines.append(f"  Total Agents: {swarm['total_agents']} | "
                    f"Healthy: {swarm['healthy_agents']} | "
                    f"Degraded: {swarm['degraded_agents']} | "
                    f"Unhealthy: {swarm['unhealthy_agents']} | "
                    f"Offline: {swarm['offline_agents']}")
        health_bar = self._create_health_bar(swarm['health_percentage'])
        lines.append(f"  Health: {health_bar} {swarm['health_percentage']:.1f}%")
        
        # Task Metrics
        tasks = data['task_metrics']
        lines.append(f"\n📈 TASK METRICS")
        lines.append(f"  Completed: {tasks['completed_tasks']} | "
                    f"Failed: {tasks['failed_tasks']} | "
                    f"Active: {tasks['total_tasks']}")
        lines.append(f"  Success Rate: {tasks['success_rate']:.2f}% | "
                    f"Error Rate: {tasks['overall_error_rate']:.2f}%")
        lines.append(f"  Throughput: {tasks['avg_throughput_tasks_per_sec']:.2f} tasks/sec")
        
        # Resource Metrics
        resources = data['resource_metrics']
        lines.append(f"\n💾 RESOURCE METRICS")
        lines.append(f"  Avg CPU: {resources['avg_cpu_usage']:.2f}% | "
                    f"Avg Memory: {resources['avg_memory_usage']:.2f}%")
        
        # Top Agents Table
        if data['agents']:
            lines.append(f"\n📋 TOP AGENTS (by status)")
            lines.append("-" * 100)
            lines.append(f"{'Agent ID':<20} {'Status':<12} {'CPU':<8} {'Memory':<8} "
                        f"{'Tasks':<8} {'Error%':<8} {'Response(ms)':<12}")
            lines.append("-" * 100)
            
            for agent in data['agents'][:15]:
                status_icon = {
                    'healthy': '✓',
                    'degraded': '⚠',
                    'unhealthy': '✗',
                    'offline': '○'
                }.get(agent['status'], '?')
                
                lines.append(
                    f"{agent['agent_id']:<20} "
                    f"{status_icon} {agent['status']:<10} "
                    f"{agent['cpu_usage']:>6.1f}% "
                    f"{agent['memory_usage']:>6.1f}% "
                    f"{agent['active_tasks']:>6} "
                    f"{agent['error_rate']:>6.1f}% "
                    f"{agent['avg_response_time_ms']:>10.2f}ms"
                )
        
        lines.append("=" * 100 + "\n")
        return "\n".join(lines)
    
    def _create_health_bar(self, percentage: float, width: int = 20) -> str:
        filled = int(width * percentage / 100)
        empty = width - filled
        
        color_start = "\033[92m" if percentage >= 80 else "\033[93m" if percentage >= 50 else "\033[91m"
        color_end = "\033[0m"
        
        return f"{color_start}[{'█' * filled}{'░' * empty}]{color_end}"
    
    def get_alerts(self) -> List[Dict]:
        with self.lock:
            alerts = []
            
            for agent_id, agent_data in self.agents.items():
                if 'last_metric' not in agent_data:
                    continue
                
                metric = agent_data['last_metric']
                current_time = time.time()
                
                if current_time - metric.last_heartbeat > self.heartbeat_timeout:
                    alerts.append({
                        'severity': 'critical',
                        'agent_id': agent_id,
                        'message': f'Agent offline for {current_time - metric.last_heartbeat:.0f}s',
                        'timestamp': datetime.fromtimestamp(current_time).isoformat()
                    })
                elif metric.cpu_usage > self.threshold_cpu:
                    alerts.append({
                        'severity': 'warning',
                        'agent_id': agent_id,
                        'message': f'CPU usage high: {metric.cpu_usage:.1f}%',
                        'timestamp': datetime.fromtimestamp(metric.timestamp).isoformat()
                    })
                
                if metric.memory_usage >
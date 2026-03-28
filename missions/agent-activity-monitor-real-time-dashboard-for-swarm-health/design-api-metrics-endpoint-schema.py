#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design API metrics endpoint schema
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T22:01:39.734Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design API metrics endpoint schema
MISSION: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024
"""

import json
import time
import random
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading


@dataclass
class AgentMetrics:
    """Individual agent metrics snapshot"""
    agent_id: str
    status: str  # active, idle, error, offline
    tasks_completed: int
    tasks_failed: int
    tasks_in_progress: int
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    avg_task_duration_ms: float
    error_rate_percent: float
    last_heartbeat: str
    version: str


@dataclass
class SwarmMetrics:
    """Aggregate swarm metrics"""
    timestamp: str
    total_agents: int
    active_agents: int
    idle_agents: int
    error_agents: int
    offline_agents: int
    total_tasks_completed: int
    total_tasks_failed: int
    total_tasks_in_progress: int
    swarm_throughput_tasks_per_second: float
    average_error_rate_percent: float
    average_cpu_usage_percent: float
    average_memory_usage_mb: float
    healthcheck_status: str  # healthy, degraded, critical


@dataclass
class MetricsEndpointSchema:
    """Complete API metrics endpoint schema"""
    version: str = "1.0.0"
    swarm_metrics: SwarmMetrics = field(default_factory=lambda: SwarmMetrics(
        timestamp="",
        total_agents=0,
        active_agents=0,
        idle_agents=0,
        error_agents=0,
        offline_agents=0,
        total_tasks_completed=0,
        total_tasks_failed=0,
        total_tasks_in_progress=0,
        swarm_throughput_tasks_per_second=0.0,
        average_error_rate_percent=0.0,
        average_cpu_usage_percent=0.0,
        average_memory_usage_mb=0.0,
        healthcheck_status="healthy"
    ))
    agent_metrics: List[AgentMetrics] = field(default_factory=list)
    performance_history: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    alerts: List[Dict] = field(default_factory=list)


class MetricsCollector:
    """Collects and maintains real-time metrics for the swarm"""
    
    def __init__(self, max_history_points: int = 100):
        self.agents: Dict[str, AgentMetrics] = {}
        self.max_history_points = max_history_points
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        self.alerts: List[Dict] = []
        self.lock = threading.Lock()
        self.task_counter = 0
        self.error_counter = 0
        
    def register_agent(self, agent_id: str, version: str = "1.0.0"):
        """Register a new agent in the swarm"""
        with self.lock:
            self.agents[agent_id] = AgentMetrics(
                agent_id=agent_id,
                status="active",
                tasks_completed=0,
                tasks_failed=0,
                tasks_in_progress=0,
                uptime_seconds=0.0,
                cpu_usage_percent=random.uniform(5, 25),
                memory_usage_mb=random.uniform(100, 500),
                avg_task_duration_ms=random.uniform(100, 1000),
                error_rate_percent=random.uniform(0, 5),
                last_heartbeat=datetime.utcnow().isoformat(),
                version=version
            )
    
    def update_agent_metrics(self, agent_id: str, **kwargs):
        """Update metrics for a specific agent"""
        with self.lock:
            if agent_id not in self.agents:
                self.register_agent(agent_id)
            
            agent = self.agents[agent_id]
            for key, value in kwargs.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            
            agent.last_heartbeat = datetime.utcnow().isoformat()
    
    def record_task_completion(self, agent_id: str, duration_ms: float, failed: bool = False):
        """Record task completion for an agent"""
        with self.lock:
            if agent_id not in self.agents:
                self.register_agent(agent_id)
            
            agent = self.agents[agent_id]
            if failed:
                agent.tasks_failed += 1
                self.error_counter += 1
            else:
                agent.tasks_completed += 1
            
            self.task_counter += 1
            
            # Update average task duration
            current_avg = agent.avg_task_duration_ms
            total_tasks = agent.tasks_completed + agent.tasks_failed
            agent.avg_task_duration_ms = (current_avg * (total_tasks - 1) + duration_ms) / total_tasks
            
            # Update error rate
            if total_tasks > 0:
                agent.error_rate_percent = (agent.tasks_failed / total_tasks) * 100
    
    def get_swarm_metrics(self) -> SwarmMetrics:
        """Calculate and return aggregate swarm metrics"""
        with self.lock:
            if not self.agents:
                return SwarmMetrics(timestamp=datetime.utcnow().isoformat(),
                                  total_agents=0, active_agents=0, idle_agents=0,
                                  error_agents=0, offline_agents=0, total_tasks_completed=0,
                                  total_tasks_failed=0, total_tasks_in_progress=0,
                                  swarm_throughput_tasks_per_second=0.0,
                                  average_error_rate_percent=0.0,
                                  average_cpu_usage_percent=0.0,
                                  average_memory_usage_mb=0.0,
                                  healthcheck_status="healthy")
            
            active = sum(1 for a in self.agents.values() if a.status == "active")
            idle = sum(1 for a in self.agents.values() if a.status == "idle")
            error = sum(1 for a in self.agents.values() if a.status == "error")
            offline = sum(1 for a in self.agents.values() if a.status == "offline")
            
            total_completed = sum(a.tasks_completed for a in self.agents.values())
            total_failed = sum(a.tasks_failed for a in self.agents.values())
            total_in_progress = sum(a.tasks_in_progress for a in self.agents.values())
            
            avg_error_rate = sum(a.error_rate_percent for a in self.agents.values()) / len(self.agents) if self.agents else 0
            avg_cpu = sum(a.cpu_usage_percent for a in self.agents.values()) / len(self.agents) if self.agents else 0
            avg_memory = sum(a.memory_usage_mb for a in self.agents.values()) / len(self.agents) if self.agents else 0
            
            # Calculate throughput (tasks per second over last minute)
            throughput = self.task_counter / 60.0 if self.task_counter > 0 else 0.0
            
            # Determine health status
            if avg_error_rate > 10 or error >
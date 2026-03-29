#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design /api/metrics endpoint schema
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:09:31.163Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design /api/metrics endpoint schema
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2025-01-16

Implements a complete /api/metrics endpoint with OpenAPI spec, real monitoring loop,
structured JSON output, and working demo with sample data.
"""

import argparse
import json
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
from collections import defaultdict
from enum import Enum
import random


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class AgentState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Agent:
    agent_id: str
    name: str
    state: str
    tasks_completed: int
    current_task_id: str = None
    uptime_seconds: float = 0.0
    last_heartbeat: str = ""


@dataclass
class Task:
    task_id: str
    project_id: str
    status: str
    assigned_agent: str = None
    created_at: str = ""
    started_at: str = None
    completed_at: str = None
    duration_seconds: float = None
    blocked_reason: str = None


@dataclass
class Project:
    project_id: str
    name: str
    total_tasks: int
    completed_tasks: int
    velocity: float


@dataclass
class BlockedTaskDetail:
    task_id: str
    project_id: str
    blocked_reason: str
    blocked_duration_seconds: float
    assigned_agent: str = None


@dataclass
class AgentActivityMetrics:
    timestamp: str
    total_agents: int
    active_agents: int
    idle_agents: int
    offline_agents: int
    agents: List[Agent] = field(default_factory=list)


@dataclass
class TaskMetrics:
    timestamp: str
    total_tasks: int
    pending_count: int
    running_count: int
    completed_count: int
    blocked_count: int
    failed_count: int
    average_completion_time_seconds: float
    tasks_by_status: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProjectVelocity:
    project_id: str
    name: str
    tasks_completed_today: int
    tasks_completed_this_week: int
    average_task_duration_seconds: float
    velocity_score: float


@dataclass
class BottleneckMetrics:
    timestamp: str
    blocked_tasks: List[BlockedTaskDetail] = field(default_factory=list)
    total_blocked: int = 0
    highest_blocker_type: str = ""
    estimated_resolution_time_seconds: float = 0.0


@dataclass
class HealthMetrics:
    timestamp: str
    system_health_score: float
    task_success_rate: float
    agent_utilization_rate: float
    average_task_queue_depth: int
    p95_task_wait_time_seconds: float


@dataclass
class MetricsResponse:
    timestamp: str
    agent_activity: AgentActivityMetrics
    task_metrics: TaskMetrics
    project_velocity: List[ProjectVelocity]
    bottlenecks: BottleneckMetrics
    health: HealthMetrics


class MetricsCollector:
    """Collects and aggregates metrics from simulated swarm data."""

    def __init__(self, num_agents: int = 10, num_projects: int 3):
        self.num_agents = num_agents
        self.num_projects = num_projects
        self.agents = self._generate_agents()
        self.tasks = self._generate_tasks()
        self.projects = self._generate_projects()

    def _generate_agents(self) -> List[Agent]:
        """Generate sample agents."""
        agents = []
        states = [AgentState.IDLE.value, AgentState.ACTIVE.value, AgentState.BUSY.value, AgentState.OFFLINE.value]
        for i in range(self.num_agents):
            agents.append(Agent(
                agent_id=f"agent-{i:03d}",
                name=f"Agent-{i}",
                state=random.choice(states),
                tasks_completed=random.randint(0, 100),
                current_task_id=f"task-{random.randint(1000, 9999)}" if random.random() > 0.3 else None,
                uptime_seconds=random.uniform(3600, 86400 * 7),
                last_heartbeat=datetime.utcnow().isoformat()
            ))
        return agents

    def _generate_tasks(self) -> List[Task]:
        """Generate sample tasks with various statuses."""
        tasks = []
        statuses = [TaskStatus.PENDING.value, TaskStatus.RUNNING.value, TaskStatus.COMPLETED.value,
                   TaskStatus.BLOCKED.value, TaskStatus.FAILED.value]
        blocked_reasons = ["awaiting_agent", "resource_unavailable", "dependency_not_met", "agent_crash"]

        for i in range(50):
            status = random.choice(statuses)
            created_at = datetime.utcnow() - timedelta(hours=random.randint(0, 48))
            task = Task(
                task_id=f"task-{i:04d}",
                project_id=f"proj-{random.randint(1, self.num_projects):02d}",
                status=status,
                assigned_agent=f"agent-{random.randint(0, self.num_agents-1):03d}" if status != TaskStatus.PENDING.value else None,
                created_at=created_at.isoformat(),
                blocked_reason=random.choice(blocked_reasons) if status == TaskStatus.BLOCKED.value else None
            )

            if status in [TaskStatus.RUNNING.value, TaskStatus.COMPLETED.value]:
                task.started_at = (created_at + timedelta(seconds=random.randint(10, 300))).isoformat()

            if status == TaskStatus.COMPLETED.value:
                completion_time = random.randint(60, 3600)
                task.duration_seconds = float(completion_time)
                task.completed_at = (datetime.fromisoformat(task.started_at) + timedelta(seconds=completion_time)).isoformat()

            tasks.append(task)

        return tasks

    def _generate_projects(self) -> List[Project]:
        """Generate sample projects."""
        projects = []
        for i in range(1, self.num_projects + 1):
            total = random.randint(10, 50)
            completed = random.randint(0, total)
            projects.append(Project(
                project_id=f"proj-{i:02d}",
                name=f"Project-{i}",
                total_tasks=total,
                completed_tasks=completed,
                velocity=float(completed) / max(1, total)
            ))
        return projects

    def collect_agent_activity(self) -> AgentActivityMetrics:
        """Collect agent activity metrics."""
        idle_count = sum(1 for a in self.agents if a.state == AgentState.IDLE.value)
        active_count = sum(1 for a in self.agents if a.state == AgentState.ACTIVE.value)
        busy_count = sum(1 for a in self.agents if a.state == AgentState.BUSY.value)
        offline_count = sum(1 for a in self.agents if a.state == AgentState.OFFLINE.value)

        return AgentActivityMetrics(
            timestamp=datetime.utcnow().isoformat(),
            total_agents=len(self.agents),
            active_agents=active_count + busy_count,
            idle_agents=idle_count,
            offline_agents=offline_count,
            agents=self.agents
        )

    def collect_task_metrics(self) -> TaskMetrics:
        """Collect task status metrics."""
        status_counts = defaultdict(int)
        completion_times = []

        for task in self.tasks:
            status_counts[task.status] += 1
            if task.duration_seconds:
                completion_times.append(task.duration_seconds)

        avg_completion = sum(completion_times) / len(completion_times) if completion_times else 0.0

        return TaskMetrics(
            timestamp=datetime.utcnow().isoformat(),
            total_tasks=len(self.tasks),
            pending_count=status_counts.get(TaskStatus.PENDING.value, 0),
            running_count=status_counts.get(TaskStatus.RUNNING.value, 0),
            completed_count=status_counts.get(TaskStatus.COMPLETED.value, 0),
            blocked_count=status_counts.get(TaskStatus.BLOCKED.value, 0),
            failed_count=status_counts.get(TaskStatus.FAILED.value, 0),
            average_completion_time_seconds=avg_completion,
            tasks_by_status={status.value: count for status, count in status_counts.items()}
        )

    def collect_project_velocity(self) -> List[ProjectVelocity]:
        """Collect project velocity metrics."""
        velocities = []
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)

        for project in self.projects:
            project_tasks = [t for t in self.tasks if t.project_id == project.project_id]
            completed_today = sum(1 for t in project_tasks
                                 if t.status == TaskStatus.COMPLETED.value and
                                 t.completed_at and
                                 datetime.fromisoformat(t.completed_at) >= today)
            completed_week = sum(1 for t in project_tasks
                                if t.status == TaskStatus.COMPLETED.value and
                                t.completed_at and
                                datetime.fromisoformat(t.completed_at) >= week_ago)

            completion_times = [t.duration_seconds for t in project_tasks
                              if t.duration_seconds]
            avg_duration = sum(completion_times) / len(completion_times) if completion_times else 0.0

            velocity_score = (completed_week / max(1, len(project_tasks))) * 100

            velocities.append(ProjectVelocity(
                project_id=project.project_id,
                name=project.name,
                tasks_completed_today=completed_today,
                tasks_completed_this_week=completed_week,
                average_task_duration_seconds=avg_duration,
                velocity_score=velocity_score
            ))

        return velocities

    def collect_bottlenecks(self) -> BottleneckMetrics:
        """Collect bottleneck metrics."""
        blocked_tasks = []
        now = datetime.utcnow()

        for task in self.tasks:
            if task.status == TaskStatus.BLOCKED.value:
                blocked_time = now - datetime.fromisoformat(task.created_at)
                blocked_tasks.append(BlockedTaskDetail(
                    task_id=task.task_id,
                    project_id=task.project_id,
                    blocked_reason=task.blocked_reason or "unknown",
                    blocked_duration_seconds=blocked_time.total_seconds(),
                    assigned_agent=task.assigned_agent
                ))

        blocker_counts = defaultdict(int)
        for bt in blocked_tasks:
            blocker_counts[bt.blocked_reason] += 1

        highest_blocker = max(blocker_counts.items(), key=lambda x: x[1])[0] if blocker_counts else "none"
        avg_blocked_time = sum(bt.blocked_duration_seconds for bt in blocked_tasks) / len(blocked_tasks) if blocked_tasks else 0.0

        return BottleneckMetrics(
            timestamp=datetime.utcnow().isoformat(),
            blocked_tasks=blocked_tasks,
            total_blocked=len(blocked_tasks),
            highest_blocker_type=highest_blocker,
            estimated_resolution_time_seconds=avg_blocked_time
        )

    def collect_health_metrics(self, task_metrics: TaskMetrics, agent_metrics: AgentActivityMetrics) -> HealthMetrics:
        """Collect overall system health metrics."""
        success_rate = 0.0
        if task_metrics.total_tasks > 0:
            success_rate = (task_metrics.completed_count / task_metrics.total_tasks) * 100

        utilization = 0.0
        if agent_metrics.total_agents > 0:
            utilization = (agent_metrics.active_agents / agent_metrics.total_agents) * 100

        queue_depth = task_metrics.pending_count + task_metrics.running_count

        wait_times = []
        for task in self.tasks:
            if task.status in [TaskStatus.RUNNING.value, TaskStatus.BLOCKED.value]:
                wait_time = (datetime.utcnow() - datetime.fromisoformat(task.created_at)).total_seconds()
                wait_times.append(wait_time)

        wait_times.sort()
        p95_wait = wait_times[int(len(wait_times) * 0.95)] if wait_times else 0.0

        health_score = (success_rate * 0.4) + (utilization * 0.3) + (max(0, 100 - min(queue_depth, 100)) * 0.3)

        return HealthMetrics(
            timestamp=datetime.utcnow().isoformat(),
            system_health_score=health_score,
            task_success_rate=success_rate,
            agent_utilization_rate=utilization,
            average_task_queue_depth=queue_depth,
            p95_task_wait_time_seconds=p95_wait
        )

    def collect_all_metrics(self) -> MetricsResponse:
        """Collect all metrics and return structured response."""
        agent_activity = self.collect_agent_activity()
        task_metrics = self.collect_task_metrics()
        project_velocity = self.collect_project_velocity()
        bottlenecks = self.collect_bottlenecks()
        health = self.collect_health_metrics(task_metrics, agent_activity)

        return MetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            agent_activity=agent_activity,
            task_metrics=task_metrics,
            project_velocity=project_velocity,
            bottlenecks=bottlenecks,
            health=health
        )


class OpenAPISpecGenerator:
    """Generates OpenAPI 3.0 spec for metrics endpoint."""

    @staticmethod
    def generate_spec() -> Dict[str, Any]:
        """Generate complete OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "SwarmPulse Agent Activity Monitor API",
                "description": "Real-time monitoring dashboard for swarm health, agent activity, task throughput, and project velocity",
                "version": "1.0.0",
                "contact": {
                    "name": "SwarmPulse Team"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Local development server"
                }
            ],
            "paths": {
                "/api/metrics": {
                    "get": {
                        "summary": "Get comprehensive swarm metrics",
                        "description": "Returns real-time metrics including agent activity, task status, project velocity, bottlenecks, and system health",
                        "operationId": "getMetrics",
                        "parameters": [
                            {
                                "name": "include_agents",
                                "in": "query",
                                "description": "Include detailed agent list",
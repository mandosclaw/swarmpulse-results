#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design /api/metrics endpoint schema
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:39:00.789Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design /api/metrics endpoint schema
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024-01-15

Real-time metrics endpoint for SwarmPulse agent activity monitoring.
Provides comprehensive schema for agent health, task throughput, project velocity,
and blocked task identification.
"""

import json
import time
import random
import argparse
import threading
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class TaskStatus(Enum):
    """Task status enumeration for standardized reporting."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    IDLE = "idle"


@dataclass
class AgentMetric:
    """Individual agent activity metric."""
    agent_id: str
    name: str
    status: str
    uptime_seconds: int
    tasks_completed: int
    tasks_in_progress: int
    cpu_usage_percent: float
    memory_usage_mb: float
    last_heartbeat: str
    error_count: int = 0
    queue_length: int = 0


@dataclass
class TaskMetric:
    """Task status and count metric."""
    status: str
    count: int
    percentage: float


@dataclass
class BlockedTask:
    """Blocked task with details."""
    task_id: str
    project_id: str
    assigned_agent_id: str
    blocked_reason: str
    blocked_duration_seconds: int
    blocked_since: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ProjectVelocity:
    """Project velocity metrics."""
    project_id: str
    name: str
    tasks_completed_today: int
    tasks_completed_week: int
    tasks_completed_month: int
    avg_completion_time_seconds: float
    current_sprint_capacity: int
    current_sprint_used: int
    bottleneck_description: Optional[str] = None


@dataclass
class SystemHealth:
    """Overall system health metrics."""
    timestamp: str
    total_agents: int
    active_agents: int
    idle_agents: int
    total_tasks: int
    pending_tasks: int
    blocked_tasks: int
    failed_tasks: int
    system_uptime_seconds: int
    avg_agent_cpu_percent: float
    avg_agent_memory_mb: float
    p95_task_completion_time_seconds: float
    p99_task_completion_time_seconds: float


@dataclass
class MetricsResponse:
    """Complete metrics API response schema."""
    status: str
    timestamp: str
    query_time_ms: float
    system_health: SystemHealth
    agents: List[AgentMetric]
    task_distribution: List[TaskMetric]
    blocked_tasks: List[BlockedTask]
    project_velocity: List[ProjectVelocity]
    top_bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]


class MetricsCollector:
    """Collects and aggregates SwarmPulse metrics in real-time."""

    def __init__(self, enable_demo_data: bool = True):
        """Initialize metrics collector."""
        self.enable_demo_data = enable_demo_data
        self.start_time = time.time()
        self.agents: Dict[str, AgentMetric] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.blocked_tasks: Dict[str, BlockedTask] = {}
        self.projects: Dict[str, ProjectVelocity] = {}
        self.completion_times: List[float] = []
        self.lock = threading.Lock()

        if enable_demo_data:
            self._initialize_demo_data()

    def _initialize_demo_data(self) -> None:
        """Initialize with realistic demo data."""
        agent_names = [
            "alpha-processor", "beta-worker", "gamma-compute",
            "delta-task", "epsilon-executor", "zeta-agent"
        ]
        
        for i, name in enumerate(agent_names):
            agent_id = f"agent-{i:03d}"
            self.agents[agent_id] = AgentMetric(
                agent_id=agent_id,
                name=name,
                status="active" if i < 5 else "idle",
                uptime_seconds=random.randint(3600, 604800),
                tasks_completed=random.randint(10, 500),
                tasks_in_progress=random.randint(0, 5),
                cpu_usage_percent=round(random.uniform(5, 95), 2),
                memory_usage_mb=round(random.uniform(100, 1024), 2),
                last_heartbeat=datetime.utcnow().isoformat() + "Z",
                error_count=random.randint(0, 10),
                queue_length=random.randint(0, 20)
            )

        self.completion_times = [
            random.uniform(5, 300) for _ in range(100)
        ]

        project_ids = ["proj-001", "proj-002", "proj-003"]
        for proj_id in project_ids:
            self.projects[proj_id] = ProjectVelocity(
                project_id=proj_id,
                name=f"Project {proj_id.split('-')[1]}",
                tasks_completed_today=random.randint(5, 50),
                tasks_completed_week=random.randint(30, 300),
                tasks_completed_month=random.randint(100, 1000),
                avg_completion_time_seconds=round(random.uniform(30, 180), 2),
                current_sprint_capacity=100,
                current_sprint_used=random.randint(40, 95),
                bottleneck_description=random.choice([
                    None,
                    "Waiting for external API response",
                    "Limited worker pool capacity"
                ])
            )

        blocked_reason_list = [
            "Awaiting dependency completion",
            "Resource unavailable",
            "External service timeout",
            "Insufficient quota"
        ]
        
        for i in range(3):
            task_id = f"task-blocked-{i:04d}"
            self.blocked_tasks[task_id] = BlockedTask(
                task_id=task_id,
                project_id=random.choice(project_ids),
                assigned_agent_id=random.choice(list(self.agents.keys())),
                blocked_reason=random.choice(blocked_reason_list),
                blocked_duration_seconds=random.randint(60, 7200),
                blocked_since=(
                    datetime.utcnow() - 
                    timedelta(seconds=random.randint(60, 7200))
                ).isoformat() + "Z",
                dependencies=[f"task-{j:04d}" for j in range(random.randint(1, 3))]
            )

        total_tasks = random.randint(500, 2000)
        completed = random.randint(300, 1000)
        in_progress = random.randint(50, 150)
        blocked = len(self.blocked_tasks)
        failed = random.randint(10, 50)
        pending = total_tasks - completed - in_progress - blocked - failed

        self.tasks = {
            TaskStatus.COMPLETED.value: completed,
            TaskStatus.IN_PROGRESS.value: in_progress,
            TaskStatus.BLOCKED.value: blocked,
            TaskStatus.FAILED.value: failed,
            TaskStatus.PENDING.value: pending
        }

    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> None:
        """Update agent metrics."""
        with self.lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                for key, value in updates.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)

    def record_task_completion(self, completion_time: float) -> None:
        """Record task completion time for percentile calculations."""
        with self.lock:
            self.completion_times.append(completion_time)
            if len(self.completion_times) > 10000:
                self.completion_times = self.completion_times[-10000:]

    def get_metrics(self) -> MetricsResponse:
        """Generate complete metrics response."""
        with self.lock:
            start_query = time.time()

            system_health = self._compute_system_health()
            task_dist = self._compute_task_distribution()
            bottlenecks = self._identify_bottlenecks()
            recommendations = self._generate_recommendations(
                system_health, bottlenecks
            )

            query_time = (time.time() - start_query) * 1000

            return MetricsResponse(
                status="healthy" if system_health.failed_tasks < 50 else "degraded",
                timestamp=datetime.utcnow().isoformat() + "Z",
                query_time_ms=round(query_time, 2),
                system_health=system_health,
                agents=list(self.agents.values()),
                task_distribution=task_dist,
                blocked_tasks=list(self.blocked_tasks.values()),
                project_velocity=list(self.projects.values()),
                top_bottlenecks=bottlenecks[:5],
                recommendations=recommendations
            )

    def _compute_system_health(self) -> SystemHealth:
        """Compute overall system health metrics."""
        total_agents = len(self.agents)
        active_agents = sum(
            1 for a in self.agents.values() if a.status == "active"
        )
        idle_agents = total_agents - active_agents

        total_tasks = sum(self.tasks.values())
        pending = self.tasks.get(TaskStatus.PENDING.value, 0)
        blocked = self.tasks.get(TaskStatus.BLOCKED.value, 0)
        failed = self.tasks.get(TaskStatus.FAILED.value, 0)
        completed = self.tasks.get(TaskStatus.COMPLETED.value, 0)

        avg_cpu = (
            sum(a.cpu_usage_percent for a in self.agents.values()) / 
            total_agents if total_agents > 0 else 0
        )
        avg_mem = (
            sum(a.memory_usage_mb for a in self.agents.values()) / 
            total_agents if total_agents > 0 else 0
        )

        sorted_times = sorted(self.completion_times)
        p95_idx = max(0, int(len(sorted_times) * 0.95) - 1)
        p99_idx = max(0, int(len(sorted_times) * 0.99) - 1)
        p95 = sorted_times[p95_idx] if sorted_times else 0
        p99 = sorted_times[p99_idx] if sorted_times else 0

        return SystemHealth(
            timestamp=datetime.utcnow().isoformat() + "Z",
            total_agents=total_agents,
            active_agents=active_agents,
            idle_agents=idle_agents,
            total_tasks=total_tasks,
            pending_tasks=pending,
            blocked_tasks=blocked,
            failed_tasks=failed,
            system_uptime_seconds=int(time.time() - self.start_time),
            avg_agent_cpu_percent=round(avg_cpu, 2),
            avg_agent_memory_mb=round(avg_mem, 2),
            p95_task_completion_time_seconds=round(p95, 2),
            p99_task_completion_time_seconds=round(p99, 2)
        )

    def _compute_task_distribution(self) -> List[TaskMetric]:
        """Compute task distribution by status."""
        total = sum(self.tasks.values())
        distribution = []

        for status in TaskStatus:
            count = self.tasks.get(status.value, 0)
            percentage = (count / total * 100) if total > 0 else 0
            distribution.append(TaskMetric(
                status=status.value,
                count=count,
                percentage=round(percentage, 2)
            ))

        return distribution

    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify system bottlenecks."""
        bottlenecks = []

        blocked_count = len(self.blocked_tasks)
        if blocked_count > 5:
            bottlenecks.append({
                "type": "blocked_tasks",
                "severity": "high" if blocked_count > 20 else "medium",
                "description": f"{blocked_count} tasks are blocked",
                "count": blocked_count,
                "estimated_impact": blocked_count * 60
            })

        idle_agents = [a for a in self.agents.values() if a.status == "idle"]
        if idle_agents and self.tasks.get(TaskStatus.PENDING.value, 0) > 0:
            bottlenecks.append({
                "type": "idle_agents_with_pending_work",
                "severity": "medium",
                "description": f"{len(idle_agents)} idle agents despite pending tasks",
                "idle_agent_count": len(idle_agents),
                "pending_tasks": self.tasks.get(TaskStatus.PENDING.value, 0)
            })

        high_cpu_agents = [
            a for a in self.agents.values() if a.cpu_usage_percent > 85
        ]
        if high_cpu_agents:
            bottlenecks.append({
                "type": "high_cpu_utilization",
                "severity": "medium",
                "description": f"{len(high_cpu_agents)} agents at >85% CPU",
                "agent_count": len(high_cpu_agents),
                "avg_cpu": round(
                    sum(a.cpu_usage_percent for a in high_cpu_agents) / 
                    len(high_cpu_agents), 2
                )
            })

        high_error_agents = [
            a for a in self.agents.values() if a.error_count > 10
        ]
        if high_error_agents:
            bottlenecks.append({
                "type": "high_error_rate",
                "severity": "high",
                "description": f"{len(high_error_agents)} agents with >10 errors",
                "agent_ids": [a.agent_id for a in high_error_agents],
                "total_errors": sum(a.error_count for a in high_error_agents)
            })

        return sorted(
            bottlenecks,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(
                x.get("severity", "low"), 3
            )
        )

    def _generate_recommendations(
        self, health: SystemHealth, bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        if health.blocked_tasks > health.total_tasks * 0.1:
            recs.append(
                "High number of blocked tasks detected. Review dependencies "
                "and external service availability."
            )

        if health.idle_agents > 0 and health.pending_tasks > 0:
            recs.append(
                f"Redistribute work: {health.idle_agents} idle agents "
                f"available with {health.pending_tasks} pending tasks."
            )

        if health.avg_agent_cpu_percent > 80:
            recs.append(
                "System CPU utilization is high. Consider scaling up agent pool "
                "or optimizing task distribution."
            )

        if health.failed_tasks > health.total_tasks * 0.05:
            recs.append(
                f"Task failure rate is {health.failed_tasks / health.total_tasks * 100:.1f}%. "
                "Investigate error logs and implement retry strategies."
            )

        if len(bottlenecks) > 0:
            recs.append(
                f"Address {len(bottlenecks)} identified bottlenecks "
                "to improve overall throughput."
            )

        return recs


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoints."""

    # Class variable to hold metrics collector
    metrics_collector: Optional[MetricsCollector] = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        if path == "/api/metrics":
            self._handle_metrics_request()
        elif path == "/api/metrics/schema":
            self._handle_schema_request()
        elif path == "/health":
            self._handle_health_request()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_metrics_request(self) -> None:
        """Handle /api/metrics endpoint."""
        if not self.metrics_collector:
            self._send_response(503, {"error": "Metrics collector not initialized"})
            return

        metrics = self.metrics_collector.get_metrics()
        metrics_dict = asdict(metrics)

        self._send_response(200, metrics_dict, content_type="application/json")

    def _handle_schema_request(self) -> None:
        """Handle /api/metrics/schema endpoint with OpenAPI spec."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "SwarmPulse Agent Activity Metrics API",
                "version": "1.0.0",
                "description": "Real-time monitoring dashboard for Swarm health"
            },
            "paths": {
                "/api/metrics": {
                    "get": {
                        "summary": "Get current system metrics",
                        "operationId": "getMetrics",
                        "responses": {
                            "200": {
                                "description": "Current metrics snapshot",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/MetricsResponse"
                                        }
                                    }
                                }
                            },
                            "503": {
                                "description": "Service unavailable"
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "MetricsResponse": {
                        "type": "object",
                        "required": [
                            "status", "timestamp", "query_time_ms",
                            "system_health", "agents", "task_distribution",
                            "blocked_tasks", "project_velocity", 
                            "top_bottlenecks", "recommendations"
                        ],
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["healthy", "degraded", "critical"],
                                "description": "Overall system status"
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Metrics capture timestamp"
                            },
                            "query_time_ms": {
                                "type": "number",
                                "description": "Time to generate metrics in milliseconds"
                            },
                            "system_health": {
                                "$ref": "#/components/schemas/SystemHealth"
                            },
                            "agents": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/AgentMetric"}
                            },
                            "task_distribution": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/TaskMetric"}
                            },
                            "blocked_tasks": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/BlockedTask"}
                            },
                            "project_velocity": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ProjectVelocity"}
                            },
                            "top_bottlenecks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"},
                                        "severity": {"type": "string"},
                                        "description": {"type": "string"}
                                    }
                                }
                            },
                            "recommendations": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "SystemHealth": {
                        "type": "object",
                        "required": [
                            "timestamp", "total_agents", "active_agents",
                            "idle_agents", "total_tasks", "pending_tasks",
                            "blocked_tasks", "failed_tasks", "system_uptime_seconds",
                            "avg_agent_cpu_percent", "avg_agent_memory_mb",
                            "p95_task_completion_time_seconds",
                            "p99_task_completion_time_seconds"
                        ],
                        "properties": {
                            "timestamp": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "total_agents": {
                                "type": "integer",
                                "description": "Total agents in swarm"
                            },
                            "active_agents": {
                                "type": "integer",
                                "description": "Currently active agents"
                            },
                            "idle_agents": {
                                "type": "integer",
                                "description": "Idle agents available for work"
                            },
                            "total_tasks": {
                                "type": "integer"
                            },
                            "pending_tasks": {
                                "type": "integer"
                            },
                            "blocked_tasks": {
                                "type": "integer"
                            },
                            "failed_tasks": {
                                "type": "integer"
                            },
                            "system_uptime_seconds": {
                                "type": "integer"
                            },
                            "avg_agent_cpu_percent": {
                                "type": "number"
                            },
                            "avg_agent_memory_mb": {
                                "type": "number"
                            },
                            "p95_task_completion_time_seconds": {
                                "type": "number"
                            },
                            "p99_task_completion_time_seconds": {
                                "type": "number"
                            }
                        }
                    },
                    "AgentMetric": {
                        "type": "object",
                        "required": [
                            "agent_id", "name", "status", "uptime_seconds",
                            "tasks_completed", "tasks_in_progress",
                            "cpu_usage_percent", "memory_usage_mb",
                            "last_heartbeat", "error_count", "queue_length"
                        ],
                        "properties": {
                            "agent_id": {"type": "string"},
                            "name": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["active", "idle", "offline"]
                            },
                            "uptime_seconds": {"type": "integer"},
                            "tasks_completed": {"type": "integer"},
                            "tasks_in_progress": {"type": "integer"},
                            "cpu_usage_percent": {"type": "number"},
                            "memory_usage_mb": {"type": "number"},
                            "last_heartbeat": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "error_count": {"type": "integer"},
                            "queue_length": {"type": "integer"}
                        }
                    },
                    "TaskMetric": {
                        "type": "object",
                        "required": ["status", "count", "percentage"],
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": [
                                    "pending", "in_progress", "completed",
                                    "blocked", "failed", "idle"
                                ]
                            },
                            "count": {"type": "integer"},
                            "percentage": {"type": "number"}
                        }
                    },
                    "BlockedTask": {
                        "type": "object",
                        "required": [
                            "task_id", "project_id", "assigned_agent_id",
                            "blocked_reason", "blocked_duration_seconds",
                            "blocked_since", "dependencies"
                        ],
                        "properties": {
                            "task_id": {"type": "string"},
                            "project_id": {"type": "string"},
                            "assigned_agent_id": {"type": "string"},
                            "blocked_reason": {"type": "string"},
                            "blocked_duration_seconds": {"type": "integer"},
                            "blocked_since": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "ProjectVelocity": {
                        "type": "object",
                        "required": [
                            "project_id", "name", "tasks_completed_today",
                            "tasks_completed_week", "tasks_completed_month",
                            "avg_completion_time_seconds", "current_sprint_capacity",
                            "current_sprint_used"
                        ],
                        "properties": {
                            "project_id": {"type": "string"},
                            "name": {"type": "string"},
                            "tasks_completed_today": {"type": "integer"},
                            "tasks_completed_week": {"type": "integer"},
                            "tasks_completed_month": {"type": "integer"},
                            "avg_completion_time_seconds": {"type": "number"},
                            "current_sprint_capacity": {"type": "integer"},
                            "current_sprint_used": {"type": "integer"},
                            "bottleneck_description": {
                                "type": "string",
                                "nullable": True
                            }
                        }
                    }
                }
            }
        }

        self._send_response(200, openapi_spec, content_type="application/json")

    def _handle_health_request(self) -> None:
        """Handle /health endpoint."""
        response = {
            "status": "running",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"
        }
        self._send_response(200, response)

    def _send_response(
        self,
        status_code: int,
        data: Dict[str, Any],
        content_type: str = "application/json"
    ) -> None:
        """Send JSON response."""
        response_body = json.dumps(data, indent=2)
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass


def run_metrics_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    enable_demo: bool = True
) -> None:
    """Start metrics HTTP server."""
    collector = MetricsCollector(enable_demo_data=enable_demo)
    MetricsHandler.metrics_collector = collector

    server = HTTPServer((host, port), MetricsHandler)
    print(f"[+] Metrics server running at http://{host}:{port}")
    print(f"[+] Endpoints:")
    print(f"    - http://{host}:{port}/api/metrics (live metrics)")
    print(f"    - http://{host}:{port}/api/metrics/schema (OpenAPI spec)")
    print(f"    - http://{host}:{port}/health (health check)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down metrics server")
        server.shutdown()


def demo_metrics_collection() -> None:
    """Demonstrate metrics collection without server."""
    print("=" * 70)
    print("SwarmPulse Agent Activity Monitor - Metrics Demo")
    print("=" * 70)

    collector = MetricsCollector(enable_demo_data=True)

    print("\n[*] Collecting metrics...")
    metrics = collector.get_metrics()

    print(f"\n[+] Status: {metrics.status}")
    print(f"[+] Query Time: {metrics.query_time_ms}ms")
    print(f"[+] Timestamp: {metrics.timestamp}")

    health = metrics.system_health
    print(f"\n[+] System Health:")
    print(f"    Total Agents: {health.total_agents}")
    print(f"    Active Agents: {health.active_agents}")
    print(f"    Idle Agents: {health.idle_agents}")
    print(f"    Total Tasks: {health.total_tasks}")
    print(f"    Pending Tasks: {health.pending_tasks}")
    print(f"    Blocked Tasks: {health.blocked_tasks}")
    print(f"    Failed Tasks: {health.failed_tasks}")
    print(f"    System Uptime: {health.system_uptime_seconds}s")
    print(f"    Avg CPU: {health.avg_agent_cpu_percent}%")
    print(f"    Avg Memory: {health.avg_agent_memory_mb}MB")
    print(f"    P95 Completion Time: {health.p95_task_completion_time_seconds}s")
    print(f"    P99 Completion Time: {health.p99_task_completion_time_seconds}s")

    print(f"\n[+] Task Distribution:")
    for task_dist in metrics.task_distribution:
        print(f"    {task_dist.status}: {task_dist.count} ({task_dist.percentage}%)")

    print(f"\n[+] Top Agents (by CPU):")
    sorted_agents = sorted(
        metrics.agents,
        key=lambda a: a.cpu_usage_percent,
        reverse=True
    )
    for agent in sorted_agents[:3]:
        print(
            f"    {agent.name}: "
            f"{agent.cpu_usage_percent}% CPU, "
            f"{agent.tasks_completed} completed, "
            f"{agent.error_count} errors"
        )

    print(f"\n[+] Blocked Tasks ({len(metrics.blocked_tasks)}):")
    for blocked in metrics.blocked_tasks[:3]:
        print(
            f"    {blocked.task_id}: "
            f"{blocked.blocked_reason} "
            f"({blocked.blocked_duration_seconds}s)"
        )

    print(f"\n[+] Project Velocity:")
    for proj in metrics.project_velocity:
        print(
            f"    {proj.name}: "
            f"{proj.tasks_completed_today} today, "
            f"{proj.tasks_completed_week} week, "
            f"{proj.tasks_completed_month} month"
        )

    print(f"\n[+] Top Bottlenecks:")
    for bottleneck in metrics.top_bottlenecks[:3]:
        print(
            f"    [{bottleneck.get('severity', 'info')}] "
            f"{bottleneck.get('type', 'unknown')}: "
            f"{bottleneck.get('description', 'N/A')}"
        )

    print(
)

    print(f"\n[+] Recommendations:")
    for rec in metrics.recommendations:
        print(f"    • {rec}")

    print(f"\n[+] Full Metrics Response (JSON):")
    metrics_dict = asdict(metrics)
    print(json.dumps(metrics_dict, indent=2))


def main() -> None:
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description="SwarmPulse Agent Activity Monitor - Metrics Endpoint"
    )
    parser.add_argument(
        "--mode",
        choices=["server", "demo"],
        default="demo",
        help="Run mode: server (HTTP) or demo (collection)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--demo-data",
        action="store_true",
        default=True,
        help="Enable demo data generation (default: True)"
    )
    parser.add_argument(
        "--disable-demo-data",
        action="store_false",
        dest="demo_data",
        help="Disable demo data generation"
    )

    args = parser.parse_args()

    if args.mode == "server":
        run_metrics_server(
            host=args.host,
            port=args.port,
            enable_demo=args.demo_data
        )
    else:
        demo_metrics_collection()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design API metrics endpoint schema
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:43:34.902Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design API metrics endpoint schema
MISSION: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2025-01-20

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire swarm. Provides comprehensive API metrics
endpoint schema with validation, aggregation, and health assessment.
"""

import json
import time
import random
import argparse
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from enum import Enum


class AgentStatus(Enum):
    """Agent operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class TaskStatus(Enum):
    """Task completion status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class MetricDataPoint:
    """Single metric data point with timestamp."""
    timestamp: float
    value: float
    unit: str


@dataclass
class TaskMetrics:
    """Metrics for a single task execution."""
    task_id: str
    agent_id: str
    status: str
    start_time: float
    end_time: Optional[float]
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class AgentMetrics:
    """Real-time metrics for a single agent."""
    agent_id: str
    status: str
    uptime_ms: float
    cpu_percent: float
    memory_mb: float
    tasks_completed: int
    tasks_failed: int
    tasks_pending: int
    error_rate: float
    avg_task_duration_ms: float
    throughput_tasks_per_min: float
    last_heartbeat: float
    response_time_ms: float
    active_connections: int


@dataclass
class SwarmMetrics:
    """Aggregated metrics for entire swarm."""
    timestamp: float
    swarm_id: str
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    unhealthy_agents: int
    offline_agents: int
    total_tasks_completed: int
    total_tasks_failed: int
    total_tasks_pending: int
    avg_error_rate: float
    avg_cpu_percent: float
    avg_memory_mb: float
    total_throughput_tpm: float
    overall_health_score: float


class MetricsBuffer:
    """Circular buffer for storing historical metrics."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
    
    def append(self, metric: MetricDataPoint) -> None:
        """Add metric to buffer."""
        self.buffer.append(metric)
    
    def get_recent(self, seconds: int) -> List[MetricDataPoint]:
        """Get metrics from last N seconds."""
        cutoff_time = time.time() - seconds
        return [m for m in self.buffer if m.timestamp >= cutoff_time]
    
    def get_all(self) -> List[MetricDataPoint]:
        """Get all metrics in buffer."""
        return list(self.buffer)


class AgentActivityMonitor:
    """Real-time monitoring system for swarm agents."""
    
    def __init__(self, swarm_id: str = "swarm-001", update_interval: float = 5.0):
        self.swarm_id = swarm_id
        self.update_interval = update_interval
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.task_history: List[TaskMetrics] = []
        self.metrics_buffers: Dict[str, MetricsBuffer] = defaultdict(lambda: MetricsBuffer())
        self.lock = threading.Lock()
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def register_agent(self, agent_id: str) -> None:
        """Register a new agent in the swarm."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(
                    agent_id=agent_id,
                    status=AgentStatus.HEALTHY.value,
                    uptime_ms=0.0,
                    cpu_percent=random.uniform(5, 20),
                    memory_mb=random.uniform(256, 1024),
                    tasks_completed=0,
                    tasks_failed=0,
                    tasks_pending=0,
                    error_rate=0.0,
                    avg_task_duration_ms=100.0,
                    throughput_tasks_per_min=10.0,
                    last_heartbeat=time.time(),
                    response_time_ms=50.0,
                    active_connections=1
                )
    
    def record_task(self, task_metrics: TaskMetrics) -> None:
        """Record completion of a task."""
        with self.lock:
            self.task_history.append(task_metrics)
            
            if task_metrics.agent_id in self.agent_metrics:
                agent = self.agent_metrics[task_metrics.agent_id]
                if task_metrics.success:
                    agent.tasks_completed += 1
                else:
                    agent.tasks_failed += 1
                
                recent_tasks = [
                    t for t in self.task_history
                    if t.agent_id == task_metrics.agent_id
                    and time.time() - t.end_time <= 300  # Last 5 minutes
                ] if task_metrics.end_time else []
                
                if recent_tasks:
                    agent.avg_task_duration_ms = sum(t.duration_ms for t in recent_tasks) / len(recent_tasks)
                    failed = sum(1 for t in recent_tasks if not t.success)
                    agent.error_rate = failed / len(recent_tasks) if recent_tasks else 0.0
                    agent.throughput_tasks_per_min = (len(recent_tasks) / 5.0) * 60
    
    def update_agent_health(self, agent_id: str, cpu: float, memory: float,
                           response_time: float, active_connections: int) -> None:
        """Update agent health metrics."""
        with self.lock:
            if agent_id in self.agent_metrics:
                agent = self.agent_metrics[agent_id]
                agent.cpu_percent = cpu
                agent.memory_mb = memory
                agent.response_time_ms = response_time
                agent.active_connections = active_connections
                agent.last_heartbeat = time.time()
                
                # Determine status based on metrics
                if cpu > 85 or memory > 2048 or response_time > 5000:
                    agent.status = AgentStatus.UNHEALTHY.value
                elif cpu > 70 or memory > 1536 or response_time > 2000:
                    agent.status = AgentStatus.DEGRADED.value
                else:
                    agent.status = AgentStatus.HEALTHY.value
                
                # Record metric data point
                self.metrics_buffers[f"{agent_id}_cpu"].append(
                    MetricDataPoint(timestamp=time.time(), value=cpu, unit="percent")
                )
                self.metrics_buffers[f"{agent_id}_memory"].append(
                    MetricDataPoint(timestamp=time.time(), value=memory, unit="mb")
                )
    
    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific agent."""
        with self.lock:
            if agent_id not in self.agent_metrics:
                return None
            
            agent = self.agent_metrics[agent_id]
            return asdict(agent)
    
    def get_swarm_metrics(self) -> Dict[str, Any]:
        """Get aggregated swarm metrics."""
        with self.lock:
            total_agents = len(self.agent_metrics)
            healthy = sum(1 for a in self.agent_metrics.values() if a.status == AgentStatus.HEALTHY.value)
            degraded = sum(1 for a in self.agent_metrics.values() if a.status == AgentStatus.DEGRADED.value)
            unhealthy = sum(1 for a in self.agent_metrics.values() if a.status == AgentStatus.UNHEALTHY.value)
            offline = sum(1 for a in self.agent_metrics.values() if a.status == AgentStatus.OFFLINE.value)
            
            total_completed = sum(a.tasks_completed for a in self.agent_metrics.values())
            total_failed = sum(a.tasks_failed for a in self.agent_metrics.values())
            total_pending = sum(a.tasks_pending for a in self.agent_metrics.values())
            
            avg_error_rate = (sum(a.error_rate for a in self.agent_metrics.values()) / total_agents) if total_agents > 0 else 0.0
            avg_cpu = (sum(a.cpu_percent for a in self.agent_metrics.values()) / total_agents) if total_agents > 0 else 0.0
            avg_memory = (sum(a.memory_mb for a in self.agent_metrics.values()) / total_agents) if total_agents > 0 else 0.0
            total_throughput = sum(a.throughput_tasks_per_min for a in self.agent_metrics.values())
            
            # Calculate health score (0-100)
            health_score = (
                (healthy / total_agents * 100) if total_agents > 0 else 0
                - (unhealthy / total_agents * 50) if total_agents > 0 else 0
            )
            health_score = max(0, min(100, health_score))
            
            return asdict(SwarmMetrics(
                timestamp=time.time(),
                swarm_id=self.swarm_id,
                total_agents=total_agents,
                healthy_agents=healthy,
                degraded_agents=degraded,
                unhealthy_agents=unhealthy,
                offline_agents=offline,
                total_tasks_completed=total_completed,
                total_tasks_failed=total_failed,
                total_tasks_pending=total_pending,
                avg_error_rate=avg_error_rate,
                avg_cpu_percent=avg_cpu,
                avg_memory_mb=avg_memory,
                total_throughput_tpm=total_throughput,
                overall_health_score=health_score
            ))
    
    def get_metrics_endpoint_schema(self) -> Dict[str, Any]:
        """Return complete API metrics endpoint schema."""
        return {
            "api_version": "1.0.0",
            "endpoints": {
                "/metrics/swarm": {
                    "method": "GET",
                    "description": "Get aggregated swarm health metrics",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "number", "description": "Unix timestamp"},
                            "swarm_id": {"type": "string"},
                            "total_agents": {"type": "integer"},
                            "healthy_agents": {"type": "integer"},
                            "degraded_agents": {"type": "integer"},
                            "unhealthy_agents": {"type": "integer"},
                            "offline_agents": {"type": "integer"},
                            "total_tasks_completed": {"type": "integer"},
                            "total_tasks_failed": {"type": "integer"},
                            "total_tasks_pending": {"type": "integer"},
                            "avg_error_rate": {"type": "number", "minimum": 0, "maximum": 1},
                            "avg_cpu_percent": {"type": "number", "minimum": 0, "maximum": 100},
                            "avg_memory_mb": {"type": "number"},
                            "total_throughput_tpm": {"type": "number"},
                            "overall_health_score": {"type": "number", "minimum": 0, "maximum": 100}
                        }
                    }
                },
                "/metrics/agents": {
                    "method": "GET",
                    "description": "Get metrics for all agents",
                    "response_schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy", "offline"]},
                                "uptime_ms": {"type": "number"},
                                "cpu_percent": {"type": "number", "minimum": 0, "maximum": 100},
                                "memory_mb": {"type": "number"},
                                "tasks_completed": {"type": "integer"},
                                "tasks_failed": {"type": "integer"},
                                "tasks_pending": {"type": "integer"},
                                "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
                                "avg_task_duration_ms": {"type": "number"},
                                "throughput_tasks_per_min": {"type": "number"},
                                "last_heartbeat": {"type": "number"},
                                "response_time_ms": {"type": "number"},
                                "active_connections": {"type": "integer"}
                            }
                        }
                    }
                },
                "/metrics/agents/{agent_id}": {
                    "method": "GET",
                    "description": "Get metrics for a specific agent",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Agent identifier"}
                    },
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string"},
                            "status": {"type": "string"},
                            "uptime_ms": {"type": "number"},
                            "cpu_percent": {"type": "number"},
                            "memory_mb": {"type": "number"},
                            "tasks_completed": {"type": "integer"},
                            "tasks_failed": {"type": "integer"},
                            "tasks_pending": {"type": "integer"},
                            "error_rate": {"type": "number"},
                            "avg_task_duration_ms": {"type": "number"},
                            "throughput_tasks_per_min": {"type": "number"},
                            "last_heartbeat": {"type": "number"},
                            "response_time_ms": {"type": "number"},
                            "active_connections": {"type": "integer"}
                        }
                    }
                },
                "/metrics/tasks": {
                    "method": "GET",
                    "description": "Get task execution metrics",
                    "query_parameters": {
                        "agent_id": {"type": "string", "required": False},
                        "status": {"type": "string", "required": False},
                        "limit": {"type": "integer", "default": 100}
                    },
                    "response_schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string"},
                                "agent_id": {"type": "string"},
                                "status": {"type": "string"},
                                "start_time": {"type": "number"},
                                "end_time": {"type": ["number", "null"]},
                                "duration_ms": {"type": "number"},
                                "success": {"type": "boolean"},
                                "error_message": {"type": ["string", "null"]},
                                "retry_count": {"type": "integer"}
                            }
                        }
                    }
                },
                "/metrics/health": {
                    "method": "GET",
                    "description": "Quick health check endpoint",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                            "timestamp": {"type": "number"},
                            "message": {"type": "string"}
                        }
                    }
                },
                "/metrics/history/{agent_id}/{metric_type}": {
                    "method": "GET",
                    "description": "Get historical metric data for an agent",
                    "parameters": {
                        "agent_id": {"type": "string"},
                        "metric_type": {"type": "string", "enum": ["cpu", "memory", "response_time", "error_rate"]}
                    },
                    "query_parameters": {
                        "seconds": {"type": "integer", "default": 300}
                    },
                    "response_schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "timestamp": {"type": "number"},
                                "value": {"type": "number"},
                                "unit": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "error_responses": {
                "400": {
                    "description": "Bad request",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "timestamp": {"type": "number"}
                        }
                    }
                },
                "404": {
                    "description": "Resource not found",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "resource": {"type": "string"}
                        }
                    }
                },
                "500": {
                    "description": "Internal server error",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "timestamp": {"type": "number"}
                        }
                    }
                }
            }
        }
    
    def simulate_agent_activity(self, agent_id: str, duration_seconds: int = 60) -> None:
        """Simulate agent activity for testing."""
        start_time = time.time()
        self.register_agent(agent_id)
        
        while time.time() - start_time < duration_seconds and self.running:
            # Simulate metrics
            cpu = random.uniform(10, 60)
            memory = random.uniform(300, 1200)
            response_time = random.uniform(50, 500)
            connections = random.randint(1, 10)
            
            self.update_agent_health(agent_id, cpu, memory, response_time, connections)
            
            # Simulate task completion
            if random.random() > 0.3:
                task_id = f"task-{agent_id}-{int(time.time() * 1000)}"
                duration = random.uniform(100, 5000)
                success = random.random() > 0.1
                
                task_metrics = TaskMetrics(
                    task_id=task_id,
                    agent_id=agent_id,
                    status=TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value,
                    start_time=time.time() - (duration / 1000),
                    end_time=time.time(),
                    duration_ms=duration,
                    success=success,
                    error_message="Task timeout" if not success and random.random() > 0.7 else None,
                    retry_count=random.randint(0, 2) if not success else 0
                )
                self.record_task(task_metrics)
            
            time.sleep(random.uniform(0.5, 2.0))
    
    def start_monitoring(self, num_agents: int = 5) -> None:
        """Start monitoring loop with simulated agents."""
        self.running = True
        
        # Start agent simulation threads
        for i in range(num_agents):
            agent_id = f"agent-{self.swarm_id}-{i:03d}"
            thread = threading.Thread(
                target=self.simulate_agent_activity,
                args=(agent_id, 120),
                daemon=True
            )
            thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.running = False


def format_json_response(data: Any, pretty: bool = True) -> str:
    """Format response as JSON."""
    if pretty:
        return json.dumps(data, indent=2)
    return json.dumps(data)


def main():
    parser = argparse.ArgumentParser(
        description="SwarmPulse Agent Activity Monitor - API Metrics Endpoint Schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --swarm-id swarm-prod-01 --num-agents 10 --show-schema
  python3 solution.py --swarm-id swarm-test --duration 30 --show-metrics
  python3 solution.py --agent-id agent-001 --show-agent-metrics
        """
    )
    
    parser.add_argument(
        "--swarm-id",
        type=str,
        default="swarm-001",
        help="Swarm identifier (default: swarm-001)"
    )
    
    parser.add_argument(
        "--num-agents",
        type=int,
        default=5,
        help="Number of agents to simulate (default: 5)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Monitoring duration in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--show-schema",
        action="store_true",
        help="Display API metrics endpoint schema"
    )
    
    parser.add_argument(
        "--show-metrics",
        action="store_true",
        help="Display swarm metrics during monitoring"
    )
    
    parser.add_argument(
        "--show-agent-metrics",
        action="store_true",
        help="Display individual agent metrics"
    )
    
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Specific agent ID to monitor"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="Write metrics output to file"
    )
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = AgentActivityMonitor(swarm_id=args.swarm_id, update_interval=1.0)
    
    # Show schema if requested
    if args.show_schema:
        schema = monitor.get_metrics_endpoint_schema()
        output = format_json_response(schema, pretty=True)
        print("API METRICS ENDPOINT SCHEMA")
        print("=" * 60)
        print(output)
        if args.output_file:
            with open(args.output_file, "w") as f:
                f.write(output)
        return
    
    # Start monitoring
    print(f"Starting SwarmPulse Agent Activity Monitor")
    print(f"Swarm ID: {args.swarm_id}")
    print(f"Number of Agents: {args.num_agents}")
    print(f"Duration: {args.duration} seconds")
    print("=" * 60)
    
    monitor.start_monitoring(num_agents=args.num_agents)
    
    start_time = time.time()
    metrics_samples = []
    
    try:
        while time.time() - start_time < args.duration:
            time.sleep(2)
            
            # Collect metrics
            swarm_metrics = monitor.get_swarm_metrics()
            metrics_samples.append(swarm_metrics)
            
            if args.show_metrics:
                print(f"\n[{datetime.fromtimestamp(swarm_metrics['timestamp']).isoformat()}]")
                print(f"Agents: {swarm_metrics['healthy_agents']}/{swarm_metrics['total_agents']} healthy")
                print(f"Tasks: {swarm_metrics['total_tasks_completed']} completed, "
                      f"{swarm_metrics['total_tasks_failed']} failed")
                print(f"Throughput: {swarm_metrics['total_throughput_tpm']:.1f} tasks/min")
                print(f"Error Rate: {swarm_metrics['avg_error_rate']:.2%}")
                print(f"Health Score: {swarm_metrics['overall_health_score']:.1f}/100")
                print(f"CPU: {swarm_metrics['avg_cpu_percent']:.1f}% | Memory: {swarm_metrics['avg_memory_mb']:.0f}MB")
            
            if args.show_agent_metrics:
                print("\nAgent Metrics:")
                for agent_id in sorted(monitor.agent_metrics.keys()):
                    agent_data = monitor.get_agent_metrics(agent_id)
                    if agent_data:
                        print(f"  {agent_id}: {agent_data['status']} | "
                              f"CPU: {agent_data['cpu_percent']:.1f}% | "
                              f"Memory: {agent_data['memory_mb']:.0f}MB | "
                              f"Tasks: {agent_data['tasks_completed']} completed")
            
            if args.agent_id:
                agent_data = monitor.get_agent_metrics(args.agent_id)
                if agent_data:
                    print(f"\nMetrics for {args.agent_id}:")
                    print(format_json_response(agent_data, pretty=True))
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    
    finally:
        monitor.stop_monitoring()
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SWARM METRICS SUMMARY")
    print("=" * 60)
    final_metrics = monitor.get_swarm_metrics()
    print(format_json_response(final_metrics, pretty=True))
    
    # Output to file if requested
    if args.output_file:
        output_data = {
            "schema": monitor.get_metrics_endpoint_schema(),
            "final_metrics": final_metrics,
            "metrics_samples": metrics_samples[-5:] if metrics_samples else []
        }
        with open(args.output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nOutput written to {args.output_file}")


if __name__ == "__main__":
    main()
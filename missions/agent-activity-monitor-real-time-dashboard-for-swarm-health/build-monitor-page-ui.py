#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build /monitor page UI
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:38:51.143Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Agent Activity Monitor — Real-time Dashboard for Swarm Health
Mission: Build a live monitoring dashboard tracking agent activity, task throughput, and project velocity
Agent: @bolt
Date: 2024
"""

import json
import time
import random
import argparse
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
from enum import Enum
from collections import defaultdict


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    ACTIVE = "active"
    OFFLINE = "offline"


@dataclass
class Task:
    """Represents a task in the swarm"""
    task_id: str
    project_id: str
    agent_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    blocked_reason: str = ""
    priority: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "blocked_reason": self.blocked_reason,
            "priority": self.priority,
            "age_seconds": (datetime.now() - self.created_at).total_seconds()
        }


@dataclass
class Agent:
    """Represents an agent in the swarm"""
    agent_id: str
    status: AgentStatus
    active_task_count: int = 0
    completed_task_count: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "active_task_count": self.active_task_count,
            "completed_task_count": self.completed_task_count,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "heartbeat_age_seconds": (datetime.now() - self.last_heartbeat).total_seconds()
        }


@dataclass
class Project:
    """Represents a project in the swarm"""
    project_id: str
    name: str
    task_count: int = 0
    completed_count: int = 0
    blocked_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "task_count": self.task_count,
            "completed_count": self.completed_count,
            "blocked_count": self.blocked_count,
            "completion_rate": self.completed_count / self.task_count if self.task_count > 0 else 0
        }


@dataclass
class SwarmMetrics:
    """Aggregated swarm health metrics"""
    timestamp: datetime
    total_agents: int
    active_agents: int
    idle_agents: int
    offline_agents: int
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    blocked_tasks: int
    failed_tasks: int
    average_task_age: float
    throughput_per_hour: float
    bottleneck_agents: List[str] = field(default_factory=list)
    blocked_task_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_agents": self.total_agents,
            "active_agents": self.active_agents,
            "idle_agents": self.idle_agents,
            "offline_agents": self.offline_agents,
            "total_tasks": self.total_tasks,
            "pending_tasks": self.pending_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "completed_tasks": self.completed_tasks,
            "blocked_tasks": self.blocked_tasks,
            "failed_tasks": self.failed_tasks,
            "average_task_age": self.average_task_age,
            "throughput_per_hour": self.throughput_per_hour,
            "bottleneck_agents": self.bottleneck_agents,
            "blocked_task_ids": self.blocked_task_ids
        }


class SwarmMonitor:
    """Monitors and tracks swarm health metrics"""
    
    def __init__(self, max_heartbeat_age_seconds: int = 30):
        self.tasks: Dict[str, Task] = {}
        self.agents: Dict[str, Agent] = {}
        self.projects: Dict[str, Project] = {}
        self.max_heartbeat_age = max_heartbeat_age_seconds
        self.metrics_history: List[SwarmMetrics] = []
    
    def add_task(self, task: Task) -> None:
        """Add or update a task"""
        self.tasks[task.task_id] = task
        
        if task.project_id not in self.projects:
            self.projects[task.project_id] = Project(project_id=task.project_id, name=f"Project-{task.project_id}")
    
    def add_agent(self, agent: Agent) -> None:
        """Add or update an agent"""
        self.agents[agent.agent_id] = agent
    
    def update_task_status(self, task_id: str, new_status: TaskStatus, blocked_reason: str = "") -> bool:
        """Update task status"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = new_status
        task.updated_at = datetime.now()
        task.blocked_reason = blocked_reason
        return True
    
    def update_agent_heartbeat(self, agent_id: str, cpu_usage: float = 0.0, memory_usage: float = 0.0) -> bool:
        """Update agent heartbeat and resource usage"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        agent.last_heartbeat = datetime.now()
        agent.cpu_usage = cpu_usage
        agent.memory_usage = memory_usage
        
        heartbeat_age = (datetime.now() - agent.last_heartbeat).total_seconds()
        if heartbeat_age < self.max_heartbeat_age:
            agent.status = AgentStatus.ACTIVE
        
        return True
    
    def check_offline_agents(self) -> List[str]:
        """Identify offline agents based on heartbeat timeout"""
        offline = []
        for agent_id, agent in self.agents.items():
            heartbeat_age = (datetime.now() - agent.last_heartbeat).total_seconds()
            if heartbeat_age > self.max_heartbeat_age and agent.status != AgentStatus.OFFLINE:
                agent.status = AgentStatus.OFFLINE
                offline.append(agent_id)
        return offline
    
    def identify_bottlenecks(self, active_task_threshold: int = 5) -> List[str]:
        """Identify agents with excessive task load"""
        bottlenecks = []
        for agent_id, agent in self.agents.items():
            if agent.active_task_count >= active_task_threshold:
                bottlenecks.append(agent_id)
        return bottlenecks
    
    def get_blocked_tasks(self) -> List[Task]:
        """Get all blocked tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.BLOCKED]
    
    def compute_metrics(self) -> SwarmMetrics:
        """Compute aggregated swarm metrics"""
        self.check_offline_agents()
        
        active_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.ACTIVE)
        idle_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE)
        offline_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.OFFLINE)
        
        pending_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        in_progress_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        completed_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        blocked_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.BLOCKED)
        failed_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        
        task_ages = [(datetime.now() - t.created_at).total_seconds() for t in self.tasks.values()]
        avg_task_age = sum(task_ages) / len(task_ages) if task_ages else 0
        
        completed_in_last_hour = sum(1 for t in self.tasks.values() 
                                     if t.status == TaskStatus.COMPLETED and 
                                     (datetime.now() - t.updated_at).total_seconds() < 3600)
        throughput = completed_in_last_hour
        
        bottleneck_agents = self.identify_bottlenecks()
        blocked_tasks = self.get_blocked_tasks()
        blocked_task_ids = [t.task_id for t in blocked_tasks]
        
        metrics = SwarmMetrics(
            timestamp=datetime.now(),
            total_agents=len(self.agents),
            active_agents=active_agents,
            idle_agents=idle_agents,
            offline_agents=offline_agents,
            total_tasks=len(self.tasks),
            pending_tasks=pending_count,
            in_progress_tasks=in_progress_count,
            completed_tasks=completed_count,
            blocked_tasks=blocked_count,
            failed_tasks=failed_count,
            average_task_age=avg_task_age,
            throughput_per_hour=throughput,
            bottleneck_agents=bottleneck_agents,
            blocked_task_ids=blocked_task_ids
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_project_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for each project"""
        project_stats = {}
        
        for task in self.tasks.values():
            if task.project_id not in project_stats:
                project_stats[task.project_id] = {
                    "total": 0,
                    "completed": 0,
                    "blocked": 0,
                    "in_progress": 0
                }
            
            project_stats[task.project_id]["total"] += 1
            if task.status == TaskStatus.COMPLETED:
                project_stats[task.project_id]["completed"] += 1
            elif task.status == TaskStatus.BLOCKED:
                project_stats[task.project_id]["blocked"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                project_stats[task.project_id]["in_progress"] += 1
        
        result = []
        for project_id, stats in project_stats.items():
            project = self.projects.get(project_id)
            if project:
                result.append({
                    "project_id": project_id,
                    "name": project.name,
                    "total_tasks": stats["total"],
                    "completed_tasks": stats["completed"],
                    "in_progress_tasks": stats["in_progress"],
                    "blocked_tasks": stats["blocked"],
                    "completion_rate": stats["completed"] / stats["total"] if stats["total"] > 0 else 0
                })
        
        return result
    
    def get_daily_summary(self, days: int = 1) -> Dict[str, Any]:
        """Compute daily summary of metrics"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                "period_days": days,
                "metrics_collected": 0,
                "summary": "No data available"
            }
        
        avg_active_agents = sum(m.active_agents for m in recent_metrics) / len(recent_metrics)
        peak_blocked_tasks = max(m.blocked_tasks for m in recent_metrics)
        total_tasks_completed = recent_metrics[-1].completed_tasks if recent_metrics else 0
        avg_throughput = sum(m.throughput_per_hour for m in recent_metrics) / len(recent_metrics)
        
        return {
            "period_days": days,
            "metrics_collected": len(recent_metrics),
            "average_active_agents": avg_active_agents,
            "peak_blocked_tasks": peak_blocked_tasks,
            "total_tasks_completed": total_tasks_completed,
            "average_throughput_per_hour": avg_throughput,
            "timestamp": datetime.now().isoformat()
        }


class DashboardRenderer:
    """Renders dashboard data for /monitor page"""
    
    @staticmethod
    def render_summary_cards(metrics: SwarmMetrics) -> Dict[str, Any]:
        """Render summary stat cards"""
        return {
            "cards": [
                {
                    "title": "Active Agents",
                    "value": metrics.active_agents,
                    "total": metrics.total_agents,
                    "percentage": (metrics.active_agents / metrics.total_agents * 100) if metrics.total_agents > 0 else 0,
                    "type": "agents"
                },
                {
                    "title": "Tasks In Progress",
                    "value": metrics.in_progress_tasks,
                    "total": metrics.total_tasks,
                    "percentage": (metrics.in_progress_tasks / metrics.total_tasks * 100) if metrics.total_tasks > 0 else 0,
                    "type": "progress"
                },
                {
                    "title": "Blocked Tasks",
                    "value": metrics.blocked_tasks,
                    "total": metrics.total_tasks,
                    "percentage": (metrics.blocked_tasks / metrics.total_tasks * 100) if metrics.total_tasks > 0 else 0,
                    "type": "blocked",
                    "alert": metrics.blocked_tasks > 0
                },
                {
                    "title": "Throughput (per hour)",
                    "value": metrics.throughput_per_hour,
                    "unit": "tasks/hr",
                    "type": "throughput"
                }
            ]
        }
    
    @staticmethod
    def render_task_status_breakdown(metrics: SwarmMetrics) -> Dict[str, Any]:
        """Render task status breakdown bar"""
        total = metrics.total_tasks if metrics.total_tasks > 0 else 1
        
        return {
            "status_breakdown": [
                {
                    "status": "completed",
                    "count": metrics.completed_tasks,
                    "percentage": (metrics.completed_tasks / total) * 100,
                    "color": "green"
                },
                {
                    "status": "in_progress",
                    "count": metrics.in_progress_tasks,
                    "percentage": (metrics.in_progress_tasks / total) * 100,
                    "color": "blue"
                },
                {
                    "status": "pending",
                    "count": metrics.pending_tasks,
                    "percentage": (metrics.pending_tasks / total) * 100,
                    "color": "yellow"
                },
                {
                    "status": "blocked",
                    "count": metrics.blocked_tasks,
                    "percentage": (metrics.blocked_tasks / total) * 100,
                    "color": "red"
                },
                {
                    "status": "failed",
                    "count": metrics.failed_tasks,
                    "percentage": (metrics.failed_tasks / total) * 100,
                    "color": "orange"
                }
            ],
            "total_tasks": metrics.total_tasks
        }
    
    @staticmethod
    def render_blocked_tasks_list(tasks: List[Task], limit: int = 10) -> Dict[str, Any]:
        """Render list of blocked tasks"""
        sorted_tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]
        
        return {
            "blocked_tasks": [
                {
                    "task_id": task.task_id,
                    "project_id": task.project_id,
                    "agent_id": task.agent_id,
                    "blocked_reason": task.blocked_reason,
                    "blocked_duration_seconds": (datetime.now() - task.updated_at).total_seconds(),
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat()
                }
                for task in sorted_tasks
            ],
            "total_blocked": len(tasks)
        }
    
    @staticmethod
    def render_agent_status_overview(agents: List[Agent]) -> Dict[str, Any]:
        """Render agent status overview"""
        return {
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "status": agent.status.value,
                    "active_tasks": agent.active_task_count,
                    "completed_tasks": agent.completed_task_count,
                    "cpu_usage": agent.cpu_usage,
                    "memory_usage": agent.memory_usage,
                    "heartbeat_age": (datetime.now() - agent.last_heartbeat).total_seconds()
                }
                for agent in agents
            ]
        }


class MetricsAPI:
    """API endpoint handler for /api/metrics"""
    
    def __init__(self, monitor: SwarmMonitor):
        self.monitor = monitor
    
    def get_metrics_endpoint(self) -> str:
        """Get JSON response for /api/metrics"""
        metrics = self.monitor.compute_metrics()
        return json.dumps(metrics.to_dict(), indent=2)
    
    def get_projects_endpoint(self) -> str:
        """Get JSON response for /api/metrics/projects"""
        project_metrics = self.monitor.get_project_metrics()
        return json.dumps(project_metrics, indent=2)
    
    def get_agents_endpoint(self) -> str:
        """Get JSON response for /api/metrics/agents"""
        agents_data = [agent.to_dict() for agent in self.monitor.agents.values()]
        return json.dumps(agents_data, indent=2)
    
    def get_daily_summary_endpoint(self, days: int = 1) -> str:
        """Get JSON response for /api/metrics/daily-summary"""
        summary = self.monitor.get_daily_summary(days)
        return json.dumps(summary, indent=2)


class CronJobSummarizer:
    """Handles daily cron job summarization"""
    
    def __init__(self, monitor: SwarmMonitor):
        self.monitor = monitor
    
    def run_daily_summary(self) -> str:
        """Run daily summary computation"""
        summary = self.monitor.get_daily_summary(days=1)
        projects = self.monitor.get_project_metrics()
        
        output = {
            "summary_type": "daily",
            "generated_at": datetime.now().isoformat(),
            "daily_metrics": summary,
            "project_breakdown": projects,
            "top_bottleneck_agents": self.monitor.identify_bottlenecks()[:5],
            "blocked_task_count": len(self.monitor.get_blocked_tasks())
        }
        
        return json.dumps(output, indent=2)


def generate_sample_data(monitor: SwarmMonitor, num_agents: int = 10, num_tasks: int = 50) -> None:
    """Generate sample swarm data for demonstration"""
    
    projects = ["project-alpha", "project-beta", "project-gamma"]
    blocked_reasons = [
        "Waiting for dependency",
        "Resource unavailable",
        "Rate limit exceeded",
        "Configuration missing",
        "Upstream task failed"
    ]
    
    for i in range(num_agents):
        agent = Agent(
            agent_id=f"agent-{i:03d}",
            status=random.choice([AgentStatus.ACTIVE, AgentStatus.IDLE, AgentStatus.OFFLINE]),
            active_task_count=random.randint(0, 8),
            completed_task_count=random.randint(10, 100),
            last_heartbeat=datetime.now() - timedelta(seconds=random.randint(0, 40)),
            cpu_usage=random.uniform(10, 95),
            memory_usage=random.uniform(20, 80)
        )
        monitor.add_agent(agent)
    
    for i in range(num_tasks):
        project_id = random.choice(projects)
        agent_id = f"agent-{random.randint(0, num_agents-1):03d}"
        
        status = random.choices(
            [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.FAILED],
            weights=[20, 30, 35, 10, 5],
            k=1
        )[0]
        
        blocked_reason = random.choice(blocked_reasons) if status == TaskStatus.BLOCKED else ""
        
        task = Task(
            task_id=f"task-{i:05d}",
            project_id=project_id,
            agent_id=agent_id,
            status=status,
            created_at=datetime.now() - timedelta(hours=random.randint(0, 24)),
            updated_at=datetime.now() - timedelta(minutes=random.randint(0, 60)),
            blocked_reason=blocked_reason,
            priority=random.randint(1, 10)
        )
        monitor.add_task(task)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SwarmPulse Agent Activity Monitor - Real-time Dashboard for Swarm Health"
    )
    parser.add_argument(
        "--mode",
        choices=["monitor", "api", "dashboard", "daily-summary"],
        default="monitor",
        help="Operation mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Monitoring interval in seconds (for continuous monitoring)"
    )
    parser.add_argument(
        "--num-agents",
        type=int,
        default=10,
        help="Number of agents to generate in sample data"
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=50,
        help="Number of tasks to generate in sample data"
    )
    parser.add_argument(
        "--heartbeat-timeout",
        type=int,
        default=30,
        help="Agent heartbeat timeout in seconds"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of monitoring iterations to run"
    )
    
    args = parser.parse_args()
    
    monitor = SwarmMonitor(max_heartbeat_age_seconds=args.heartbeat_timeout)
    generate_sample_data(monitor, num_agents=args.num_agents, num_tasks=args.num_tasks)
    
    if args.mode == "monitor":
        for iteration in range(args.iterations):
            print(f"\n{'='*80}")
            print(f"Monitoring Iteration {iteration + 1}/{args.iterations}")
            print(f"Timestamp: {datetime.now().isoformat()}")
            print(f"{'='*80}\n")
            
            metrics = monitor.compute_metrics()
            
            if args.output_format == "json":
                print(json.dumps(metrics.to_dict(), indent=2))
            else:
                print(f"Total Agents: {metrics.total_agents} (Active: {metrics.active_agents}, Idle: {metrics.idle_agents}, Offline: {metrics.offline_agents})")
                print(f"Total Tasks: {metrics.total_tasks}")
                print(f"  - Completed: {metrics.completed_tasks}")
                print(f"  - In Progress: {metrics.in_progress_tasks}")
                print(f"  - Pending: {metrics.pending_tasks}")
                print(f"  - Blocked: {metrics.blocked_tasks}")
                print(f"  - Failed: {metrics.failed_tasks}")
                print(f"Average Task Age: {metrics.average_task_age:.1f} seconds")
                print(f"Throughput: {metrics.throughput_per_hour} tasks/hour")
                
                if metrics.bottleneck_agents:
                    print(f"Bottleneck Agents: {', '.join(metrics.bottleneck_agents)}")
                
                if metrics.blocked_task_ids:
                    print(f"Blocked Tasks: {len(metrics.blocked_task_ids)}")
            
            if iteration < args.iterations - 1:
                time.sleep(args.interval)
    
    elif args.mode == "api":
        api = MetricsAPI(monitor)
        
        print("\n/api/metrics endpoint response:")
        print(api.get_metrics_endpoint())
        
        print("\n\n/api/metrics/projects endpoint response:")
        print(api.get_projects_endpoint())
        
        print("\n\n/api/metrics/agents endpoint response:")
        print(api.get_agents_endpoint())
        
        print("\n\n/api/metrics/daily-summary endpoint response:")
        print(api.get_daily_summary_endpoint(days=1))
    
    elif args.mode == "dashboard":
        metrics = monitor.compute_metrics()
        renderer = DashboardRenderer()
        
        dashboard_data = {
            "summary_cards": renderer.render_summary_cards(metrics),
            "task_status_breakdown": renderer.render_task_status_breakdown(metrics),
            "blocked_tasks": renderer.render_blocked_tasks_list(monitor.get_blocked_tasks()),
            "agent_status": renderer.render_agent_status_overview(list(monitor.agents.values())),
            "projects": monitor.get_project_metrics()
        }
        
        print("\n/monitor page dashboard data:")
        print(json.dumps(dashboard_data, indent=2))
    
    elif args.mode == "daily-summary":
        summarizer = CronJobSummarizer(monitor)
        
        print("\nDaily Summary (Cron Job Output):")
        print(summarizer.run_daily_summary())


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement metrics aggregation queries
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:09:28.173Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement metrics aggregation queries
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2025-01-10
"""

import argparse
import json
import sqlite3
import time
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
import statistics


@dataclass
class AgentMetrics:
    agent_id: str
    last_activity: datetime
    tasks_completed: int
    tasks_in_progress: int
    idle_duration_minutes: float


@dataclass
class TaskMetrics:
    task_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    age_minutes: float
    blocked: bool
    blocked_reason: Optional[str]
    staleness_minutes: float


@dataclass
class AggregatedMetrics:
    timestamp: datetime
    active_agents_24h: int
    idle_agents: int
    total_agents: int
    daily_throughput: int
    task_age_p50_minutes: float
    task_age_p95_minutes: float
    blocked_tasks_count: int
    blocked_tasks: List[TaskMetrics]
    agent_metrics: List[AgentMetrics]


class MetricsDatabase:
    """SQLite database wrapper for SwarmPulse metrics."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT,
                created_at TIMESTAMP,
                last_activity TIMESTAMP,
                task_capacity INTEGER DEFAULT 10
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT,
                status TEXT,
                created_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                blocked INTEGER DEFAULT 0,
                blocked_reason TEXT,
                priority TEXT DEFAULT 'normal',
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                agent_id TEXT,
                status_change TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        self.conn.commit()
    
    def add_agent(self, agent_id: str, name: str, capacity: int = 10):
        """Add an agent to the database."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO agents (agent_id, name, status, created_at, last_activity, task_capacity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_id, name, "online", now, now, capacity))
        self.conn.commit()
    
    def add_task(self, task_id: str, agent_id: str, status: str, blocked: bool = False, blocked_reason: Optional[str] = None):
        """Add a task to the database."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO tasks (task_id, agent_id, status, created_at, started_at, blocked, blocked_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_id, agent_id, status, now, now if status == "in_progress" else None, 1 if blocked else 0, blocked_reason))
        self.conn.commit()
    
    def update_task_status(self, task_id: str, new_status: str, agent_id: Optional[str] = None):
        """Update task status."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        
        if new_status == "completed":
            cursor.execute("""
                UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ?
            """, (new_status, now, task_id))
        elif new_status == "in_progress":
            cursor.execute("""
                UPDATE tasks SET status = ?, started_at = ? WHERE task_id = ?
            """, (new_status, now, task_id))
        else:
            cursor.execute("""
                UPDATE tasks SET status = ? WHERE task_id = ?
            """, (new_status, task_id))
        
        self.conn.commit()
    
    def update_agent_activity(self, agent_id: str):
        """Update agent last activity timestamp."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE agents SET last_activity = ? WHERE agent_id = ?
        """, (now, agent_id))
        self.conn.commit()
    
    def set_task_blocked(self, task_id: str, blocked: bool, reason: Optional[str] = None):
        """Mark task as blocked or unblocked."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tasks SET blocked = ?, blocked_reason = ? WHERE task_id = ?
        """, (1 if blocked else 0, reason, task_id))
        self.conn.commit()
    
    def get_active_agents_24h(self) -> List[AgentMetrics]:
        """Get agents active in the last 24 hours."""
        cursor = self.conn.cursor()
        threshold = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        cursor.execute("""
            SELECT 
                a.agent_id,
                a.name,
                a.last_activity,
                COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as tasks_completed,
                COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as tasks_in_progress
            FROM agents a
            LEFT JOIN tasks t ON a.agent_id = t.agent_id
            WHERE a.last_activity >= ?
            GROUP BY a.agent_id
        """, (threshold,))
        
        agents = []
        now = datetime.utcnow()
        for row in cursor.fetchall():
            last_activity = datetime.fromisoformat(row['last_activity'])
            idle_duration = (now - last_activity).total_seconds() / 60
            agents.append(AgentMetrics(
                agent_id=row['agent_id'],
                last_activity=last_activity,
                tasks_completed=row['tasks_completed'],
                tasks_in_progress=row['tasks_in_progress'],
                idle_duration_minutes=idle_duration
            ))
        
        return agents
    
    def get_idle_agents(self, idle_threshold_minutes: int = 30) -> List[AgentMetrics]:
        """Get agents idle for more than threshold."""
        cursor = self.conn.cursor()
        threshold_time = (datetime.utcnow() - timedelta(minutes=idle_threshold_minutes)).isoformat()
        
        cursor.execute("""
            SELECT 
                a.agent_id,
                a.name,
                a.last_activity,
                COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as tasks_completed,
                COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as tasks_in_progress
            FROM agents a
            LEFT JOIN tasks t ON a.agent_id = t.agent_id
            WHERE a.last_activity < ? AND a.status = 'online'
            GROUP BY a.agent_id
        """, (threshold_time,))
        
        agents = []
        now = datetime.utcnow()
        for row in cursor.fetchall():
            last_activity = datetime.fromisoformat(row['last_activity'])
            idle_duration = (now - last_activity).total_seconds() / 60
            agents.append(AgentMetrics(
                agent_id=row['agent_id'],
                last_activity=last_activity,
                tasks_completed=row['tasks_completed'],
                tasks_in_progress=row['tasks_in_progress'],
                idle_duration_minutes=idle_duration
            ))
        
        return agents
    
    def get_daily_throughput(self, days_back: int = 1) -> int:
        """Get number of tasks completed in the last N days."""
        cursor = self.conn.cursor()
        threshold = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) as completed_count
            FROM tasks
            WHERE status = 'completed' AND completed_at >= ?
        """, (threshold,))
        
        row = cursor.fetchone()
        return row['completed_count'] if row else 0
    
    def get_task_age_percentiles(self) -> Tuple[float, float]:
        """Get p50 and p95 percentiles of task age for active tasks."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            SELECT 
                (julianday(?) - julianday(created_at)) * 24 * 60 as age_minutes
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
            ORDER BY created_at
        """, (now,))
        
        ages = [row['age_minutes'] for row in cursor.fetchall()]
        
        if not ages:
            return 0.0, 0.0
        
        p50 = statistics.median(ages)
        p95 = statistics.quantiles(ages, n=20)[18] if len(ages) > 1 else ages[0]
        
        return p50, p95
    
    def get_blocked_tasks(self) -> List[TaskMetrics]:
        """Get all blocked tasks with staleness information."""
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            SELECT 
                task_id,
                status,
                created_at,
                completed_at,
                blocked_reason,
                (julianday(?) - julianday(created_at)) * 24 * 60 as age_minutes
            FROM tasks
            WHERE blocked = 1
            ORDER BY created_at
        """, (now,))
        
        blocked_tasks = []
        for row in cursor.fetchall():
            created = datetime.fromisoformat(row['created_at'])
            completed = datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
            staleness = (datetime.utcnow() - created).total_seconds() / 60
            
            blocked_tasks.append(TaskMetrics(
                task_id=row['task_id'],
                status=row['status'],
                created_at=created,
                completed_at=completed,
                age_minutes=row['age_minutes'],
                blocked=True,
                blocked_reason=row['blocked_reason'],
                staleness_minutes=staleness
            ))
        
        return blocked_tasks
    
    def get_all_agents(self) -> List[AgentMetrics]:
        """Get all agents with their metrics."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.agent_id,
                a.name,
                a.last_activity,
                COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as tasks_completed,
                COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as tasks_in_progress
            FROM agents a
            LEFT JOIN tasks t ON a.agent_id = t.agent_id
            GROUP BY a.agent_id
        """)
        
        agents = []
        now = datetime.utcnow()
        for row in cursor.fetchall():
            last_activity = datetime.fromisoformat(row['last_activity'])
            idle_duration = (now - last_activity).total_seconds() / 60
            agents.append(AgentMetrics(
                agent_id=row['agent_id'],
                last_activity=last_activity,
                tasks_completed=row['tasks_completed'],
                tasks_in_progress=row['tasks_in_progress'],
                idle_duration_minutes=idle_duration
            ))
        
        return agents
    
    def get_total_agent_count(self) -> int:
        """Get total number of agents."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        row = cursor.fetchone()
        return row['count'] if row else 0


class MetricsAggregator:
    """Aggregates SwarmPulse metrics into actionable insights."""
    
    def __init__(self, db: MetricsDatabase):
        self.db = db
    
    def compute_metrics(self, idle_threshold_minutes: int = 30) -> AggregatedMetrics:
        """Compute all metrics and return aggregated result."""
        active_agents = self.db.get_active_agents_24h()
        idle_agents = self.db.get_idle_agents(idle_threshold_minutes)
        total_agents = self.db.get_total_agent_count()
        daily_throughput = self.db.get_daily_throughput(days_back=1)
        p50, p95 = self.db.get_task_age_percentiles()
        blocked_tasks = self.db.get_blocked_tasks()
        all_agent_metrics = self.db.get_all_agents()
        
        return AggregatedMetrics(
            timestamp=datetime.utcnow(),
            active_agents_24h=len(active_agents),
            idle_agents=len(idle_agents),
            total_agents=total_agents,
            daily_throughput=daily_throughput,
            task_age_p50_minutes=p50,
            task_age_p95_minutes=p95,
            blocked_tasks_count=len(blocked_tasks),
            blocked_tasks=blocked_tasks,
            agent_metrics=all_agent_metrics
        )
    
    def to_json(self, metrics: AggregatedMetrics) -> str:
        """Convert metrics to JSON representation."""
        return json.dumps({
            "timestamp": metrics.timestamp.isoformat(),
            "active_agents_24h": metrics.active_agents_24h,
            "idle_agents": metrics.idle_agents,
            "total_agents": metrics.total_agents,
            "daily_throughput": metrics.daily_throughput,
            "task_age_metrics": {
                "p50_minutes": round(metrics.task_age_p50_minutes, 2),
                "p95_minutes": round(metrics.task_age_p95_minutes, 2)
            },
            "blocked_tasks": {
                "count": metrics.blocked_tasks_count,
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "status": task.status,
                        "age_minutes": round(task.age_minutes, 2),
                        "staleness_minutes": round(task.staleness_minutes, 2),
                        "blocked_reason": task.blocked_reason,
                        "created_at": task.created_at.isoformat()
                    }
                    for task in metrics.blocked_tasks
                ]
            },
            "agent_metrics": [
                {
                    "agent_id": agent.agent_
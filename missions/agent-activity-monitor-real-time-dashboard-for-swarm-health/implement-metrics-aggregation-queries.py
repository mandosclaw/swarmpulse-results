#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement metrics aggregation queries
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T21:58:46.242Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Metrics Aggregation Queries for SwarmPulse Agent Activity Monitor
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024

Real-time monitoring dashboard that tracks agent activity, task throughput, and project velocity.
Implements Prisma-equivalent queries for metrics aggregation:
- Active agents (last 24h)
- Task throughput (completed per day)
- p50/p95 task age
- Blocked task list with staleness
"""

import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics
import time


@dataclass
class AgentMetrics:
    """Agent activity metrics"""
    agent_id: str
    name: str
    status: str
    last_activity: str
    tasks_completed_24h: int
    tasks_in_progress: int
    uptime_seconds: float


@dataclass
class TaskMetrics:
    """Task metrics"""
    task_id: str
    status: str
    age_seconds: float
    is_blocked: bool
    blocker_reason: str
    completed_at: str


@dataclass
class ThroughputMetrics:
    """Daily throughput metrics"""
    date: str
    tasks_completed: int
    avg_completion_time_seconds: float
    active_agents_count: int


@dataclass
class BlockedTaskMetrics:
    """Blocked task details"""
    task_id: str
    project_id: str
    status: str
    blocker_reason: str
    age_seconds: float
    created_at: str
    blocked_at: str
    assignee_id: str


class MetricsDatabase:
    """Lightweight SQLite database for agent and task metrics"""
    
    def __init__(self, db_path: str = "swarm_metrics.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'idle',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_tasks_completed INTEGER DEFAULT 0,
                current_task_id TEXT
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                is_blocked INTEGER DEFAULT 0,
                blocker_reason TEXT,
                blocked_at TIMESTAMP
            )
        """)
        
        # Task activity log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)
        
        # Agent activity log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_active_agents_24h(self) -> List[AgentMetrics]:
        """
        Query: Active agents in the last 24 hours
        Returns agents with activity in the last 24h
        """
        cursor = self.conn.cursor()
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        cursor.execute("""
            SELECT 
                a.agent_id,
                a.name,
                a.status,
                a.last_activity,
                COUNT(CASE WHEN t.status = 'completed' AND t.completed_at > ? THEN 1 END) as tasks_completed_24h,
                COUNT(CASE WHEN t.status = 'in_progress' AND t.assigned_to = a.agent_id THEN 1 END) as tasks_in_progress,
                CAST((julianday('now') - julianday(a.created_at)) * 86400 AS INTEGER) as uptime_seconds
            FROM agents a
            LEFT JOIN tasks t ON a.agent_id = t.assigned_to
            WHERE a.last_activity > ?
            GROUP BY a.agent_id
            ORDER BY a.last_activity DESC
        """, (twenty_four_hours_ago, twenty_four_hours_ago))
        
        agents = []
        for row in cursor.fetchall():
            agents.append(AgentMetrics(
                agent_id=row[0],
                name=row[1],
                status=row[2],
                last_activity=row[3],
                tasks_completed_24h=row[4],
                tasks_in_progress=row[5],
                uptime_seconds=row[6]
            ))
        
        return agents
    
    def get_task_throughput_daily(self, days: int = 1) -> List[ThroughputMetrics]:
        """
        Query: Task throughput metrics per day
        Computes completed tasks per day and avg completion time
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(t.completed_at) as completion_date,
                COUNT(t.task_id) as tasks_completed,
                AVG(CAST((julianday(t.completed_at) - julianday(t.started_at)) * 86400 AS FLOAT)) as avg_completion_seconds,
                COUNT(DISTINCT t.assigned_to) as active_agents
            FROM tasks t
            WHERE t.status = 'completed'
            AND t.completed_at > datetime('now', '-' || ? || ' days')
            GROUP BY DATE(t.completed_at)
            ORDER BY completion_date DESC
        """, (days,))
        
        throughputs = []
        for row in cursor.fetchall():
            throughputs.append(ThroughputMetrics(
                date=row[0],
                tasks_completed=row[1],
                avg_completion_time_seconds=row[2] if row[2] else 0.0,
                active_agents_count=row[3]
            ))
        
        return throughputs
    
    def get_task_age_percentiles(self) -> Dict[str, float]:
        """
        Query: Task age percentiles (p50, p95)
        Computes for tasks currently in progress or pending
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                CAST((julianday('now') - julianday(t.created_at)) * 86400 AS FLOAT) as age_seconds
            FROM tasks t
            WHERE t.status IN ('pending', 'in_progress')
            ORDER BY age_seconds
        """)
        
        ages = [row[0] for row in cursor.fetchall()]
        
        if not ages:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        return {
            "p50": statistics.median
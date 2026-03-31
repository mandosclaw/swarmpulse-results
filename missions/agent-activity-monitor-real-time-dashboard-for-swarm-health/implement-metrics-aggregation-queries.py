#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement metrics aggregation queries
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:38:43.466Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement metrics aggregation queries
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2025-01-21
"""

import json
import sqlite3
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import statistics
import time

class MetricsAggregator:
    """Aggregates metrics for agent activity, task throughput, and project velocity."""
    
    def __init__(self, db_path: str = ":memory:"):
        """Initialize the metrics aggregator with a database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize database schema for agents, tasks, and activity logs."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_heartbeat TIMESTAMP NOT NULL
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                blocked_reason TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                details TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
        
        self.conn.commit()
    
    def add_agent(self, agent_id: str, name: str, status: str = "idle") -> None:
        """Add or update an agent in the database."""
        now = datetime.utcnow().isoformat()
        self.cursor.execute("""
            INSERT OR REPLACE INTO agents (id, name, status, created_at, last_heartbeat)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, name, status, now, now))
        self.conn.commit()
    
    def add_task(self, task_id: str, agent_id: str, project_id: str, 
                status: str = "pending", created_at: str = None) -> None:
        """Add a task to the database."""
        if created_at is None:
            created_at = datetime.utcnow().isoformat()
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO tasks 
            (id, agent_id, project_id, status, created_at, started_at, completed_at, blocked_reason)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
        """, (task_id, agent_id, project_id, status, created_at))
        self.conn.commit()
    
    def update_task_status(self, task_id: str, status: str, 
                          started_at: str = None, completed_at: str = None,
                          blocked_reason: str = None) -> None:
        """Update task status and timestamps."""
        self.cursor.execute("""
            UPDATE tasks 
            SET status = ?, started_at = ?, completed_at = ?, blocked_reason = ?
            WHERE id = ?
        """, (status, started_at, completed_at, blocked_reason, task_id))
        self.conn.commit()
    
    def update_agent_heartbeat(self, agent_id: str, status: str = None) -> None:
        """Update agent heartbeat timestamp."""
        now = datetime.utcnow().isoformat()
        if status:
            self.cursor.execute("""
                UPDATE agents SET last_heartbeat = ?, status = ? WHERE id = ?
            """, (now, status, agent_id))
        else:
            self.cursor.execute("""
                UPDATE agents SET last_heartbeat = ? WHERE id = ?
            """, (now, agent_id))
        self.conn.commit()
    
    def log_activity(self, agent_id: str, event_type: str, details: str = None) -> None:
        """Log an agent activity event."""
        now = datetime.utcnow().isoformat()
        self.cursor.execute("""
            INSERT INTO activity_log (agent_id, event_type, timestamp, details)
            VALUES (?, ?, ?, ?)
        """, (agent_id, event_type, now, details))
        self.conn.commit()
    
    def get_active_agents_24h(self) -> Dict[str, Any]:
        """Query active agents in the last 24 hours."""
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        self.cursor.execute("""
            SELECT id, name, status, last_heartbeat
            FROM agents
            WHERE last_heartbeat > ?
            ORDER BY last_heartbeat DESC
        """, (cutoff_time,))
        
        rows = self.cursor.fetchall()
        active_agents = []
        
        for row in rows:
            agent_id, name, status, last_heartbeat = row
            active_agents.append({
                "id": agent_id,
                "name": name,
                "status": status,
                "last_heartbeat": last_heartbeat
            })
        
        return {
            "count": len(active_agents),
            "agents": active_agents,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_task_throughput(self, days: int = 1) -> Dict[str, Any]:
        """Query task throughput (completed tasks per day)."""
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        self.cursor.execute("""
            SELECT COUNT(*) as completed_count, 
                   DATE(completed_at) as completion_date
            FROM tasks
            WHERE status = 'completed' AND completed_at > ?
            GROUP BY DATE(completed_at)
            ORDER BY completion_date DESC
        """, (cutoff_time,))
        
        rows = self.cursor.fetchall()
        daily_stats = []
        total_completed = 0
        
        for row in rows:
            count, date = row
            total_completed += count
            daily_stats.append({
                "date": date,
                "completed_tasks": count
            })
        
        avg_per_day = total_completed / max(days, 1)
        
        return {
            "period_days": days,
            "total_completed": total_completed,
            "average_per_day": avg_per_day,
            "daily_breakdown": daily_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_task_age_percentiles(self) -> Dict[str, Any]:
        """Query p50 and p95 task age for incomplete tasks."""
        now = datetime.utcnow()
        
        self.cursor.execute("""
            SELECT id, created_at
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
            ORDER BY created_at ASC
        """)
        
        rows = self.cursor.fetchall()
        task_ages = []
        
        for row in rows:
            task_id, created_at = row
            created = datetime.fromisoformat(created_at)
            age_seconds = (now - created).total_seconds()
            task_ages.append({
                "task_id": task_id,
                "age_seconds": age_seconds,
                "age_hours": age_seconds / 3600,
                "created_at": created_at
            })
        
        if not task_ages:
            return {
                "total_incomplete": 0,
                "p50_age_hours": 0,
                "p95_age_hours": 0,
                "min_age_hours": 0,
                "max_age_hours": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        ages_in_hours = [t["age_hours"] for t in task_ages]
        ages_in_hours.sort()
        
        p50 = statistics.median(ages_in_hours)
        p95 = ages_in_hours[int(len(ages_in_hours) * 0.95)] if len(ages_in_hours) > 1 else ages_in_hours[0]
        
        return {
            "total_incomplete": len(task_ages),
            "p50_age_hours": round(p50, 2),
            "p95_age_hours": round(p95, 2),
            "min_age_hours": round(min(ages_in_hours), 2),
            "max_age_hours": round(max(ages_in_hours), 2),
            "oldest_tasks": task_ages[-5:] if len(task_ages) > 5 else task_ages,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_blocked_tasks(self) -> Dict[str, Any]:
        """Query blocked tasks with staleness information."""
        now = datetime.utcnow()
        
        self.cursor.execute("""
            SELECT id, agent_id, project_id, created_at, blocked_reason
            FROM tasks
            WHERE status = 'blocked'
            ORDER BY created_at ASC
        """)
        
        rows = self.cursor.fetchall()
        blocked_tasks = []
        
        for row in rows:
            task_id, agent_id, project_id, created_at, blocked_reason = row
            created = datetime.fromisoformat(created_at)
            staleness_seconds = (now - created).total_seconds()
            
            blocked_tasks.append({
                "task_id": task_id,
                "agent_id": agent_id,
                "project_id": project_id,
                "created_at": created_at,
                "blocked_reason": blocked_reason or "unknown",
                "staleness_hours": round(staleness_seconds / 3600, 2),
                "staleness_seconds": staleness_seconds
            })
        
        blocked_tasks.sort(key=lambda x: x["staleness_seconds"], reverse=True)
        
        return {
            "total_blocked": len(blocked_tasks),
            "blocked_tasks": blocked_tasks,
            "oldest_blocked": blocked_tasks[0] if blocked_tasks else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_idle_agents(self) -> Dict[str, Any]:
        """Query idle agents and their inactivity duration."""
        now = datetime.utcnow()
        cutoff_time = (now - timedelta(minutes=5)).isoformat()
        
        self.cursor.execute("""
            SELECT id, name, last_heartbeat, status
            FROM agents
            WHERE last_heartbeat < ? OR status = 'idle'
            ORDER BY last_heartbeat ASC
        """, (cutoff_time,))
        
        rows = self.cursor.fetchall()
        idle_agents = []
        
        for row in rows:
            agent_id, name, last_heartbeat, status = row
            last_beat = datetime.fromisoformat(last_heartbeat)
            inactivity_seconds = (now - last_beat).total_seconds()
            
            idle_agents.append({
                "agent_id": agent_id,
                "name": name,
                "status": status,
                "last_heartbeat": last_heartbeat,
                "inactivity_minutes": round(inactivity_seconds / 60, 2),
                "inactivity_seconds": inactivity_seconds
            })
        
        idle_agents.sort(key=lambda x: x["inactivity_seconds"], reverse=True)
        
        return {
            "total_idle": len(idle_agents),
            "idle_agents": idle_agents,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_bottlenecks(self) -> Dict[str, Any]:
        """Identify bottlenecks in task processing."""
        self.cursor.execute("""
            SELECT agent_id, COUNT(*) as task_count,
                   SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked_count
            FROM tasks
            WHERE status IN ('in_progress', 'blocked')
            GROUP BY agent_id
            HAVING task_count > 0
            ORDER BY task_count DESC
        """)
        
        rows = self.cursor.fetchall()
        bottlenecks = []
        
        for row in rows:
            agent_id, task_count, blocked_count = row
            blocked_count = blocked_count or 0
            
            self.cursor.execute("""
                SELECT name FROM agents WHERE id = ?
            """, (agent_id,))
            
            agent_name_row = self.cursor.fetchone()
            agent_name = agent_name_row[0] if agent_name_row else "unknown"
            
            bottleneck_severity = (blocked_count / task_count * 100) if task_count > 0 else 0
            
            bottlenecks.append({
                "agent_id": agent_id,
                "agent_name": agent_name,
                "active_tasks": task_count,
                "blocked_tasks": blocked_count,
                "bottleneck_severity": round(bottleneck_severity, 2)
            })
        
        return {
            "total_bottlenecks": len(bottlenecks),
            "bottlenecks": bottlenecks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Aggregate all metrics into a comprehensive dashboard report."""
        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "active_agents_24h": self.get_active_agents_24h(),
            "task_throughput": self.get_task_throughput(days=1),
            "task_age_percentiles": self.get_task_age_percentiles(),
            "blocked_tasks": self.get_blocked_tasks(),
            "idle_agents": self.get_idle_agents(),
            "bottlenecks": self.get_bottlenecks()
        }
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()


def generate_sample_data(aggregator: MetricsAggregator) -> None:
    """Generate sample data for testing and demonstration."""
    now = datetime.utcnow()
    
    # Add agents
    agents = [
        ("agent-001", "Worker Alpha", "active"),
        ("agent-002", "Worker Beta", "idle"),
        ("agent-003", "Worker Gamma", "active"),
        ("agent-004", "Worker Delta", "idle"),
    ]
    
    for agent_id, name, status in agents:
        aggregator.add_agent(agent_id, name, status)
        if status == "active":
            aggregator.update_agent_heartbeat(agent_id, "active")
        else:
            old_time = (now - timedelta(minutes=30)).isoformat()
            aggregator.cursor.execute(
                "UPDATE agents SET last_heartbeat = ? WHERE id = ?",
                (old_time, agent_id)
            )
            aggregator.conn.commit()
    
    # Add tasks
    task_configs = [
        ("task-001", "agent-001", "project-A", "completed", -48, -24),
        ("task-002", "agent-001", "project-A", "completed", -24, -18),
        ("task-003", "agent-002", "project-B", "completed", -24, -12),
        ("task-004", "agent-003", "project-A", "in_progress", -6, None),
        ("task-005", "agent-003", "project-C", "pending", -3, None),
        ("task-006", "agent-001", "project-B", "blocked", -12, None),
        ("task-007", "agent-002", "project-A", "blocked", -8, None),
        ("task-008", "agent-004", "project-C", "pending", -2, None),
    ]
    
    for task_id, agent_id, project_id, status, created_hours_ago, completed_hours_ago in task_configs:
        created_at = (now - timedelta(hours=abs(created_hours_ago))).isoformat()
        aggregator.add_task(task_id, agent_id, project_id, status, created_at)
        
        if status == "completed":
            started_at = (now - timedelta(hours=abs(created_hours_ago) - 2)).isoformat()
            completed_at = (now - timedelta(hours=abs(completed_hours_ago))).isoformat()
            aggregator.update_task_status(task_id, status, started_at, completed_at)
        elif status == "in_progress":
            started_at = (now - timedelta(hours=abs(created_hours_ago) - 1)).isoformat()
            aggregator.update_task_status(task_id, status, started_at)
        elif status == "blocked":
            aggregator.update_task_status(
                task_id, status, 
                blocked_reason="Dependency on task-999 not resolved"
            )


def main():
    """Main entry point for the metrics aggregator CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Activity Metrics Aggregator for SwarmPulse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --db metrics.db --metrics all
  python3 solution.py --metrics active-agents
  python3 solution.py --metrics task-throughput --days 7
  python3 solution.py --metrics blocked-tasks --format json
        """
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default=":memory:",
        help="Database path (default: in-memory)"
    )
    
    parser.add_argument(
        "--metrics",
        type=str,
        choices=["all", "active-agents", "task-throughput", "task-age", 
                "blocked-tasks", "idle-agents", "bottlenecks"],
        default="all",
        help="Metrics to compute (default: all)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days for throughput analysis (default: 1)"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "pretty"],
        default="pretty",
        help="Output format (default: pretty)"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with sample/generated test data"
    )
    
    args = parser.parse_args()
    
    aggregator = MetricsAggregator(db_path=args.db)
    
    if args.demo:
        generate_sample_data(aggregator)
    
    try:
        if args.metrics == "all":
            result = aggregator.get_comprehensive_metrics()
        elif args.metrics == "active-agents":
            result = aggregator.get_active_agents_24h()
        elif args.metrics == "task-throughput":
            result = aggregator.get_task_throughput(days=args.days)
        elif args.metrics == "task-age":
            result = aggregator.get_task_age_percentiles()
        elif args.metrics == "blocked-tasks":
            result = aggregator.get_blocked_tasks()
        elif args.metrics == "idle-agents":
            result = aggregator.get_idle_agents()
        elif args.metrics == "bottlenecks":
            result = aggregator.get_bottlenecks()
        else:
            result = {}
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
    
    finally:
        aggregator.close()


if __name__ == "__main__":
    main()
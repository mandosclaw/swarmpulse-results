#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add daily summary cron job
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:09:57.215Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Add daily summary cron job
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024
"""

import argparse
import json
import sqlite3
import sys
import time
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import random
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    agent_id: str
    tasks_completed: int
    tasks_failed: int
    avg_task_duration: float
    uptime_minutes: int
    last_heartbeat: str


@dataclass
class DailySummary:
    date: str
    total_agents: int
    total_tasks_completed: int
    total_tasks_failed: int
    avg_throughput: float
    idle_agents: int
    blocked_tasks: int
    bottleneck_agents: List[str]
    summary_message: str
    posted_at: str


class MetricsDatabase:
    """Manages metrics data in SQLite"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Agent metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                avg_task_duration REAL DEFAULT 0.0,
                uptime_minutes INTEGER DEFAULT 0,
                last_heartbeat TEXT NOT NULL,
                UNIQUE(agent_id, timestamp)
            )
        ''')
        
        # Task tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                agent_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                duration_seconds REAL,
                blocked INTEGER DEFAULT 0
            )
        ''')
        
        # Daily summaries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_agents INTEGER,
                total_tasks_completed INTEGER,
                total_tasks_failed INTEGER,
                avg_throughput REAL,
                idle_agents INTEGER,
                blocked_tasks INTEGER,
                bottleneck_agents TEXT,
                summary_message TEXT,
                posted_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_agent_metrics(self, agent_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get metrics for a specific agent in date range"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                agent_id,
                SUM(tasks_completed) as total_completed,
                SUM(tasks_failed) as total_failed,
                AVG(avg_task_duration) as avg_duration,
                MAX(uptime_minutes) as max_uptime,
                MAX(last_heartbeat) as last_heartbeat
            FROM agent_metrics
            WHERE agent_id = ? AND timestamp BETWEEN ? AND ?
            GROUP BY agent_id
        ''', (agent_id, start_date, end_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'agent_id': row[0],
                'tasks_completed': row[1] or 0,
                'tasks_failed': row[2] or 0,
                'avg_task_duration': row[3] or 0.0,
                'uptime_minutes': row[4] or 0,
                'last_heartbeat': row[5]
            }
        return {}
    
    def get_all_agents(self, timestamp: str) -> List[str]:
        """Get list of all active agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT agent_id FROM agent_metrics
            WHERE timestamp >= datetime(?, '-1 day')
            ORDER BY agent_id
        ''', (timestamp,))
        
        agents = [row[0] for row in cursor.fetchall()]
        conn.close()
        return agents
    
    def get_idle_agents(self, timestamp: str, idle_threshold_minutes: int = 30) -> List[str]:
        """Get agents that haven't had activity recently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT agent_id FROM agent_metrics
            WHERE last_heartbeat < datetime(?, '-' || ? || ' minutes')
            ORDER BY agent_id
        ''', (timestamp, idle_threshold_minutes))
        
        agents = [row[0] for row in cursor.fetchall()]
        conn.close()
        return agents
    
    def get_blocked_tasks(self, start_date: str, end_date: str) -> int:
        """Count blocked tasks in date range"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks
            WHERE blocked = 1 AND created_at BETWEEN ? AND ?
        ''', (start_date, end_date))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_task_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get overall task statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                AVG(duration_seconds) as avg_duration
            FROM tasks
            WHERE created_at BETWEEN ? AND ?
        ''', (start_date, end_date))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total': row[0] or 0,
            'completed': row[1] or 0,
            'failed': row[2] or 0,
            'avg_duration': row[3] or 0.0
        }
    
    def save_daily_summary(self, summary: DailySummary) -> bool:
        """Save daily summary to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summaries
                (date, total_agents, total_tasks_completed, total_tasks_failed,
                 avg_throughput, idle_agents, blocked_tasks, bottleneck_agents,
                 summary_message, posted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary.date,
                summary.total_agents,
                summary.total_tasks_completed,
                summary.total_tasks_failed,
                summary.avg_throughput,
                summary.idle_agents,
                summary.blocked_tasks,
                json.dumps(summary.bottleneck_agents),
                summary.summary_message,
                summary.posted_at
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            conn.close()
            return False
    
    def insert_agent_metric(self, metric: AgentMetrics, timestamp: str) -> bool:
        """Insert agent metric record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO agent_metrics
                (agent_id, timestamp, tasks_completed, tasks_failed,
                 avg_task_duration, uptime_minutes, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.agent_id,
                timestamp,
                metric.tasks_completed,
                metric.tasks_failed,
                metric.avg_task_duration,
                metric.uptime_minutes,
                metric.last_heartbeat
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error inserting metric: {e}")
            conn.close()
            return False
    
    def insert_task(self, task_id: str, agent_id: str, status: str, 
                   created_at: str, completed_at: Optional[str] = None,
                   duration_seconds: Optional[float] = None, blocked: int = 0) -> bool:
        """Insert task record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tasks
                (task_id, agent_id, status, created_at, completed_at, 
                 duration_seconds, blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, agent_id, status, created_at, completed_at,
                  duration_seconds, blocked))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error inserting task: {e}")
            conn.close()
            return False


class DailySummaryCron:
    """Handles daily summary computation and posting"""
    
    def __init__(self, db_path: str = "metrics.db", 
                 forum_post_enabled: bool = True,
                 forum_url: str = "http://localhost:8000"):
        self.db = MetricsDatabase(db_path)
        self.forum_post_enabled = forum_post_enabled
        self.forum_url = forum_url
    
    def compute_daily_summary(self, target_date: Optional[str] = None) -> DailySummary:
        """Compute metrics for a specific day (default: yesterday)"""
        if target_date is None:
            target_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        start_time = f"{target_date}T00:00:00Z"
        end_time = f"{target_date}T23:59:59Z"
        
        # Get all agents and their metrics
        agents = self.db.get_all_agents(start_time)
        total_agents = len(agents)
        
        agent_metrics_list = []
        total_completed = 0
        total_failed = 0
        
        for agent_id in agents:
            metrics = self.db.get_agent_metrics(agent_id, start_time, end_time)
            if metrics:
                agent_metrics_list.append(metrics)
                total_completed += metrics.get('tasks_completed', 0)
                total_failed += metrics.get('tasks_failed', 0)
        
        # Get task statistics
        task_stats = self.db.get_task_stats(start_time, end_time)
        
        # Calculate throughput (tasks per hour)
        hours_in_day = 24
        avg_throughput = task_stats['completed'] / hours_in_day if task_stats['completed'] > 0 else 0.0
        
        # Get idle agents
        idle_agents = self.db.get_idle_agents(start_time, idle_threshold_minutes=60)
        
        # Get blocked tasks
        blocked_tasks = self.db.get_blocked_tasks(start_time, end_time)
        
        # Identify bottleneck agents (high task failure rate)
        bottleneck_agents = []
        for metrics in agent_metrics_list:
            total = metrics['tasks_completed'] + metrics['tasks_failed']
            if total > 5:  # Only consider agents with sufficient activity
                failure_rate = metrics['tasks_failed'] / total
                if failure_rate > 0.3:  # 30% failure rate threshold
                    bottleneck_agents.append(metrics['agent_id'])
        
        # Generate summary message
        summary_message = self._generate_summary_message(
            target_date, total_agents, total_completed, total_failed,
            avg_throughput, len(idle_agents), blocked_tasks, bottleneck_agents
        )
        
        summary = DailySummary(
            date=target_date,
            total_agents=total_agents,
            total_tasks_completed=total_completed,
            total_tasks_failed=total_failed,
            avg_throughput=round(avg_throughput, 2),
            idle_agents=len(idle_agents),
            blocked_tasks=blocked_tasks,
            bottleneck_agents=bottleneck_agents,
            summary_message=summary_message,
            posted_at=datetime.utcnow().isoformat() + "Z"
        )
        
        return summary
    
    def _generate_summary_message(self, date: str, total_agents: int,
                                 total_completed: int, total_failed: int,
                                 avg_throughput: float, idle_agents: int,
                                 blocked_tasks: int, bottleneck_agents: List[str]) -> str:
        """Generate human-readable summary message"""
        lines = [
            f"📊 **SwarmPulse Daily Digest - {date}**",
            "",
            "**Activity Summary:**",
            f"• Total Agents: {total_agents}",
            f"• Tasks Completed: {total_completed}",
            f"• Tasks Failed: {total_failed}",
            f"• Average Throughput: {avg_throughput:.2f} tasks/hour",
            "",
            "**Health Indicators:**",
            f"• Idle Agents: {idle_agents}",
            f"• Blocked Tasks: {blocked_tasks}",
        ]
        
        if bottleneck_agents:
            lines.append("• Bottleneck Agents (high failure rate):")
            for agent_id in bottleneck_agents[:5]:  # Show top 5
                lines.append(f"  - {agent_id}")
        else:
            lines.append("• Bottleneck Agents: None detected")
        
        lines.extend([
            "",
            "**Recommendations:**",
        ])
        
        if idle_agents > total_agents * 0.2:
            lines.append("• Consider redistributing load; too many idle agents")
        
        if blocked_tasks > 10:
            lines.append("• Investigate blocked tasks; potential bottlenecks exist")
        
        if total_failed > total_completed * 0.1:
            lines.append("• High failure rate detected; review agent configurations")
        
        if not lines[-1].startswith("•"):
            lines.append("• System operating within normal parameters")
        
        return "\n".join(lines)
    
    def post_to_forum(self, summary: DailySummary) -> bool:
        """Post summary to forum's daily-digest thread"""
        if not self.forum_post_enabled:
            logger.info("Forum posting disabled; skipping post")
            return True
        
        try:
            import urllib.request
            import urllib.error
            
            endpoint = f"{self.forum_url}/api/forum/daily-digest"
            
            payload = json.dumps({
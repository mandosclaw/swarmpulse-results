#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T21:58:59.274Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Agent Activity Monitor — Real-time Dashboard for Swarm Health (Deploy and verify)
MISSION: Build a live monitoring dashboard that tracks agent activity, task throughput, and project velocity
AGENT: @bolt
DATE: 2025-01-20
"""

import argparse
import json
import time
import threading
import sqlite3
import random
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
import statistics
import sys


class MetricsDatabase:
    """SQLite-based metrics storage for agent activity."""
    
    def __init__(self, db_path="metrics.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                status TEXT NOT NULL,
                task_count INTEGER DEFAULT 0,
                idle_duration INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                status TEXT NOT NULL,
                blocked INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_tasks INTEGER DEFAULT 0,
                avg_duration REAL DEFAULT 0,
                blocked_tasks INTEGER DEFAULT 0,
                idle_agents INTEGER DEFAULT 0,
                throughput_per_hour REAL DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_agent_activity(self, agent_id, status, task_count=0, idle_duration=0):
        """Record agent activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = int(time.time())
        
        cursor.execute("""
            INSERT INTO agent_activity (agent_id, timestamp, status, task_count, idle_duration)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, timestamp, status, task_count, idle_duration))
        
        conn.commit()
        conn.close()
    
    def record_task_metric(self, task_id, agent_id, duration, status, blocked=0):
        """Record task execution metric."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = int(time.time())
        
        cursor.execute("""
            INSERT INTO task_metrics (task_id, agent_id, timestamp, duration, status, blocked)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, agent_id, timestamp, duration, status, blocked))
        
        conn.commit()
        conn.close()
    
    def get_recent_metrics(self, minutes=60):
        """Get metrics from last N minutes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff_time = int(time.time()) - (minutes * 60)
        
        cursor.execute("""
            SELECT agent_id, timestamp, status, task_count, idle_duration
            FROM agent_activity
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff_time,))
        
        activities = cursor.fetchall()
        
        cursor.execute("""
            SELECT task_id, agent_id, timestamp, duration, status, blocked
            FROM task_metrics
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff_time,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        return {
            "activities": activities,
            "tasks": tasks,
            "cutoff_time": cutoff_time
        }
    
    def compute_daily_summary(self, target_date=None):
        """Compute and store daily summary metrics."""
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        next_date = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        start_ts = int(datetime.strptime(target_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(next_date, "%Y-%m-%d").timestamp())
        
        cursor.execute("""
            SELECT COUNT(*), AVG(duration), SUM(blocked)
            FROM task_metrics
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_ts, end_ts))
        
        result = cursor.fetchone()
        total_tasks = result[0] or 0
        avg_duration = result[1] or 0
        blocked_tasks = result[2] or 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT agent_id)
            FROM agent_activity
            WHERE timestamp >= ? AND timestamp < ? AND status = 'idle'
        """, (start_ts, end_ts))
        
        idle_agents = cursor.fetchone()[0] or 0
        
        throughput_per_hour = (total_tasks / 24) if total_tasks > 0 else 0
        
        cursor.execute("""
            INSERT OR REPLACE INTO daily_summary 
            (date, total_tasks, avg_duration, blocked_tasks, idle_agents, throughput_per_hour)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (target_date, total_tasks, avg_duration, blocked_tasks, idle_agents, throughput_per_hour))
        
        conn.commit()
        
        cursor.execute("""
            SELECT * FROM daily_summary WHERE date = ?
        """, (target_date,))
        
        summary = cursor.fetchone()
        conn.close()
        
        return {
            "date": target_date,
            "total_tasks": total_tasks,
            "avg_duration": round(avg_duration, 2),
            "blocked_tasks": blocked_tasks,
            "idle_agents": idle_agents,
            "throughput_per_hour": round(throughput_per_hour, 2)
        }
    
    def get_dashboard_data(self):
        """Get comprehensive dashboard data."""
        metrics = self.get_recent_metrics(minutes=120)
        
        agent_stats = defaultdict(lambda: {"tasks": 0, "idle_time": 0, "status": "unknown"})
        
        for activity in metrics["activities"]:
            agent_id = activity[0]
            agent_stats[agent_id]["tasks"] += activity[3]
            agent_stats[agent_id]["idle_time"] += activity[4]
            agent_stats[agent_id]["status"] = activity[2]
        
        blocked_count = sum(1 for task in metrics["tasks"] if task[5] == 1)
        task_durations = [task[3] for task in metrics["tasks"]]
        
        avg_duration = statistics.mean(task_durations) if task_durations else 0
        throughput = len(metrics["tasks"]) / 2
        
        idle_agents = sum(1 for stats in agent_stats.values() if stats["status"] == "idle")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": dict(agent_stats),
            "metrics": {
                "total_agents
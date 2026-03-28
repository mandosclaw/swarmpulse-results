#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design /api/metrics endpoint schema
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T21:58:45.180Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Design /api/metrics endpoint schema
Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
Agent: @bolt
Date: 2024-01-15

Implements a live monitoring dashboard backend with OpenAPI-documented /api/metrics endpoint,
real-time agent activity tracking, task throughput metrics, project velocity calculations,
and blocked task detection. Includes a /monitor page, cron-based daily summaries, and
structured JSON responses for SwarmPulse agent coordination.
"""

import argparse
import json
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from collections import defaultdict
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import math


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"


class MetricsDatabase:
    """SQLite-backed metrics storage with thread-safe operations"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_heartbeat INTEGER,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    current_task_id TEXT,
                    created_at INTEGER
                )
            """)
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    agent_id TEXT,
                    status TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    created_at INTEGER,
                    started_at INTEGER,
                    completed_at INTEGER,
                    blocked_reason TEXT,
                    blocked_at INTEGER,
                    dependencies TEXT
                )
            """)
            
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at INTEGER,
                    total_tasks INTEGER DEFAULT 0
                )
            """)
            
            # Metrics snapshots (for daily summaries)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp INTEGER,
                    agent_count INTEGER,
                    task_count INTEGER,
                    completed_count INTEGER,
                    failed_count INTEGER,
                    blocked_count INTEGER,
                    avg_task_duration REAL,
                    throughput REAL
                )
            """)
            
            conn.commit()
            conn.close()
    
    def add_agent(self, agent_id: str, name: str) -> None:
        """Add or update an agent"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = int(time.time())
            
            cursor.execute("""
                INSERT OR REPLACE INTO agents
                (agent_id, name, status, last_heartbeat, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, name, AgentStatus.ACTIVE.value, now, now))
            
            conn.commit()
            conn.close()
    
    def update_agent_status(self, agent_id: str, status: AgentStatus, current_task_id: Optional[str] = None) -> None:
        """Update agent status"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = int(time.time())
            
            cursor.execute("""
                UPDATE agents
                SET status = ?, last_heartbeat = ?, current_task_id = ?
                WHERE agent_id = ?
            """, (status.value, now, current_task_id, agent_id))
            
            conn.commit()
            conn.close()
    
    def create_project(self, project_id: str, name: str, description: str) -> None:
        """Create a new project"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = int(time.time())
            
            cursor.execute("""
                INSERT OR REPLACE INTO projects
                (project_id, name, description, created_at)
                VALUES (?, ?, ?, ?)
            """, (project_id, name, description, now))
            
            conn.commit()
            conn.close()
    
    def add_task(self, task_id: str, project_id: str, title: str, description: str,
                 dependencies: Optional[List[str]] = None) -> None:
        """Add a new task"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = int(time.time())
            deps_json = json.dumps(dependencies) if dependencies else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (task_id, project_id, status, title, description, created_at, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, project_id, TaskStatus.PENDING.value, title, description, now, deps_json))
            
            # Increment project task count
            cursor.execute("UPDATE projects SET total_tasks = total_tasks + 1 WHERE project_id = ?", (project_id,))
            
            conn.commit()
            conn.close()
    
    def update_task_status(self, task_id: str, status: TaskStatus, agent_id: Optional[str] = None,
                          blocked_reason: Optional[str] = None) -> None:
        """Update task status"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = int(time.time())
            
            if status == TaskStatus.IN_PROGRESS:
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, agent_id = ?, started_at = ?
                    WHERE task_id = ?
                """, (status.value, agent_id, now, task_id))
            elif status == TaskStatus.COMPLETED:
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, completed_at = ?
                    WHERE task_id = ?
                """, (status.value, now, task_id))
                # Update agent stats
                if agent_id:
                    cursor.execute("""
                        UPDATE agents
                        SET tasks_completed = tasks_completed + 1
                        WHERE agent_id = ?
                    """, (agent_id,))
            elif status == TaskStatus.FAILED:
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, completed_at = ?
                    WHERE task_id = ?
                """, (status.value, now, task_id))
                # Update agent stats
                if agent_id:
                    cursor.execute("""
                        UPDATE agents
                        SET tasks_failed = tasks_failed + 1
                        WHERE agent_id = ?
                    """, (
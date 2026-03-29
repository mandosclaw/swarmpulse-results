#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:09:56.539Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Agent Activity Monitor — Real-time Dashboard for Swarm Health
MISSION: Deploy and verify /monitor page, /api/metrics endpoint, and cron job
AGENT: @bolt
DATE: 2024
"""

import json
import sqlite3
import argparse
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re

@dataclass
class AgentMetric:
    agent_id: str
    status: str
    tasks_completed: int
    tasks_blocked: int
    uptime_minutes: int
    last_heartbeat: str
    cpu_usage: float
    memory_usage: float

@dataclass
class TaskMetric:
    task_id: str
    agent_id: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: int
    project_id: str

@dataclass
class ProjectVelocity:
    project_id: str
    tasks_completed_today: int
    tasks_completed_week: int
    avg_task_duration: float
    blocked_tasks: int
    velocity_score: float

class SwarmMetricsDB:
    def __init__(self, db_path: str = "swarm_metrics.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    status TEXT,
                    tasks_completed INTEGER,
                    tasks_blocked INTEGER,
                    uptime_minutes INTEGER,
                    last_heartbeat TEXT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    status TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration_seconds INTEGER,
                    project_id TEXT,
                    created_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    summary_date TEXT PRIMARY KEY,
                    total_agents INTEGER,
                    active_agents INTEGER,
                    idle_agents INTEGER,
                    total_tasks INTEGER,
                    completed_tasks INTEGER,
                    blocked_tasks INTEGER,
                    avg_task_duration REAL,
                    system_health_score REAL,
                    created_at TEXT
                )
            ''')
            
            conn.commit()

    def insert_agent(self, metric: AgentMetric):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO agents 
                (agent_id, status, tasks_completed, tasks_blocked, uptime_minutes, 
                 last_heartbeat, cpu_usage, memory_usage, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.agent_id, metric.status, metric.tasks_completed,
                metric.tasks_blocked, metric.uptime_minutes, metric.last_heartbeat,
                metric.cpu_usage, metric.memory_usage, datetime.utcnow().isoformat()
            ))
            conn.commit()

    def insert_task(self, metric: TaskMetric):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tasks
                (task_id, agent_id, status, start_time, end_time, duration_seconds, project_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.task_id, metric.agent_id, metric.status, metric.start_time,
                metric.end_time, metric.duration_seconds, metric.project_id,
                datetime.utcnow().isoformat()
            ))
            conn.commit()

    def get_agents(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM agents ORDER BY updated_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks(self, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_status(self, status: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', (status,))
            return [dict(row) for row in cursor.fetchall()]

    def get_project_velocity(self, project_id: str) -> ProjectVelocity:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            today = datetime.utcnow().date().isoformat()
            week_ago = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM tasks 
                WHERE project_id = ? AND status = 'completed' AND DATE(created_at) = ?
            ''', (project_id, today))
            tasks_today = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM tasks 
                WHERE project_id = ? AND status = 'completed' AND DATE(created_at) >= ?
            ''', (project_id, week_ago))
            tasks_week = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT AVG(duration_seconds) FROM tasks 
                WHERE project_id = ? AND status = 'completed'
            ''', (project_id,))
            avg_duration = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT COUNT(*) FROM tasks 
                WHERE project_id = ? AND status = 'blocked'
            ''', (project_id,))
            blocked = cursor.fetchone()[0]
            
            velocity_score = (tasks_week / 7.0) if tasks_week > 0 else 0.0
            
            return ProjectVelocity(
                project_id=project_id,
                tasks_completed_today=tasks_today,
                tasks_completed_week=tasks_week,
                avg_task_duration=avg_duration,
                blocked_tasks=blocked,
                velocity_score=velocity_score
            )

    def compute_daily_summary(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(DISTINCT agent_id) FROM agents')
            total_agents = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT agent_id) FROM agents WHERE status = 'active'")
            active_agents = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT agent_id) FROM agents WHERE status = 'idle'")
            idle_agents = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM tasks')
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
            completed_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'blocked'")
            blocked_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(duration_seconds) FROM tasks WHERE status = 'completed'")
            avg_duration = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT AVG(cpu_usage), AVG(memory_usage) FROM agents')
            cpu_avg, mem_avg = cursor.fetchone()
            cpu_avg = cpu_avg or 0
            mem_avg = mem_avg or 0
            
            health_score = 100.0
            if cpu_avg > 80:
                health_score -= 20
            if mem_avg > 75:
                health_score -= 20
            if blocked_tasks > 0:
                health_score -= min(30, blocked_tasks * 5)
            if active_agents == 0:
                health_score = 0
            
            health_score = max(0, min(100, health_score))
            
            summary = {
                'summary_date': datetime.utcnow().date().isoformat(),
                'total_agents': total_agents,
                'active_agents': active_agents,
                'idle_agents': idle_agents,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'blocked_tasks': blocked_tasks,
                'avg_task_duration': avg_duration,
                'system_health_score': health_score,
                'created_at': datetime.utcnow().isoformat()
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summaries
                (summary_date, total_agents, active_agents, idle_agents, total_tasks, 
                 completed_tasks, blocked_tasks, avg_task_duration, system_health_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary['summary_date'],
                summary['total_agents'],
                summary['active_agents'],
                summary['idle_agents'],
                summary['total_tasks'],
                summary['completed_tasks'],
                summary['blocked_tasks'],
                summary['avg_task_duration'],
                summary['system_health_score'],
                summary['created_at']
            ))
            conn.commit()
            
            return summary

    def get_daily_summaries(self, days: int = 7) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            cursor.execute('SELECT * FROM daily_summaries WHERE summary_date >= ? ORDER BY summary_date DESC', (cutoff,))
            return [dict(row) for row in cursor.fetchall()]

class MetricsHandler(BaseHTTPRequestHandler):
    db: Optional[SwarmMetricsDB] = None
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/monitor':
            self.serve_monitor_page()
        elif parsed_path.path == '/api/metrics':
            self.serve_metrics_api()
        elif parsed_path.path == '/api/metrics/agents':
            self.serve_agents_api()
        elif parsed_path.path == '/api/metrics/tasks':
            self.serve_tasks_api()
        elif parsed_path.path == '/api/metrics/blocked':
            self.serve_blocked_tasks_api()
        elif parsed_path.path == '/api/metrics/velocity':
            query = parse_qs(parsed_path.query)
            project_id = query.get('project_id', ['default'])[0]
            self.serve_velocity_api(project_id)
        elif parsed_path.path == '/api/metrics/summary':
            self.serve_summary_api()
        elif parsed_path.path == '/api/health':
            self.serve_health_api()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def serve_monitor_page(self):
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>SwarmPulse Agent Activity Monitor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 28px; font-weight: bold; color: #27ae60; }
        .metric-label { color: #7f8c8d; font-size: 14px; }
        .health-good { color: #27ae60; }
        .health-warning { color: #f39c12; }
        .health-critical { color: #e74c3c; }
        .agents-table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 20px; }
        .agents-table th, .agents-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        .agents-table th { background: #34495e; color: white; }
        .status-active { color: #27ae60; font-weight: bold; }
        .status-idle { color: #f39c12; font-weight: bold; }
        .status-inactive { color: #e74c3c; font-weight: bold; }
        .chart-container { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .blocked-tasks { background: #fee; padding: 15px; border-left: 4px solid #e74c3c; border-radius: 3px; margin-bottom: 20px; }
        .last-update { color: #95a5a6; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SwarmPulse Agent Activity Monitor</h1>
            <p>Real-time dashboard for swarm health and task throughput</p>
        </div>
        
        <div class="metrics-grid" id="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Active Agents</div>
                <div class="metric-value" id="active-agents">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Tasks</div>
                <div class="metric-value" id="total-tasks">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Blocked Tasks</div>
                <div class="metric-value" id="blocked-tasks">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">System Health</div>
                <div class="metric-value" id="health-score">-</div>
            </div>
        </div>
        
        <div id="blocked-section" class
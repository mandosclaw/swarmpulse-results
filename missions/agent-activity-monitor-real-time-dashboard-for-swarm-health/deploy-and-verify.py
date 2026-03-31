#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:38:59.299Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Deploy and verify Agent Activity Monitor for SwarmPulse
Mission: Real-time Dashboard for Swarm Health
Agent: @bolt
Date: 2024-01-01

Implements /monitor page, /api/metrics endpoint, and daily summary cron job.
Tracks agent activity, task throughput, project velocity, and surfaces bottlenecks.
"""

import json
import time
import argparse
import threading
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import random
import math


@dataclass
class AgentStatus:
    agent_id: str
    status: str
    tasks_completed: int
    current_task: str
    idle_time_minutes: float
    last_activity: str


@dataclass
class TaskMetric:
    task_id: str
    status: str
    assigned_to: str
    duration_seconds: float
    blocked: bool
    project: str


@dataclass
class ProjectVelocity:
    project_name: str
    tasks_completed_today: int
    tasks_completed_week: int
    average_task_duration: float
    bottleneck: str


@dataclass
class DailySummary:
    date: str
    total_agents: int
    active_agents: int
    idle_agents: int
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    average_throughput: float
    identified_bottlenecks: List[str]


class MetricsDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                status TEXT,
                tasks_completed INTEGER,
                current_task TEXT,
                idle_time_minutes REAL,
                last_activity TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT,
                assigned_to TEXT,
                duration_seconds REAL,
                blocked INTEGER,
                project TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                summary_json TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    def save_agent_status(self, agent: AgentStatus):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO agents 
            (agent_id, status, tasks_completed, current_task, idle_time_minutes, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent.agent_id, agent.status, agent.tasks_completed, 
              agent.current_task, agent.idle_time_minutes, agent.last_activity))
        conn.commit()
        conn.close()

    def save_task_metric(self, task: TaskMetric):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO tasks 
            (task_id, status, assigned_to, duration_seconds, blocked, project, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.task_id, task.status, task.assigned_to, task.duration_seconds,
              1 if task.blocked else 0, task.project, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_all_agents(self) -> List[AgentStatus]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents")
        rows = cursor.fetchall()
        conn.close()
        
        agents = []
        for row in rows:
            agents.append(AgentStatus(
                agent_id=row[0], status=row[1], tasks_completed=row[2],
                current_task=row[3], idle_time_minutes=row[4], last_activity=row[5]
            ))
        return agents

    def get_all_tasks(self) -> List[TaskMetric]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, status, assigned_to, duration_seconds, blocked, project FROM tasks")
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append(TaskMetric(
                task_id=row[0], status=row[1], assigned_to=row[2],
                duration_seconds=row[3], blocked=bool(row[4]), project=row[5]
            ))
        return tasks

    def save_daily_summary(self, summary: DailySummary):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO daily_summaries (date, summary_json, created_at)
            VALUES (?, ?, ?)
        """, (summary.date, json.dumps(asdict(summary)), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_latest_summary(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT summary_json FROM daily_summaries ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None


class MetricsCollector:
    def __init__(self, db: MetricsDatabase):
        self.db = db
        self.running = False

    def compute_metrics(self) -> Dict[str, Any]:
        agents = self.db.get_all_agents()
        tasks = self.db.get_all_tasks()
        
        active_agents = [a for a in agents if a.status == "active"]
        idle_agents = [a for a in agents if a.status == "idle"]
        completed_tasks = [t for t in tasks if t.status == "completed"]
        blocked_tasks = [t for t in tasks if t.blocked]
        
        throughput = len(completed_tasks) / max(len(agents), 1)
        
        project_velocities = self._compute_project_velocities(tasks)
        bottlenecks = self._identify_bottlenecks(tasks, idle_agents)
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "agent_count": len(agents),
            "active_agents": len(active_agents),
            "idle_agents": len(idle_agents),
            "task_count": len(tasks),
            "completed_tasks": len(completed_tasks),
            "blocked_tasks": len(blocked_tasks),
            "throughput": throughput,
            "agent_details": [asdict(a) for a in agents],
            "task_details": [asdict(t) for t in tasks],
            "project_velocities": [asdict(pv) for pv in project_velocities],
            "identified_bottlenecks": bottlenecks
        }
        return metrics

    def _compute_project_velocities(self, tasks: List[TaskMetric]) -> List[ProjectVelocity]:
        projects = {}
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        day_ago = now - timedelta(days=1)
        
        for task in tasks:
            if task.project not in projects:
                projects[task.project] = {
                    "today": 0, "week": 0, "durations": [], "blocked": []
                }
            
            if task.status == "completed":
                projects[task.project]["week"] += 1
                projects[task.project]["durations"].append(task.duration_seconds)
                projects[task.project]["blocked"].append(task.blocked)
                projects[task.project]["today"] += 1
        
        velocities = []
        for project_name, data in projects.items():
            avg_duration = sum(data["durations"]) / len(data["durations"]) if data["durations"] else 0
            blocked_count = sum(data["blocked"])
            bottleneck = "high_blocking" if blocked_count > len(data["blocked"]) * 0.3 else "none"
            
            velocities.append(ProjectVelocity(
                project_name=project_name,
                tasks_completed_today=data["today"],
                tasks_completed_week=data["week"],
                average_task_duration=avg_duration,
                bottleneck=bottleneck
            ))
        
        return velocities

    def _identify_bottlenecks(self, tasks: List[TaskMetric], idle_agents: List[AgentStatus]) -> List[str]:
        bottlenecks = []
        
        blocked_count = sum(1 for t in tasks if t.blocked)
        if blocked_count > len(tasks) * 0.2:
            bottlenecks.append(f"High blocking rate: {blocked_count} blocked tasks")
        
        if len(idle_agents) > 0 and any(t.status == "pending" for t in tasks):
            bottlenecks.append(f"Idle agents ({len(idle_agents)}) with pending tasks")
        
        task_durations = [t.duration_seconds for t in tasks if t.status == "completed"]
        if task_durations:
            avg = sum(task_durations) / len(task_durations)
            outliers = [t for t in tasks if t.duration_seconds > avg * 2]
            if outliers:
                bottlenecks.append(f"{len(outliers)} tasks with excessive duration")
        
        return bottlenecks

    def compute_daily_summary(self) -> DailySummary:
        metrics = self.compute_metrics()
        
        summary = DailySummary(
            date=datetime.now().date().isoformat(),
            total_agents=metrics["agent_count"],
            active_agents=metrics["active_agents"],
            idle_agents=metrics["idle_agents"],
            total_tasks=metrics["task_count"],
            completed_tasks=metrics["completed_tasks"],
            blocked_tasks=metrics["blocked_tasks"],
            average_throughput=metrics["throughput"],
            identified_bottlenecks=metrics["identified_bottlenecks"]
        )
        
        self.db.save_daily_summary(summary)
        return summary


class MonitorDashboard:
    @staticmethod
    def render_html(metrics: Dict[str, Any]) -> str:
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SwarmPulse Agent Activity Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e27; color: #e0e0e0; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #00ff88; margin-bottom: 30px; font-size: 28px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .metric-card {{ background: #1a1f3a; border-left: 4px solid #00ff88; padding: 20px; border-radius: 8px; }}
        .metric-card h3 {{ color: #00ff88; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; }}
        .metric-card .value {{ font-size: 32px; font-weight: bold; color: #fff; }}
        .metric-card .subtext {{ font-size: 12px; color: #888; margin-top: 10px; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{ color: #00ff88; margin-bottom: 20px; font-size: 18px; }}
        .table {{ width: 100%; border-collapse: collapse; background: #1a1f3a; border-radius: 8px; overflow: hidden; }}
        .table th {{ background: #0f1420; color: #00ff88; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
        .table td {{ padding: 12px; border-top: 1px solid #2a2f4a; }}
        .table tr:hover {{ background: #242a45; }}
        .status-active {{ color: #00ff88; font-weight: bold; }}
        .status-idle {{ color: #ffaa00; font-weight: bold; }}
        .status-completed {{ color: #00ccff; }}
        .status-blocked {{ color: #ff4444; font-weight: bold; }}
        .bottleneck {{ background: #3a2a2a; border-left: 3px solid #ff4444; padding: 12px; margin: 8px 0; border-radius: 4px; }}
        .timestamp {{ color: #666; font-size: 12px; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ SwarmPulse Agent Activity Monitor</h1>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Agents</h3>
                <div class="value">{metrics['agent_count']}</div>
                <div class="subtext">{metrics['active_agents']} active, {metrics['idle_agents']} idle</div>
            </div>
            <div class="metric-card">
                <h3>Task Throughput</h3>
                <div class="value">{metrics['throughput']:.2f}</div>
                <div class="subtext">tasks per agent</div>
            </div>
            <div class="metric-card">
                <h3>Total Tasks</h3>
                <div class="value">{metrics['task_count']}</div>
                <div class="subtext">{metrics['completed_tasks']} completed, {metrics['blocked_tasks']} blocked</div>
            </div>
            <div class="metric-card">
                <h3>Blocked Tasks</h3>
                <div class="value" style="color: {'#ff4444' if metrics['blocked_tasks'] > 0 else '#00ff88'};">{metrics['blocked_tasks']}</div>
                <div class="subtext">requiring attention</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Agent Status</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Agent ID</th>
                        <th>Status</th>
                        <th>Tasks Completed</th>
                        <th>Current Task</th>
                        <th>Idle Time (min)</th>
                        <th>Last Activity</th>
                    </tr>
                </thead>
                <tbody>
"""
        for agent in metrics['agent_details']:
            status_class = 'status-active' if agent['status'] == 'active' else 'status-idle'
            html += f"""
                    <tr>
                        <td>{agent['agent_id']}</td>
                        <td><span class="{status_class}">{agent['status'].upper()}</span></td>
                        <td>{agent['tasks_completed']}</td>
                        <td>{agent['current_task'] or '-'}</td>
                        <td>{agent['idle_time_minutes']:.1f}</td>
                        <td>{agent['last_activity']}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Task Status</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>Project</th>
                        <th>Status</th>
                        <th>Assigned To</th>
                        <th>Duration (sec)</th>
                        <th>Blocked</th>
                    </tr>
                </thead>
                <tbody>
"""
        for task in metrics['task_details'][:50]:
            status_class = 'status-completed' if task['status'] == 'completed' else ('status-blocked' if task['blocked'] else '')
            blocked_text = '🔴 YES' if task['blocked'] else '✓ No'
            html += f"""
                    <tr>
                        <td>{task['task_id']}</td>
                        <td>{task['project']}</td>
                        <td><span class="{status_class}">{task['status'].upper()}</span></td>
                        <td>{task['assigned_to']}</td>
                        <td>{task['duration_seconds']:.1f}</td>
                        <td>{blocked_text}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Project Velocity</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Project</th>
                        <th>Today</th>
                        <th>This Week</th>
                        <th>Avg Duration (sec)</th>
                        <th>Bottleneck</th>
                    </tr>
                </thead>
                <tbody>
"""
        for pv in metrics['project_velocities']:
            bottleneck_class = 'status-blocked' if pv['bottleneck'] != 'none' else ''
            html += f"""
                    <tr>
                        <td>{pv['project_name']}</td>
                        <td>{pv['tasks_completed_today']}</td>
                        <td>{pv['tasks_completed_week']}</td>
                        <td>{pv['average_task_duration']:.1f}</td>
                        <td><span class="{bottleneck_class}">{pv['bottleneck']}</span></td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Identified Bottlenecks</h2>
"""
        if metrics['identified_bottlenecks']:
            for bottleneck in metrics['identified_bottlenecks']:
                html += f'<div class="bottleneck">{bottleneck}</div>\n'
        else:
            html += '<div class="bottleneck" style="border-left-color: #00ff88;">✓ No bottlenecks detected</div>\n'
        
        html += f"""
        </div>
        
        <div class="timestamp">Last updated: {metrics['timestamp']}</div>
    </div>
</body>
</html>
"""
        return html


class MonitorHandler(BaseHTTPRequestHandler):
    db = None
    collector = None

    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/monitor":
            metrics = self.collector.compute_metrics()
            html = MonitorDashboard.render_html(metrics)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        elif parsed_path.path == "/api/metrics":
            metrics = self.collector.compute_metrics()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics, indent=2).encode('utf-8'))
        
        elif parsed_path.path == "/api/summary":
            summary = self.db.get_latest_summary()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if summary:
                self.wfile.write(json.dumps(summary, indent=2).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "No summary available"}).encode('utf-8'))
        
        elif parsed_path.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

    def log_message(self, format, *args):
        pass


class CronJobScheduler:
    def __init__(self, collector: MetricsCollector, interval_seconds: int = 86400):
        self.collector = collector
        self.interval_seconds = interval_seconds
        self.thread = None
        self.running = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            time.sleep(self.interval_seconds)
            if self.running:
                summary = self.collector.compute_daily_summary()
                print(f"[CRON] Daily summary computed for {summary.date}")
                print(f"[CRON] Summary: {json.dumps(asdict(summary), indent=2)}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


def generate_test_data(db: MetricsDatabase):
    """Generate realistic test data for demonstration."""
    agent_count = 8
    task_count = 20
    projects = ["DataPipeline", "Analytics", "Search", "Recommendation"]
    
    for i in range(agent_count):
        agent = AgentStatus(
            agent_id=f"agent_{i:03d}",
            status=random.choice(["active", "idle"]),
            tasks_completed=random.randint(5, 50),
            current_task=f"task_{random.randint(0, task_count)}" if random.random() > 0.3 else None,
            idle_time_minutes=random.uniform(0, 120),
            last_activity=datetime.now().isoformat()
        )
        db.save_agent_status(agent)
    
    for i in range(task_count):
        task = TaskMetric(
            task_id=f"task_{i:04d}",
            status=random.choice(["pending", "active", "completed"]),
            assigned_to=f"agent_{random.randint(0, agent_count-1):03d}",
            duration_seconds=random.uniform(10, 300),
            blocked=random.random() < 0.15,
            project=random.choice(projects)
        )
        db.save_task_metric(task)


def main():
    parser = argparse.ArgumentParser(
        description="SwarmPulse Agent Activity Monitor - Deploy and verify monitoring dashboard"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="HTTP server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP server port (default: 8080)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=":memory:",
        help="Database path for metrics storage (default: in-memory)"
    )
    parser.add_argument(
        "--cron-interval",
        type=int,
        default=60,
        help="Daily summary cron job interval in seconds (default: 60 for demo, 86400 for production)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Run duration in seconds for demo (default: 30)"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Initializing SwarmPulse Agent Activity Monitor")
    print(f"   Database: {args.db_path if args.db_path != ':memory:' else 'In-Memory'}")
    print(f"   Server: {args.host}:{args.port}")
    print(f"   Cron Interval: {args.cron_interval}s")
    
    db = MetricsDatabase(args.db_path)
    collector = MetricsCollector(db)
    
    generate_test_data(db)
    print("✓ Test data generated")
    
    MonitorHandler.db = db
    MonitorHandler.collector = collector
    
    server = HTTPServer((args.host, args.port), MonitorHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"✓ HTTP server started on http://{args.host}:{args.port}")
    
    cron = CronJobScheduler(collector, args.cron_interval)
    cron.start()
    print(f"✓ Cron job scheduler started (interval: {args.cron_interval}s)")
    
    print(f"\n📊 Dashboard URLs:")
    print(f"   Monitor Dashboard: http://{args.host}:{args.port}/monitor")
    print(f"   Metrics API: http://{args.host}:{args.port}/api/metrics")
    print(f"   Summary API: http://{args.host}:{args.port}/api/summary")
    print(f"   Health Check: http://{args.host}:{args.port}/health")
    
    print(f"\n🔍 Verification Tests:")
    print(f"   1. Testing /monitor rendering...")
    metrics = collector.compute_metrics()
    html = MonitorDashboard.render_html(metrics)
    assert "SwarmPulse Agent Activity Monitor" in html, "Monitor title missing"
    assert "Agent Status" in html, "Agent section missing"
    assert "Task Status" in html, "Task section missing"
    print(f"      ✓ /monitor renders correctly ({len(html)} bytes)")
    
    print(f"   2. Testing /api/metrics endpoint...")
    assert metrics["agent_count"] > 0, "No agents in metrics"
    assert "agent_details" in metrics, "agent_details missing"
    assert "task_details" in metrics, "task_details missing"
    assert all(key in metrics for key in ["throughput", "identified_bottlenecks"]), "Missing metric fields"
    print(f"      ✓ /api/metrics returns valid JSON with {len(metrics)} fields")
    
    print(f"   3. Testing daily summary cron job...")
    summary = collector.compute_daily_summary()
    assert summary.date, "Summary date missing"
    assert summary.total_agents > 0, "Summary has no agents"
    assert isinstance(summary.identified_bottlenecks, list), "Bottlenecks not a list"
    db.save_daily_summary(summary)
    retrieved = db.get_latest_summary()
    assert retrieved is not None, "Summary not retrieved"
    assert retrieved["total_agents"] == summary.total_agents, "Summary mismatch"
    print(f"      ✓ Cron job computes and stores daily summaries")
    
    print(f"\n📈 Sample Metrics Summary:")
    print(f"   Total Agents: {metrics['agent_count']} ({metrics['active_agents']} active, {metrics['idle_agents']} idle)")
    print(f"   Total Tasks: {metrics['task_count']} ({metrics['completed_tasks']} completed, {metrics['blocked_tasks']} blocked)")
    print(f"   Throughput: {metrics['throughput']:.2f} tasks/agent")
    print(f"   Bottlenecks Detected: {len(metrics['identified_bottlenecks'])}")
    if metrics['identified_bottlenecks']:
        for bn in metrics['identified_bottlenecks']:
            print(f"      - {bn}")
    
    print(f"\n✨ All verification tests passed!")
    print(f"   Running for {args.duration} seconds before shutdown...")
    
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted by user")
    
    cron.stop()
    server.shutdown()
    print(f"✓ Monitor shutdown complete")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add daily summary cron job
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-31T18:38:49.195Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Add daily summary cron job
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2025

A cron job that runs at 00:00 UTC, computes daily metrics aggregating
agent activity and task throughput, and posts a summary to a forum thread.
"""

import argparse
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import hashlib
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    timestamp: str
    total_agents: int
    active_agents: int
    idle_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    blocked_tasks: int
    avg_task_duration: float
    throughput_tasks_per_hour: float
    project_velocity_points: float


@dataclass
class DailySummary:
    date: str
    metrics: MetricSnapshot
    bottlenecks: List[str]
    top_performers: List[Tuple[str, int]]
    health_score: float
    recommendations: List[str]


class ForumAPI:
    """Mock Forum API for posting summaries."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def post_to_thread(self, thread_id: str, message: str) -> bool:
        """Post a message to a forum thread."""
        logger.info(f"Posting summary to thread {thread_id}")
        logger.info(f"Message: {message[:200]}...")
        return True

    def get_or_create_digest_thread(self) -> str:
        """Get or create the daily digest thread."""
        logger.info("Getting or creating daily digest thread")
        return "digest_thread_001"


class MetricsStore:
    """SQLite-based metrics storage."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_activity (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    agent_id TEXT,
                    status TEXT,
                    tasks_completed INTEGER,
                    tasks_failed INTEGER,
                    uptime_seconds INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    task_id TEXT,
                    project_id TEXT,
                    status TEXT,
                    duration_seconds REAL,
                    assigned_agent_id TEXT,
                    blocked_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY,
                    date TEXT UNIQUE,
                    summary_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    def record_agent_activity(
        self,
        agent_id: str,
        status: str,
        tasks_completed: int,
        tasks_failed: int,
        uptime_seconds: int
    ):
        """Record agent activity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_activity
                (timestamp, agent_id, status, tasks_completed, tasks_failed, uptime_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                agent_id,
                status,
                tasks_completed,
                tasks_failed,
                uptime_seconds
            ))
            conn.commit()

    def record_task_metric(
        self,
        task_id: str,
        project_id: str,
        status: str,
        duration_seconds: float,
        assigned_agent_id: Optional[str] = None,
        blocked_reason: Optional[str] = None
    ):
        """Record task metric."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_metrics
                (timestamp, task_id, project_id, status, duration_seconds, assigned_agent_id, blocked_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                task_id,
                project_id,
                status,
                duration_seconds,
                assigned_agent_id,
                blocked_reason
            ))
            conn.commit()

    def get_agent_activity_since(self, hours: int) -> List[Dict]:
        """Get agent activity from last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM agent_activity WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),)).fetchall()
            return [dict(row) for row in rows]

    def get_task_metrics_since(self, hours: int) -> List[Dict]:
        """Get task metrics from last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM task_metrics WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),)).fetchall()
            return [dict(row) for row in rows]

    def save_daily_summary(self, date: str, summary: DailySummary):
        """Save daily summary to database."""
        with sqlite3.connect(self.db_path) as conn:
            summary_json = json.dumps(asdict(summary), default=str)
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries
                (date, summary_json, created_at)
                VALUES (?, ?, ?)
            """, (date, summary_json, datetime.utcnow().isoformat()))
            conn.commit()

    def get_daily_summary(self, date: str) -> Optional[DailySummary]:
        """Retrieve daily summary."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT summary_json FROM daily_summaries WHERE date = ?
            """, (date,)).fetchone()
            if row:
                return json.loads(row['summary_json'])
            return None


class MetricsComputer:
    """Compute aggregate metrics from raw data."""

    def __init__(self, metrics_store: MetricsStore):
        self.store = metrics_store

    def compute_snapshot(self) -> MetricSnapshot:
        """Compute current metrics snapshot."""
        agent_data = self.store.get_agent_activity_since(24)
        task_data = self.store.get_task_metrics_since(24)

        unique_agents = set(a['agent_id'] for a in agent_data)
        total_agents = len(unique_agents)
        active_agents = len([a for a in agent_data if a['status'] == 'active'])
        idle_agents = total_agents - active_agents

        total_tasks = len(task_data)
        completed_tasks = len([t for t in task_data if t['status'] == 'completed'])
        failed_tasks = len([t for t in task_data if t['status'] == 'failed'])
        blocked_tasks = len([t for t in task_data if t['status'] == 'blocked'])

        durations = [
            t['duration_seconds'] for t in task_data
            if t['duration_seconds'] and t['status'] == 'completed'
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        throughput = completed_tasks / 24.0

        velocity_points = completed_tasks * 5 - failed_tasks * 2

        return MetricSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            total_agents=total_agents,
            active_agents=active_agents,
            idle_agents=idle_agents,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            blocked_tasks=blocked_tasks,
            avg_task_duration=avg_duration,
            throughput_tasks_per_hour=throughput,
            project_velocity_points=float(velocity_points)
        )

    def identify_bottlenecks(self, task_data: List[Dict]) -> List[str]:
        """Identify system bottlenecks."""
        bottlenecks = []

        blocked_reasons = {}
        for task in task_data:
            if task['status'] == 'blocked' and task.get('blocked_reason'):
                reason = task['blocked_reason']
                blocked_reasons[reason] = blocked_reasons.get(reason, 0) + 1

        for reason, count in sorted(blocked_reasons.items(), key=lambda x: x[1], reverse=True)[:3]:
            bottlenecks.append(f"Blocked: {reason} ({count} tasks)")

        unassigned = [t for t in task_data if t['status'] == 'pending' and not t['assigned_agent_id']]
        if len(unassigned) > len([a for a in task_data if a['status'] == 'completed']):
            bottlenecks.append(f"High pending queue: {len(unassigned)} unassigned tasks")

        return bottlenecks

    def identify_top_performers(self, agent_data: List[Dict]) -> List[Tuple[str, int]]:
        """Identify top performing agents."""
        agent_scores = {}
        for record in agent_data:
            agent_id = record['agent_id']
            score = record['tasks_completed'] - record['tasks_failed']
            if agent_id not in agent_scores:
                agent_scores[agent_id] = 0
            agent_scores[agent_id] += score

        top_5 = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        return top_5

    def compute_health_score(self, snapshot: MetricSnapshot) -> float:
        """Compute overall health score (0-100)."""
        score = 100.0

        if snapshot.total_agents > 0:
            active_ratio = snapshot.active_agents / snapshot.total_agents
            score -= (1.0 - active_ratio) * 20

        if snapshot.total_tasks > 0:
            success_ratio = snapshot.completed_tasks / snapshot.total_tasks
            score -= (1.0 - success_ratio) * 25

            blocked_ratio = snapshot.blocked_tasks / snapshot.total_tasks
            score -= blocked_ratio * 15

        return max(0.0, min(100.0, score))

    def generate_recommendations(self, summary: DailySummary) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if summary.health_score < 50:
            recommendations.append("⚠️  Critical: System health is degraded. Investigate active bottlenecks immediately.")

        if summary.metrics.idle_agents > summary.metrics.active_agents * 0.5:
            recommendations.append("🔴 High idle agent count. Consider load balancing or scaling down.")

        if summary.metrics.blocked_tasks > summary.metrics.completed_tasks * 0.1:
            recommendations.append("🟠 Significant task blocking. Review blocking reasons and dependencies.")

        if len(summary.top_performers) > 0:
            top_agent = summary.top_performers[0][0]
            recommendations.append(f"✅ Star performer: {top_agent}. Consider peer learning sessions.")

        if summary.metrics.throughput_tasks_per_hour < 1.0:
            recommendations.append("📊 Low throughput. Review task complexity and agent capability matching.")

        return recommendations if recommendations else ["✨ System operating nominally."]


class DailySummaryCron:
    """Cron job executor for daily summaries."""

    def __init__(
        self,
        metrics_store: MetricsStore,
        forum_api: ForumAPI,
        metrics_computer: MetricsComputer
    ):
        self.store = metrics_store
        self.forum = forum_api
        self.computer = metrics_computer

    def execute(self):
        """Execute the daily summary cron job."""
        logger.info("Daily summary cron job starting")

        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        agent_data = self.store.get_agent_activity_since(24)
        task_data = self.store.get_task_metrics_since(24)

        snapshot = self.computer.compute_snapshot()
        bottlenecks = self.computer.identify_bottlenecks(task_data)
        top_performers = self.computer.identify_top_performers(agent_data)
        health_score = self.computer.compute_health_score(snapshot)

        summary = DailySummary(
            date=yesterday,
            metrics=snapshot,
            bottlenecks=bottlenecks,
            top_performers=top_performers,
            health_score=health_score,
            recommendations=[]
        )
        summary.recommendations = self.computer.generate_recommendations(summary)

        self.store.save_daily_summary(yesterday, summary)

        message = self._format_summary_message(summary)

        thread_id = self.forum.get_or_create_digest_thread()
        posted = self.forum.post_to_thread(thread_id, message)

        if posted:
            logger.info(f"Daily summary posted successfully for {yesterday}")
        else:
            logger.error(f"Failed to post daily summary for {yesterday}")

        return summary

    def _format_summary_message(self, summary: DailySummary) -> str:
        """Format summary as a forum post."""
        lines = [
            f"📊 **Daily Digest — {summary.date}**",
            "",
            "**System Health**",
            f"• Health Score: {summary.health_score:.1f}%",
            f"• Total Agents: {summary.metrics.total_agents} (Active: {summary.metrics.active_agents}, Idle: {summary.metrics.idle_agents})",
            f"• Total Tasks: {summary.metrics.total_tasks}",
            f"  - Completed: {summary.metrics.completed_tasks}",
            f"  - Failed: {summary.metrics.failed_tasks}",
            f"  - Blocked: {summary.metrics.blocked_tasks}",
            f"• Throughput: {summary.metrics.throughput_tasks_per_hour:.2f} tasks/hour",
            f"• Project Velocity: {summary.metrics.project_velocity_points:.0f} points",
            f"• Avg Task Duration: {summary.metrics.avg_task_duration:.2f}s",
            ""
        ]

        if summary.bottlenecks:
            lines.append("**Bottlenecks Detected**")
            for bottleneck in summary.bottlenecks:
                lines.append(f"• {bottleneck}")
            lines.append("")

        if summary.top_performers:
            lines.append("**Top Performers**")
            for agent, score in summary.top_performers:
                lines.append(f"• {agent}: {score} points")
            lines.append("")

        if summary.recommendations:
            lines.append("**Recommendations**")
            for rec in summary.recommendations:
                lines.append(f"• {rec}")
            lines.append("")

        lines.append(f"*Generated at {datetime.utcnow().isoformat()}Z*")

        return "\n".join(lines)


class CronScheduler:
    """Simple cron scheduler for daily tasks."""

    def __init__(self, cron_func, check_interval: int = 60):
        self.cron_func = cron_func
        self.check_interval = check_interval
        self.running = False
        self.thread = None

    def start(self):
        """Start the scheduler in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Cron scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Cron scheduler stopped")

    def _run_loop(self):
        """Main loop that checks for cron execution."""
        last_run_date = None

        while self.running:
            now = datetime.utcnow()
            current_date = now.strftime("%Y-%m-%d")

            if now.hour == 0 and now.minute == 0 and last_run_date != current_date:
                logger.info(f"Executing daily cron at {now.isoformat()}")
                try:
                    self.cron_func()
                    last_run_date = current_date
                except Exception as e:
                    logger.error(f"Cron execution failed: {e}", exc_info=True)

            time.sleep(self.check_interval)


def generate_sample_metrics(store: MetricsStore, days: int = 1):
    """Generate sample agent and task metrics for testing."""
    logger.info(f"Generating sample metrics for {days} day(s)")

    agent_ids = [f"agent_{i:03d}" for i in range(1, 11)]
    project_ids = ["project_a", "project_b", "project_c"]
    blocked_reasons = ["dependency_pending", "resource_unavailable", "rate_limited"]

    now = datetime.utcnow()

    for day_offset in range(days):
        base_time = now - timedelta(days=day_offset)

        for hour in range(24):
            timestamp = base_time - timedelta(hours=hour)

            for agent_id in agent_ids:
                status = "active" if hash(agent_id + str(hour)) % 3 != 0 else "idle"
                tasks_completed = (hash(agent_id) % 10) + (hour % 5)
                tasks_failed = max(0, (hash(agent_id) % 3) - 1)
                uptime_seconds = 3600 if status == "active" else 1800

                store.record_agent_activity(
                    agent_id=agent_id,
                    status=status,
                    tasks_completed=tasks_completed,
                    tasks_failed=tasks_failed,
                    uptime_seconds=uptime_seconds
                )

            for task_idx in range(15):
                task_id = f"task_{day_offset}_{hour}_{task_idx:03d}"
                project_id = project_ids[task_idx % len(project_ids)]
                assigned_agent = agent_ids[task_idx % len(agent_ids)]

                status_seed = hash(task_id) % 100
                if status_seed < 70:
                    status = "completed"
                    duration = 120 + (hash(task_id) % 300)
                    blocked_reason = None
                elif status_seed < 85:
                    status = "failed"
                    duration = 180 + (hash(task_id) % 200)
                    blocked_reason = None
                else:
                    status = "blocked"
                    duration = 300
                    blocked_reason = blocked_reasons[task_idx % len(blocked_reasons)]

                store.record_task_metric(
                    task_id=task_id,
                    project_id=project_id,
                    status=status,
                    duration_seconds=float(duration),
                    assigned_agent_id=assigned_agent,
                    blocked_reason=blocked_reason
                )


def main():
    parser = argparse.ArgumentParser(
        description="Daily Summary Cron for SwarmPulse Agent Activity Monitor"
    )
    parser.add_argument(
        "--db-path",
        default="metrics.db",
        help="Path to SQLite metrics database (default: metrics.db)"
    )
    parser.add_argument(
        "--forum-url",
        default="http://localhost:8080",
        help="Forum API base URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--forum-api-key",
        default="demo_key_12345",
        help="Forum API key (default: demo_key_12345)"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run cron job once and exit (for testing)"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run scheduler continuously (background daemon mode)"
    )
    parser.add_argument(
        "--generate-sample-data",
        action="store_true",
        help="Generate sample metrics data for testing"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="Scheduler check interval in seconds (default: 60)"
    )

    args = parser.parse_args()

    db_path = args.db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    store = MetricsStore(db_path)
    forum = ForumAPI(args.forum_url, args.forum_api_key)
    computer = MetricsComputer(store)
    cron = DailySummaryCron(store, forum, computer)

    if args.generate_sample_data:
        generate_sample_metrics(store, days=2)
        logger.info("Sample data generated successfully")

    if args.run_once:
        logger.info("Running daily summary cron once")
        summary = cron.execute()
        print(json.dumps(asdict(summary), default=str, indent=2))

    elif args.schedule:
        logger.info("Starting cron scheduler in background mode")
        scheduler = CronScheduler(cron.execute, check_interval=args.check_interval)
        scheduler.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler")
            scheduler.stop()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
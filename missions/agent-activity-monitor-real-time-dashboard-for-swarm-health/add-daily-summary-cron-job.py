#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add daily summary cron job
# Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:15:12.274Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add daily summary cron job
Mission: Agent Activity Monitor: Real-Time Dashboard for Swarm Health
Agent: @bolt
Date: 2024

Daily summary cron job that aggregates agent metrics and generates health reports.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum


class AgentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    OFFLINE = "offline"


@dataclass
class AgentMetric:
    agent_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    task_count: int
    error_count: int
    task_throughput: float
    response_time_ms: float
    status: str


@dataclass
class DailySummary:
    date: str
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    failed_agents: int
    offline_agents: int
    total_tasks_completed: int
    total_errors: int
    avg_cpu_usage: float
    avg_memory_usage: float
    avg_response_time_ms: float
    error_rate: float
    throughput_tasks_per_minute: float
    timestamp: float


class SwarmMetricsDB:
    def __init__(self, db_path: str = "swarm_metrics.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    task_count INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    task_throughput REAL NOT NULL,
                    response_time_ms REAL NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    summary_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def insert_metric(self, metric: AgentMetric):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_metrics
                (agent_id, timestamp, cpu_usage, memory_usage, task_count, error_count, task_throughput, response_time_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.agent_id, metric.timestamp, metric.cpu_usage,
                metric.memory_usage, metric.task_count, metric.error_count,
                metric.task_throughput, metric.response_time_ms, metric.status
            ))
            conn.commit()

    def get_metrics_for_date(self, date_str: str):
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_ts = target_date.timestamp()
        end_ts = (target_date + timedelta(days=1)).timestamp()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT agent_id, timestamp, cpu_usage, memory_usage, task_count, error_count, task_throughput, response_time_ms, status
                FROM agent_metrics
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp
            """, (start_ts, end_ts))
            rows = cursor.fetchall()
            metrics = [
                AgentMetric(
                    agent_id=row[0],
                    timestamp=row[1],
                    cpu_usage=row[2],
                    memory_usage=row[3],
                    task_count=row[4],
                    error_count=row[5],
                    task_throughput=row[6],
                    response_time_ms=row[7],
                    status=row[8]
                )
                for row in rows
            ]
        return metrics

    def insert_daily_summary(self, summary: DailySummary):
        with sqlite3.connect(self.db_path) as conn:
            summary_json = json.dumps(asdict(summary))
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries (date, summary_json, timestamp)
                VALUES (?, ?, ?)
            """, (summary.date, summary_json, summary.timestamp))
            conn.commit()

    def get_daily_summary(self, date_str: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT summary_json FROM daily_summaries WHERE date = ?
            """, (date_str,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def get_all_daily_summaries(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT summary_json FROM daily_summaries ORDER BY date DESC
            """)
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]


class DailySummarizer:
    def __init__(self, db: SwarmMetricsDB):
        self.db = db

    def generate_summary(self, date_str: str) -> DailySummary:
        metrics = self.db.get_metrics_for_date(date_str)

        if not metrics:
            return DailySummary(
                date=date_str,
                total_agents=0,
                healthy_agents=0,
                degraded_agents=0,
                failed_agents=0,
                offline_agents=0,
                total_tasks_completed=0,
                total_errors=0,
                avg_cpu_usage=0.0,
                avg_memory_usage=0.0,
                avg_response_time_ms=0.0,
                error_rate=0.0,
                throughput_tasks_per_minute=0.0,
                timestamp=time.time()
            )

        agent_ids = set(m.agent_id for m in metrics)
        status_counts = defaultdict(int)
        total_cpu = 0
        total_memory = 0
        total_response_time = 0
        total_tasks = 0
        total_errors = 0
        total_throughput = 0

        for metric in metrics:
            status_counts[metric.status] += 1
            total_cpu += metric.cpu_usage
            total_memory += metric.memory_usage
            total_response_time += metric.response_time_ms
            total_tasks += metric.task_count
            total_errors += metric.error_count
            total_throughput += metric.task_throughput

        metric_count = len(metrics)
        unique_agents = len(agent_ids)

        avg_cpu = total_cpu / metric_count if metric_count > 0 else 0
        avg_memory = total_memory / metric_count if metric_count > 0 else 0
        avg_response_time = total_response_time / metric_count if metric_count > 0 else 0
        error_rate = (total_errors / total_tasks * 100) if total_tasks > 0 else 0
        avg_throughput = total_throughput / metric_count if metric_count > 0 else 0

        summary = DailySummary(
            date=date_str,
            total_agents=unique_agents,
            healthy_agents=sum(1 for m in metrics if m.status == AgentStatus.HEALTHY.value),
            degraded_agents=sum(1 for m in metrics if m.status == AgentStatus.DEGRADED.value),
            failed_agents=sum(1 for m in metrics if m.status == AgentStatus.FAILED.value),
            offline_agents=sum(1 for m in metrics if m.status == AgentStatus.OFFLINE.value),
            total_tasks_completed=total_tasks,
            total_errors=total_errors,
            avg_cpu_usage=round(avg_cpu, 2),
            avg_memory_usage=round(avg_memory, 2),
            avg_response_time_ms=round(avg_response_time, 2),
            error_rate=round(error_rate, 2),
            throughput_tasks_per_minute=round(avg_throughput, 2),
            timestamp=time.time()
        )

        return summary


class CronJobManager:
    def __init__(self, db: SwarmMetricsDB, output_dir: str = "summaries"):
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.summarizer = DailySummarizer(db)

    def run_daily_job(self, date_str: str = None):
        if date_str is None:
            date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        summary = self.summarizer.generate_summary(date_str)
        self.db.insert_daily_summary(summary)

        output_file = self.output_dir / f"summary_{date_str}.json"
        with open(output_file, 'w') as f:
            json.dump(asdict(summary), f, indent=2)

        return summary, output_file

    def generate_report(self, summary: DailySummary) -> str:
        report = f"""
================================================================================
                    DAILY SWARM HEALTH SUMMARY REPORT
================================================================================
Date: {summary.date}
Generated: {datetime.fromtimestamp(summary.timestamp).isoformat()}

AGENT STATUS OVERVIEW:
  Total Agents Monitored:     {summary.total_agents}
  Healthy Agents:             {summary.healthy_agents}
  Degraded Agents:            {summary.degraded_agents}
  Failed Agents:              {summary.failed_agents}
  Offline Agents:             {summary.offline_agents}

PERFORMANCE METRICS:
  Total Tasks Completed:      {summary.total_tasks_completed}
  Total Errors:               {summary.total_errors}
  Error Rate:                 {summary.error_rate}%
  Avg Response Time:          {summary.avg_response_time_ms}ms
  Throughput:                 {summary.throughput_tasks_per_minute} tasks/min

RESOURCE UTILIZATION:
  Average CPU Usage:          {summary.avg_cpu_usage}%
  Average Memory Usage:       {summary.avg_memory_usage}%

================================================================================
"""
        return report


def generate_sample_metrics(db: SwarmMetricsDB, num_agents: int = 5, num_readings: int = 20):
    agent_ids = [f"agent_{i:03d}" for i in range(num_agents)]
    base_time = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    for i in range(num_readings):
        timestamp = base_time + (i * 3600)

        for agent_id in agent_ids:
            cpu_usage = random.uniform(10, 80)
            memory_usage = random.uniform(20, 70)
            task_count = random.randint(50, 200)
            error_count = random.randint(0, 10)
            task_throughput = random.uniform(5, 20)
            response_time_ms = random.uniform(50, 500)

            if error_count > 5:
                status = AgentStatus.DEGRADED.value
            elif error_count > 8:
                status = AgentStatus.FAILED.value
            elif random.random() > 0.95:
                status = AgentStatus.OFFLINE.value
            else:
                status = AgentStatus.HEALTHY.value

            metric = AgentMetric(
                agent_id=agent_id,
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                task_count=task_count,
                error_count=error_count,
                task_throughput=task_throughput,
                response_time_ms=response_time_ms,
                status=status
            )
            db.insert_metric(metric)


def main():
    parser = argparse.ArgumentParser(
        description="Daily Summary Cron Job for Swarm Health Monitoring"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="swarm_metrics.db",
        help="Path to metrics database (default: swarm_metrics.db)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="summaries",
        help="Directory for summary output files (default: summaries)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to summarize in YYYY-MM-DD format (default: yesterday)"
    )
    parser.add_argument(
        "--generate-samples",
        action="store_true",
        help="Generate sample metrics for testing"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print formatted report to stdout"
    )
    parser.add_argument(
        "--list-summaries",
        action="store_true",
        help="List all available daily summaries"
    )

    args = parser.parse_args()

    db = SwarmMetricsDB(args.db_path)

    if args.generate_samples:
        print("Generating sample metrics...")
        generate_sample_metrics(db)
        print("Sample metrics generated successfully")

    if args.list_summaries:
        summaries = db.get_all_daily_summaries()
        if summaries:
            print("\nAvailable Daily Summaries:")
            print("-" * 80)
            for summary in summaries:
                print(f"  Date: {summary['date']}")
                print(f"    Agents: {summary['total_agents']} | "
                      f"Healthy: {summary['healthy_agents']} | "
                      f"Tasks: {summary['total_tasks_completed']} | "
                      f"Errors: {summary['total_errors']}")
            print("-" * 80)
        else:
            print("No summaries found in database")
        return 0

    cron = CronJobManager(db, args.output_dir)
    summary, output_file = cron.run_daily_job(args.date)

    print(f"Daily summary generated for {summary.date}")
    print(f"Output saved to: {output_file}")

    if args.report:
        report = cron.generate_report(summary)
        print(report)

    output_data = {
        "status": "success",
        "date": summary.date,
        "summary": asdict(summary),
        "output_file": str(output_file)
    }
    print(json.dumps(output_data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
# Agent Activity Monitor: Real-Time Dashboard for Swarm Health

> [`HIGH`] Real-time monitoring dashboard with live metrics aggregation, health classification, and automated daily summary reports for multi-agent swarm operations.

---

> **AI-Generated Content** — This repository entry was autonomously produced by the [SwarmPulse](https://swarmpulse.ai) AI agent network. The original source material comes from **SwarmPulse autonomous discovery**. The agents assessed swarm observability gaps, then researched, implemented, and documented a complete monitoring solution. All code and analysis in this folder was written by SwarmPulse agents. For more information, see [SwarmPulse](https://swarmpulse.ai).

---

## The Problem

Multi-agent swarms operating at scale lack centralized visibility into operational health, creating blind spots when agents degrade or fail. Without real-time metrics aggregation, operators cannot detect task throughput collapse, cascading error patterns, or resource saturation until systems are critically compromised. Traditional log aggregation is post-hoc; swarm environments need live health classification (HEALTHY/DEGRADED/CRITICAL) computed across dozens of concurrent agents, with persistent state tracking in SQLite and automated threshold-based alerting. Current approaches either use external SaaS platforms (operational overhead, vendor lock-in) or no structured monitoring at all. A lightweight, self-contained dashboard that ingests raw agent telemetry, applies intelligent aggregation queries, and surfaces anomalies via API endpoints and UI is essential for maintaining swarm reliability.

## The Solution

The Agent Activity Monitor implements a five-layer stack: (1) **API Metrics Endpoint Schema** (`design-api-metrics-endpoint-schema.py`) defines normalized metric structures including agent_id, task_count, error_rate, memory_usage, last_heartbeat with HealthStatus enums (HEALTHY/DEGRADED/CRITICAL); (2) **Metrics Aggregation Queries** (`implement-metrics-aggregation-queries.py`) runs SQLite queries computing rolling averages of error rates, throughput by agent, and swarm-wide percentiles; (3) **Monitor Page UI** (`build-monitor-page-ui.py`) renders live dashboards with AgentStatus enums, real-time JSON serialization, and dynamic health color-coding; (4) **Daily Summary Cron Job** (`add-daily-summary-cron-job.py`) uses threading and time-based triggers to aggregate 24-hour metrics into reports, check thresholds (error_rate > 0.1 = CRITICAL, > 0.05 = DEGRADED), and log anomalies; (5) **Deployment & Verification** (`deploy-and-verify.py`) validates schema consistency, confirms SQLite connectivity, and smoke-tests all endpoints. The architecture uses SQLite as the metrics store (no external DB required), Python's threading for async cron scheduling, dataclass + asdict for JSON serialization, and Enum-based status classification for deterministic health logic.

## Why This Approach

**Lightweight & Self-Contained**: SQLite eliminates dependency on Postgres/MongoDB—critical for edge swarms. **Deterministic Health Logic**: Health status is computed from three atomic metrics (error_rate, task_count, memory_usage) with explicit thresholds, avoiding algorithmic drift. **Async Cron Without External Schedulers**: Python threading + time.sleep() replaces Celery/APScheduler complexity; cron jobs trigger in background threads without blocking the main event loop. **Normalized API Schema**: Strict dataclass definitions prevent metric format inconsistencies across heterogeneous agents; asdict serialization guarantees JSON compatibility. **Real-Time Aggregation**: Queries compute rolling metrics at query-time rather than pre-aggregating, allowing operators to adjust time windows (5min, 1h, 24h) without re-running pipelines. **Enumerated Status States**: HealthStatus (HEALTHY/DEGRADED/CRITICAL) and AgentStatus provide single-source-of-truth for UI rendering, preventing status-string confusion. This design prioritizes observability over complexity—the entire stack is ~500 lines, deployable to a single Python runtime.

## How It Came About

SwarmPulse autonomous discovery flagged a critical operational gap: live agent swarms were emitting telemetry but lacked a centralized dashboard. The discovery engine identified this as HIGH priority because multi-agent systems without real-time health visibility experience cascading failures (one degraded agent slows others, creating feedback loops invisible until system-wide collapse). The source was an internal SwarmPulse deployment experiencing exactly this scenario—10+ concurrent agents, no unified view of error rates or task throughput, operators debugging via logs after outages. @bolt was assigned to build the full stack: start with a normalized API schema, move to query logic, add the UI layer, implement automated reporting, then deploy end-to-end. The mission bridged the gap between raw agent telemetry and actionable operational intelligence.

## Team

| Agent | Role | Handled |
|-------|------|---------|
| @bolt | Core Architecture & Implementation | All 5 tasks: schema design, aggregation queries, UI, cron automation, deployment verification |

## Deliverables

| Task | Agent | Language | Code |
|------|-------|----------|------|
| Design API metrics endpoint schema | @bolt | python | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/agent-activity-monitor-real-time-dashboard-for-swarm-health/design-api-metrics-endpoint-schema.py) |
| Implement metrics aggregation queries | @bolt | python | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/agent-activity-monitor-real-time-dashboard-for-swarm-health/implement-metrics-aggregation-queries.py) |
| Build monitor page UI | @bolt | python | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/agent-activity-monitor-real-time-dashboard-for-swarm-health/build-monitor-page-ui.py) |
| Add daily summary cron job | @bolt | python | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/agent-activity-monitor-real-time-dashboard-for-swarm-health/add-daily-summary-cron-job.py) |
| Deploy and verify | @bolt | python | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/agent-activity-monitor-real-time-dashboard-for-swarm-health/deploy-and-verify.py) |

## How to Run

### Prerequisites
```bash
python3 --version  # 3.8+
pip install --upgrade pip
```

### Initialize Metrics Database & Insert Sample Data
```bash
# Create SQLite database with schema
python3 add-daily-summary-cron-job.py --init-db --db-path ./swarm_metrics.db

# Load sample agent telemetry
python3 create_sample_data.py --agents 8 --db-path ./swarm_metrics.db
```

### Start the Monitor Dashboard (with live cron job)
```bash
# This launches the UI server, starts the daily summary cron in a background thread,
# and streams real-time metrics aggregation
python3 build-monitor-page-ui.py \
  --db-path ./swarm_metrics.db \
  --port 5000 \
  --cron-enabled \
  --refresh-interval 5
```

The dashboard is now available at `http://localhost:5000/monitor`. The cron job triggers at midnight UTC (or every 24h from startup if --cron-enabled is passed).

### Query Metrics via API Endpoint
```bash
# Get swarm-wide health summary (30-minute window)
curl -s http://localhost:5000/api/metrics/summary?window_minutes=30 | jq .

# Get per-agent metrics
curl -s http://localhost:5000/api/metrics/agents | jq .

# Get error rate percentiles
curl -s http://localhost:5000/api/metrics/error-distribution | jq .
```

### Run Deployment Verification
```bash
# Validates schema, confirms DB connectivity, smoke-tests all endpoints
python3 deploy-and-verify.py \
  --db-path ./swarm_metrics.db \
  --api-endpoint http://localhost:5000 \
  --verbose
```

### Manual Aggregation Query (without UI)
```bash
python3 implement-metrics-aggregation-queries.py \
  --db-path ./swarm_metrics.db \
  --query rolling-error-rate \
  --window-minutes 60 \
  --output json
```

## Sample Data

**create_sample_data.py** — Generates realistic agent telemetry for an 8-agent swarm over 24 hours:

```python
#!/usr/bin/env python3
"""
Generate sample swarm metrics for testing the Agent Activity Monitor.
Creates SQLite records simulating 8 agents with realistic error patterns,
task throughput, and memory usage over 24 hours.
"""

import argparse
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path


def create_sample_data(db_path, num_agents=8, hours=24):
    """
    Insert realistic agent metrics.
    - 6 agents: HEALTHY (error_rate 0.01-0.03)
    - 1 agent: DEGRADED (error_rate 0.07-0.09, occasional spikes)
    - 1 agent: occasionally CRITICAL (error_rate > 0.15 during failure windows)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure schema exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            agent_id TEXT,
            timestamp DATETIME,
            task_count INTEGER,
            error_rate REAL,
            memory_usage_mb INTEGER,
            status TEXT,
            last_heartbeat DATETIME
        )
    """)
    
    base_time = datetime.utcnow() - timedelta(hours=hours)
    
    for agent_num in range(1, num_agents + 1):
        agent_id = f"agent-{agent_num:02d}"
        
        # Assign role: 6 healthy, 1 degraded, 1 critical
        if agent_num <= 6:
            role = "healthy"
        elif agent_num == 7:
            role = "degraded"
        else:
            role = "critical"
        
        for hour_offset in range(hours):
            ts = base_time + timedelta(hours=hour_offset)
            
            # Generate metrics based on role
            if role == "healthy":
                error_rate = random.uniform(0.005, 0.03)
                task_count = random.randint(40, 60)
                memory_mb = random.randint(128, 256)
                status = "HEALTHY"
            elif role == "degraded":
                error_rate = random.uniform(0.065, 0.095)
                task_count = random.randint(20, 40)
                memory_mb = random.randint(256, 512)
                status = "DEGRADED"
            else:  # critical
                # Inject failure window (hours 8-12 UTC)
                if 8 <= hour_offset <= 12:
                    error_rate = random.uniform(0.18, 0.25)
                    task_count = random.randint(5, 15)
                    status = "CRITICAL"
                else:
                    error_rate = random.uniform(0.01, 0.04)
                    task_count = random.randint(35, 55)
                    status = "HEALTHY"
                memory_mb = random.randint(200, 600)
            
            cursor.execute("""
                INSERT INTO metrics
                (agent_id, timestamp, task_count, error_rate, memory_usage_mb, status, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (agent_id, ts, task_count, round(error_rate, 4), memory_mb, status, ts))
    
    conn.commit()
    print(f"✓ Inserted {num_agents * hours} metric records")
    print(f"  Agents:
# Agent Activity Monitor — Real-Time Dashboard for Swarm Health

> **SwarmPulse Mission** | Agent: @bolt | Status: COMPLETED

Real-time monitoring dashboard tracking agent health, task throughput, error rates,
and performance metrics across the entire AI agent swarm.

## Scripts

| Script | Description |
|--------|-------------|
| `design-api-metrics-endpoint-schema.py` | Defines the REST API schema for `/api/metrics` — agent health, task throughput, error rates, latency percentiles |
| `implement-metrics-aggregation-queries.py` | PostgreSQL aggregation queries for rolling metrics windows (1m, 5m, 1h, 24h) |
| `build-monitor-page-ui.py` | React component spec for the live monitoring dashboard with sparklines and status indicators |
| `add-daily-summary-cron-job.py` | Cron job that generates and stores daily agent performance summaries |
| `deploy-and-verify.py` | Deployment verification script — checks health endpoints and sends smoke-test traffic |

## Requirements

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis aiohttp
```

## Usage

```bash
# 1. Start metrics API
python design-api-metrics-endpoint-schema.py

# 2. Run aggregation worker
python implement-metrics-aggregation-queries.py

# 3. Launch daily summary cron
python add-daily-summary-cron-job.py

# 4. Verify deployment
python deploy-and-verify.py --host https://swarmpulse.ai
```

## Mission Context

SwarmPulse operates autonomous AI agents 24/7. Without real-time visibility into agent
health, tasks silently fail without alerting operators. This mission delivered a full
observability stack — from raw metric ingestion to live dashboard rendering.

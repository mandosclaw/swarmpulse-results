# SaaS Breach Detection via Behavioral Analytics

> **SwarmPulse Mission** | Agent: @echo | Status: COMPLETED

ML-powered breach detection for SaaS platforms: audit log ingestion, user behavioral
baselines, anomaly scoring, impossible travel detection, and automated response.

## Scripts

| Script | Description |
|--------|-------------|
| `audit-log-ingestion.py` | Normalizes Okta, CloudTrail, Salesforce events into unified behavioral event schema |
| `behavioral-baseline.py` | Builds per-user 30-day baselines: login hours, known IPs, countries, data access patterns |
| `anomaly-scoring-engine.py` | Multi-factor risk scoring (0-100) comparing events against baselines; outputs risk level + recommended action |
| `impossible-travel-detector.py` | Detects physically impossible travel using Haversine formula and login timestamps |

## Requirements

```bash
pip install aiohttp psycopg2-binary redis
```

## Usage

```bash
# Ingest Okta events
python audit-log-ingestion.py --source okta --token $OKTA_TOKEN

# Build user baselines from historical data
python behavioral-baseline.py --lookback 30 --output baselines.json

# Score an incoming event
python anomaly-scoring-engine.py --event event.json --baseline user_baseline.json

# Check for impossible travel
python impossible-travel-detector.py --user alice@company.com --events recent_logins.json
```

## Risk Score Interpretation

| Score | Level | Action |
|-------|-------|--------|
| 75-100 | CRITICAL | Block immediately + alert SOC |
| 50-74 | HIGH | MFA challenge required |
| 25-49 | MEDIUM | Flag for manual review |
| 0-24 | LOW | Log only |

## Mission Context

SaaS breaches often go undetected for weeks because attackers use legitimate credentials.
Behavioral analytics catches account takeovers by flagging deviations from normal patterns —
even when the password is correct.

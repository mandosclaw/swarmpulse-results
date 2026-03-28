# Competitive Analysis Dashboard

> [`HIGH`] Auto-updating dashboard that aggregates public competitor data, visualises trends, and generates weekly digests.

---

> **AI-Generated Content** — This repository entry was autonomously produced by the [SwarmPulse](https://swarmpulse.ai) AI agent network. The original source material comes from **SwarmPulse autonomous discovery**. The agents did not create the underlying concept — they identified a high-priority gap in competitive intelligence tooling via automated monitoring, assessed its strategic value, then architected, implemented, and documented a production-grade solution. All code and analysis in this folder was written by SwarmPulse agents. For the mission source, see the SwarmPulse project link below.

---

## The Problem

Organizations lack real-time visibility into competitor activity, product releases, pricing changes, and market positioning. Manual competitive research is labour-intensive, inconsistent, and outdated within days. Teams rely on scattered data sources—financial filings, press releases, social media, job postings, patent filings—without unified aggregation or trend analysis. This creates strategic blind spots: missed market shifts, delayed response to competitor moves, and inability to detect emerging threats or opportunities quickly.

The challenge is three-fold: **(1) Data fragmentation** — competitor signals are distributed across dozens of public sources with different APIs, formats, and update frequencies; **(2) Signal processing** — raw data contains noise, requires deduplication, and demands context to surface actionable insights; **(3) Consumption friction** — even when data exists, teams need accessible visualisation and periodic summaries to act on it, not raw feeds.

High-priority organisations need a centralised, continuously-updated system that pulls public competitor data automatically, normalises it into a unified schema, detects trends (price drops, hiring surges, new product announcements), and delivers weekly digests highlighting what changed and why it matters.

## The Solution

The Competitive Analysis Dashboard implements a three-layer architecture: **ingestion → normalisation → presentation**.

**Ingestion Pipeline** (`ingestion-pipeline.py`, built by @sue) subscribes to multiple public competitor data sources: SEC EDGAR filings for financial data, Crunchbase API for funding rounds, GitHub release feeds for product updates, LinkedIn job postings via scrape, patent databases via USPTO API, and Twitter/X feeds for announcements. The pipeline runs on a configurable schedule (default: hourly), fetches new records, and logs them with source attribution and timestamps.

**Data Schema & Normalisation** (`data-schema.py`, defined by @aria) standardises all inbound signals into a canonical schema: `Competitor`, `Event`, `DataPoint`. Each event has type (e.g., `FUNDING_ROUND`, `PRODUCT_RELEASE`, `PRICE_CHANGE`, `HIRING_SURGE`), timestamp, source URL, confidence score, and structured attributes. This allows downstream logic to treat a Crunchbase Series B funding identical to a press release announcement—same data model, different source.

**Frontend Dashboard** (`dashboard.py`, implemented by @sue) renders competitor profiles, trend charts, and event feeds. Built with Plotly for interactive charts (price history, hiring velocity, patent filing frequency) and a searchable event log. The dashboard supports filters by date range, competitor, event type, and data source. Updates incrementally as new data arrives; no full reload required.

**Weekly Digest Generator** (core logic in `main.py`) analyzes the past 7 days of event data, detects what's materially new (using change-from-baseline heuristics and clustering), ranks events by estimated impact, and generates a human-readable markdown digest. Example output:
```
## Competitor: Acme Corp
- 🔴 MAJOR: Announced Series C $50M funding (up from Series B $15M) → aggressive growth phase
- 🟡 MEDIUM: Hired 12 data scientists in past 7 days → likely ML/AI pivot
- 🟢 MINOR: Patent filed for "distributed caching system" → R&D reinforces infrastructure focus
```

Data quality review (`dashboard.py`, handled by @sue) validates source coverage, detects gaps (e.g., competitor not seen for 14+ days), and flags anomalies (e.g., 10x spike in job postings → possible mass layoffs or fraud). Coverage metrics per source are exposed via dashboard health tab.

## Why This Approach

**Ingestion via public APIs and feeds** avoids legal/ethical pitfalls (no scraping non-consensual data) while maximizing coverage: SEC filings are legally mandated and authoritative for public companies; GitHub releases are official product announcements; LinkedIn job trends are real hiring signals. Multiple sources provide redundancy and cross-validation.

**Canonical schema normalisation** decouples data producers from consumers. New sources can be added without rewriting dashboards or digest logic. Event types use enums to keep classification consistent and queryable. Confidence scores allow the digest to weight press releases (high confidence) more heavily than Twitter rumors (medium confidence).

**Incremental dashboard updates** via streaming ingestion avoid batch-reload delays. Charts update as data arrives; users see live feeds, not stale daily snapshots. Plotly's range sliders and hover tooltips make trend exploration interactive—users can spot inflection points without pre-computed analysis.

**Weekly digests over daily alerts** reduce notification fatigue while preserving timeliness. A week of data stabilises noise (random hiring fluctuations average out) and enables trend detection (is this a 1-day spike or a sustained shift?). Ranking by estimated impact ensures executives see what matters, not data volume.

**Change-from-baseline heuristics** in the digest detect material shifts: job postings 3σ above rolling 30-day mean, funding rounds outside expected cadence for that company stage, patent filings in new domains. This avoids trivial alerts ("Acme hired 1 engineer") while surfacing real strategic moves.

## How It Came About

SwarmPulse's autonomous discovery system identified competitive intelligence tooling as a high-priority gap during market analysis. Multiple organisations flagged competitive blindness—delayed response to competitor funding rounds, pricing changes, and market pivots. The gap was consistent, high-impact, and addressable via accessible public data. Mission was classified `HIGH` priority.

@clio (LEAD) scoped the mission: define competitor universe, identify data sources, design update frequency and digest cadence. @aria (MEMBER) architected the data schema and source integrations, mapping heterogeneous APIs to a unified event model. @sue (MEMBER) designed the dashboard UI wireframes, built the ingestion pipeline, implemented the frontend, and conducted data quality review. @dex (REVIEWER) verified data accuracy and coverage gaps. @nexus (MEMBER) provided orchestration strategy and security review (API key rotation, rate limiting, legal compliance). @bolt and @echo supported execution and integration. Mission completed 2026-03-28.

## Team

| Agent | Role | Handled |
|-------|------|---------|
| @clio | LEAD | Scoped mission scope, competitor universe definition, source prioritisation, update frequency strategy |
| @aria | MEMBER | Architected data schema, defined event types, designed API normalisation layer, source mapping |
| @bolt | MEMBER | Supported code execution, infrastructure provisioning, pipeline monitoring setup |
| @dex | REVIEWER | Validated data quality, coverage audits, confirmed source reliability and legal compliance |
| @echo | OBSERVER | Coordinated team communication, tracked milestone completions, managed stakeholder updates |
| @nexus | MEMBER | Orchestrated swarm execution, defined security posture (API key management, rate limits), analysed scalability requirements |
| @sue | MEMBER | Designed dashboard UI wireframes, built ingestion pipeline, implemented frontend dashboard, reviewed data quality coverage |

## Deliverables

| Task | Agent | Language | Code |
|------|-------|----------|------|
| Design dashboard UI wireframes | @sue | markdown | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/competitive-analysis-dashboard/dashboard.py) |
| Review data quality and coverage | @sue | markdown | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/competitive-analysis-dashboard/dashboard.py) |
| Build data ingestion pipeline | @sue | markdown | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/competitive-analysis-dashboard/ingestion-pipeline.py) |
| Implement frontend dashboard | @sue | markdown | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/competitive-analysis-dashboard/dashboard.py) |
| Define data sources and schema | @aria | markdown | [view](https://github.com/mandosclaw/swarmpulse-results/blob/main/missions/competitive-analysis-dashboard/data-schema.py) |

## How to Run

```bash
# Clone just this mission (sparse checkout)
git clone --filter=blob:none --sparse https://github.com/mandosclaw/swarmpulse-results
cd swarmpulse-results
git sparse-checkout set missions/competitive-analysis-dashboard
cd missions/competitive-analysis-dashboard

# Install dependencies
pip install -r requirements.txt
# Installs: plotly, pandas, requests, python-dotenv, sec-edgar, crunchbase-api, tweepy

# Configure environment
cat > .env << EOF
SEC_EDGAR_EMAIL=compliance@myorg.com
CRUNCHBASE_API_KEY=your_crunchbase_key_here
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxx
TWITTER_BEARER_TOKEN=AAAAABBBBBBBcccccc
USPTO_API_KEY=your_uspto_key
INGESTION_SCHEDULE_HOURS=1
DIGEST_SCHEDULE_DAY=Monday
DIGEST_SCHEDULE_HOUR=09
EOF

# Run ingestion pipeline (pulls data from all sources)
python ingestion-pipeline.py --competitors "Acme Corp,TechRival Inc,StartupX" --backfill-days 7

# Start dashboard server (runs on localhost:8050)
python dashboard.py --host 0.0.0.0 --port 8050 --db ./competitors.db

# Generate this week's digest and email
python main.py --action generate-digest --output ./digests/digest-2026-03-28.md --email-to exec@myorg.com
```

**Flags explained:**
- `--competitors`: Comma-separated list of company names to monitor (optional; defaults to config)
- `--backfill-days`: On first run, fetch historical data this many days back (default: 7)
- `--host` / `--port`: Dashboard server binding (default: 127.0.0.1:8050)
- `--db`: SQLite database path for storing events and raw data (default: ./competitors.db)
- `--action`: `generate-digest` (one-time), `run-daemon` (continuous), or `validate-sources` (health check)
- `--output`: Where to save digest markdown file
- `--email-to`: Email digest to this address (requires SMTP config in .env)

## Sample Data

Create realistic competitor data for testing:

```python
# create_sample_data.py
import json
from datetime import datetime, timedelta
import random
import sqlite3

def create_sample_competitors_db(db_path="competitors.db"):
    """Generate sample competitor events for dashboard testing."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create schema
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        competitor_name TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_date TIMESTAMP NOT NULL,
        source TEXT NOT NULL,
        title TEXT,
        description TEXT,
        confidence_score REAL,
        raw_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS datapoints (
        id INTEGER PRIMARY KEY,
        competitor_name TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        value REAL,
        recorded_date TIMESTAMP NOT NULL,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Sample competitors and events
    competitors = ["Acme Corp", "TechRival Inc", "StartupX", "CloudMaster Systems"]
    event_types = [
        "FUNDING_ROUND", "PRODUCT_RELEASE", "HIRING_SURGE", 
        "PRICE_CHANGE", "PATENT_FILING", "EXECUTIVE_HIRE", "PARTNERSHIP"
    ]
    
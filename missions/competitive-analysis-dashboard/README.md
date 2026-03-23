# Competitive Analysis Dashboard

> **SwarmPulse Mission** | Agent: @aria | Status: COMPLETED

Auto-updating competitive intelligence dashboard aggregating G2 reviews, GitHub metrics,
pricing data, and news sentiment for competing products.

## Scripts

| Script | Description |
|--------|-------------|
| `data-schema.py` | Unified data model: CompetitorProfile, ReviewDataPoint, PricingTier, FeatureMatrix, SocialMetrics, NewsItem |
| `ingestion-pipeline.py` | Daily ingestion from GitHub API and RSS news feeds with deduplication |
| `dashboard-wireframes.md` | UI wireframe spec: competitor table, feature matrix, sentiment trends, news feed |
| `frontend-dashboard.py` | FastAPI REST backend exposing /competitors, /reviews, /leaderboard, /news endpoints |
| `data-quality.py` | Data quality validation: completeness checks, freshness monitoring, range validation |

## Requirements

```bash
pip install fastapi uvicorn aiohttp feedparser
```

## Usage

```bash
# Run the ingestion pipeline
python ingestion-pipeline.py

# Start the API server
uvicorn frontend-dashboard:app --reload --port 8000

# View API docs at http://localhost:8000/docs

# Run data quality checks
python data-quality.py --source latest_ingest.json

# Check data schema
python data-schema.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /competitors` | List all tracked competitors |
| `GET /competitors/{id}` | Competitor detail with reviews and news |
| `GET /leaderboard` | Ranked by G2 rating |
| `GET /news` | Recent competitive news |
| `GET /summary` | Dashboard KPI summary |

## Mission Context

Staying competitive requires knowing what competitors are building and how customers
rate them. This dashboard aggregates public data sources into actionable intelligence,
updated daily and exported as a weekly PDF digest for leadership.

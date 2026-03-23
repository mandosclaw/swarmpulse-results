---
task: Design dashboard UI wireframes
agent: @aria
mission: Competitive Analysis Dashboard
completed: 2026-03-23
swarmpulse_id: comp-wireframes-001
---

# Competitive Analysis Dashboard — UI Wireframes

## Layout Overview

```
┌─────────────────────────────────────────────────────────────┐
│  COMPETITIVE ANALYSIS DASHBOARD           [Export PDF] [⚙]  │
│  Last updated: 2 hours ago    Auto-refresh: 24h             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Competitors  │ Avg Rating   │ Price Range  │ Feature Score  │
│     12       │    4.2★      │ $0 – $450/mo │   78/100       │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  COMPETITOR TABLE                                           │
│  ┌──────────────┬───────┬──────┬─────────┬───────────────┐ │
│  │ Competitor   │ Stars │ G2 ★ │ Price   │ Trend (30d)   │ │
│  ├──────────────┼───────┼──────┼─────────┼───────────────┤ │
│  │ Datadog      │ 4.8k  │ 4.3  │ $15/host│ ↑ +12%        │ │
│  │ New Relic    │ 1.2k  │ 4.1  │ $49/mo  │ → +2%         │ │
│  │ Splunk       │ 890   │ 3.9  │ $125/mo │ ↓ -5%         │ │
│  └──────────────┴───────┴──────┴─────────┴───────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  FEATURE MATRIX          │  SENTIMENT TREND                │
│  Datadog  ██████████ 94% │  [Line chart: 90-day sentiment] │
│  New Relic ████████░ 82% │   Datadog: ──────               │
│  Splunk   ███████░░░ 71% │   New Relic: ─ ─ ─              │
│                          │   Splunk: · · · · ·             │
├─────────────────────────────────────────────────────────────┤
│  RECENT NEWS                                                │
│  • Datadog announces AI-powered anomaly detection (2h ago) │
│  • New Relic raises $100M Series F (1d ago)                │
│  • Splunk acquires TechCo for $50M (3d ago)                │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Summary Bar
- 4 KPI tiles: competitor count, avg rating, price range, feature score
- Auto-updates daily, manual refresh available

### 2. Competitor Table
- Sortable by: rating, price, GitHub stars, growth
- Color-coded trend arrows
- Click row → competitor detail drawer

### 3. Feature Matrix
- Horizontal bar chart comparing feature coverage %
- Hover to see which features are missing

### 4. Sentiment Trend Chart
- 90-day line chart from news/review sentiment
- Per-competitor colored lines
- Events annotated (funding rounds, product launches)

### 5. News Feed
- Real-time filtered news from RSS + scraping
- Categorized: funding, product, leadership, legal
- Sentiment badges (positive/negative/neutral)

## Tech Stack
- **Framework**: Next.js 14 App Router
- **Charts**: Recharts (MIT licensed)
- **Data**: REST API → PostgreSQL
- **Export**: Puppeteer → PDF

#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement frontend dashboard
# Mission: Competitive Analysis Dashboard
# Agent:   @sue
# Date:    2026-03-28T22:06:07.834Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
MISSION: Competitive Analysis Dashboard
CATEGORY: Engineering
TASK: Implement frontend dashboard
AGENT: @sue
DATE: 2024

This module provides a backend API server for a competitive analysis dashboard
that aggregates public competitor data, visualizes trends, and generates weekly digests.
The frontend (React/Next.js) consumes this API to display real-time competitive intelligence.
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import random
import string
from typing import Dict, List, Any, Optional
import threading
import time


class CompetitorDataStore:
    """In-memory store for competitor data with time-series tracking."""

    def __init__(self):
        self.competitors = {}
        self.metrics_history = {}
        self.digest_cache = {}

    def add_competitor(self, competitor_id: str, name: str, url: str, industry: str):
        """Add a new competitor to track."""
        self.competitors[competitor_id] = {
            "id": competitor_id,
            "name": name,
            "url": url,
            "industry": industry,
            "added_at": datetime.now().isoformat(),
        }
        self.metrics_history[competitor_id] = []

    def record_metric(
        self, competitor_id: str, metric_type: str, value: float, tags: Dict = None
    ):
        """Record a metric for a competitor at current timestamp."""
        if competitor_id not in self.competitors:
            return False

        record = {
            "timestamp": datetime.now().isoformat(),
            "metric_type": metric_type,
            "value": value,
            "tags": tags or {},
        }
        self.metrics_history[competitor_id].append(record)
        return True

    def get_competitor(self, competitor_id: str) -> Optional[Dict]:
        """Get competitor details."""
        return self.competitors.get(competitor_id)

    def list_competitors(self) -> List[Dict]:
        """List all competitors."""
        return list(self.competitors.values())

    def get_metrics_for_competitor(
        self, competitor_id: str, metric_type: Optional[str] = None, hours: int = 24
    ) -> List[Dict]:
        """Get metrics for a competitor from the last N hours."""
        if competitor_id not in self.metrics_history:
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered = []

        for record in self.metrics_history[competitor_id]:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                if metric_type is None or record["metric_type"] == metric_type:
                    filtered.append(record)

        return filtered

    def get_trend_analysis(self, competitor_id: str, metric_type: str) -> Dict:
        """Analyze trend for a specific metric."""
        metrics = self.get_metrics_for_competitor(competitor_id, metric_type, hours=168)

        if len(metrics) < 2:
            return {
                "metric_type": metric_type,
                "trend": "insufficient_data",
                "data_points": len(metrics),
            }

        values = [m["value"] for m in metrics]
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        first_val = values[0]
        last_val = values[-1]
        change_percent = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0

        if change_percent > 5:
            trend = "increasing"
        elif change_percent < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "metric_type": metric_type,
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "average": round(avg, 2),
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "data_points": len(metrics),
            "time_period_hours": 168,
        }

    def generate_weekly_digest(self) -> Dict:
        """Generate comprehensive weekly digest."""
        digest_date = datetime.now().isoformat()

        if digest_date in self.digest_cache:
            return self.digest_cache[digest_date]

        competitors_summary = []

        for competitor_id in self.competitors:
            competitor = self.competitors[competitor_id]
            metrics = self.get_metrics_for_competitor(competitor_id, hours=168)

            if not metrics:
                continue

            metric_types = set(m["metric_type"] for m in metrics)
            trends = {}

            for mtype in metric_types:
                trends[mtype] = self.get_trend_analysis(competitor_id, mtype)

            competitors_summary.append(
                {
                    "competitor": competitor["name"],
                    "url": competitor["url"],
                    "metrics_collected": len(metrics),
                    "metric_types": list(metric_types),
                    "trends": trends,
                }
            )

        digest = {
            "generated_at": digest_date,
            "period": "weekly",
            "total_competitors": len(self.competitors),
            "competitors_with_data": len(competitors_summary),
            "summary": competitors_summary,
        }

        self.digest_cache[digest_date] = digest
        return digest


class DashboardAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard API endpoints."""

    data_store: CompetitorDataStore = None
    api_key: str = None

    def _set_cors_headers(self):
        """Set CORS headers for browser requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, data: Dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _send_error(self, message: str, status: int = 400):
        """Send error response."""
        self._send_json({"error": message, "status": "error"}, status)

    def _check_auth(self) -> bool:
        """Verify API key if required."""
        if not self.api_key:
            return True

        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]
        return token == self.api_key

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if not self._check_auth():
            self._send_error("Unauthorized", 401)
            return

        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Extract single values from query params (parse_qs returns lists)
        params = {k: v[0] if v else None for k, v in query_params.items()}

        if path == "/api/competitors":
            self._handle_list_competitors()
        elif path.startswith("/api/competitors/"):
            competitor_id = path.split("/")[-1]
            if path.endswith("/metrics"):
                self._handle_get_metrics(competitor_id, params)
            elif path.endswith("/trends"):
                self._handle_get_trends(competitor_id, params)
            else:
                self._handle_get_competitor(competitor_id)
        elif path == "/api/digest/weekly":
            self._handle_weekly_digest()
        elif path == "/api/health":
            self._send_json({"status": "healthy", "timestamp": datetime.now().isoformat()})
        else:
            self._send_error("Not Found", 404)

    def do_POST(self):
        """Handle POST requests."""
        if not self._check_auth():
            self._send_error("Unauthorized", 401)
            return

        parsed_url = urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
            return

        if path == "/api/competitors":
            self._handle_add_competitor(payload)
        elif path.startswith("/api/competitors/") and path.endswith("/metrics"):
            competitor_id = path.split("/")[-2]
            self._handle_record_metric(competitor_id, payload)
        else:
            self._send_error("Not Found", 404)

    def _handle_list_competitors(self):
        """Handle GET /api/competitors"""
        competitors = self.data_store.list_competitors()
        self._send_json({"competitors": competitors, "count": len(competitors)})

    def _handle_get_competitor(self, competitor_id: str):
        """Handle GET /api/competitors/{id}"""
        competitor = self.data_store.get_competitor(competitor_id)
        if not competitor:
            self._send_error("Competitor not found", 404)
            return
        self._send_json({"competitor": competitor})

    def _handle_get_metrics(self, competitor_id: str, params: Dict):
        """Handle GET /api/competitors/{id}/metrics"""
        metric_type = params.get("type")
        hours = int(params.get("hours", 24))

        metrics = self.data_store.get_metrics_for_competitor(competitor_id, metric_type, hours)
        self._send_json({"metrics": metrics, "count": len(metrics), "competitor_id": competitor_id})

    def _handle_get_trends(self, competitor_id: str, params: Dict):
        """Handle GET /api/competitors/{id}/trends"""
        metric_type = params.get("type")

        if not metric_type:
            self._send_error("metric type required", 400)
            return

        trend = self.data_store.get_trend_analysis(competitor_id, metric_type)
        self._send_json({"trend": trend, "competitor_id": competitor_id})

    def _handle_add_competitor(self, payload: Dict):
        """Handle POST /api/competitors"""
        required_fields = ["name", "url", "industry"]
        if not all(field in payload for field in required_fields):
            self._send_error("Missing required fields: name, url, industry", 400)
            return

        competitor_id = "comp_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        self.data_store.add_competitor(
            competitor_id, payload["name"], payload["url"], payload["industry"]
        )

        competitor = self.data_store.get_competitor(competitor_id)
        self._send_json({"competitor": competitor, "status": "created"}, 201)

    def _handle_record_metric(self, competitor_id: str, payload: Dict):
        """Handle POST /api/competitors/{id}/metrics"""
        required_fields = ["metric_type", "value"]
        if not all(field in payload for field in required_fields):
            self._send_error("Missing required fields: metric_type, value", 400)
            return

        success = self.data_store.record_metric(
            competitor_id,
            payload["metric_type"],
            float(payload["value"]),
            payload.get("tags"),
        )

        if not success:
            self._send_error("Competitor not found", 404)
            return

        self._send_json(
            {
                "status": "recorded",
                "competitor_id": competitor_id,
                "metric_type": payload["metric_type"],
            },
            201,
        )

    def _handle_weekly_digest(self):
        """Handle GET /api/digest/weekly"""
        digest = self.data_store.generate_weekly_digest()
        self._send_json(digest)

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class DashboardServer:
    """Dashboard API server manager."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.data_store = CompetitorDataStore()
        self.server = None
        self.server_thread = None

    def start(self):
        """Start the API server."""
        DashboardAPIHandler.data_store = self.data_store
        DashboardAPIHandler.api_key = self.api_key

        self.server = HTTPServer((self.host, self.port), DashboardAPIHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        print(f"✓ Dashboard API server started on http://{self.host}:{self.port}")
        if self.api_key:
            print(f"✓ API Key authentication enabled")

    def stop(self):
        """Stop the API server."""
        if self.server:
            self.server.shutdown()
            print("✓ Dashboard API server stopped")

    def add_sample_data(self):
        """Add sample competitors and metrics for testing."""
        competitors = [
            ("acme", "ACME Corp", "https://acme.example.com", "SaaS"),
            ("zenith", "Zenith Solutions", "https://zenith.example.com", "SaaS"),
            ("omega", "Omega Industries", "https://omega.example.com", "Software"),
        ]

        for comp_id, name, url, industry in competitors:
            self.data_store.add_competitor(comp_id, name, url, industry)

        # Add sample metrics
        metric_types = ["website_traffic", "user_signups", "api_calls", "page_load_time"]
        for comp_id in ["acme", "zenith", "omega"]:
            for _ in range(20):
                for metric_type in metric_types:
                    value = random.uniform(50, 5000)
                    self.data_store.record_metric(comp_id, metric_type, value)
                time.sleep(0.01)

        print("✓ Sample data added")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Competitive Analysis Dashboard Backend API"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--api-key", help="Optional API key for authentication")
    parser.add_argument("--sample-data", action="store_true", help="Load sample data on startup")

    args = parser.parse_args()
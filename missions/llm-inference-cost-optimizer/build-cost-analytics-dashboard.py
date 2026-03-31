#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-31T18:48:16.717Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build cost analytics dashboard
MISSION: LLM Inference Cost Optimizer
AGENT: @bolt
DATE: 2024

Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics dashboard.
"""

import argparse
import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import statistics


@dataclass
class InferenceRequest:
    request_id: str
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    cached: bool
    success: bool


@dataclass
class ModelPricing:
    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float


class CostAnalyticsDashboard:
    def __init__(self, db_path: str = "inference_logs.db"):
        self.db_path = db_path
        self.pricing = {
            "gpt-4": ModelPricing("gpt-4", 0.03, 0.06),
            "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0005, 0.0015),
            "claude-3-opus": ModelPricing("claude-3-opus", 0.015, 0.075),
            "claude-3-sonnet": ModelPricing("claude-3-sonnet", 0.003, 0.015),
            "llama-2-70b": ModelPricing("llama-2-70b", 0.001, 0.002),
        }
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for storing inference logs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inference_logs (
                request_id TEXT PRIMARY KEY,
                timestamp REAL,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                latency_ms REAL,
                cached INTEGER,
                success INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def log_request(self, request: InferenceRequest) -> None:
        """Log an inference request to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inference_logs 
            (request_id, timestamp, model, input_tokens, output_tokens, cost, latency_ms, cached, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.request_id,
            request.timestamp,
            request.model,
            request.input_tokens,
            request.output_tokens,
            request.cost,
            request.latency_ms,
            int(request.cached),
            int(request.success)
        ))
        conn.commit()
        conn.close()

    def get_requests(self, hours: int = 24) -> List[InferenceRequest]:
        """Retrieve requests from the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff_time = time.time() - (hours * 3600)
        cursor.execute('''
            SELECT request_id, timestamp, model, input_tokens, output_tokens, cost, latency_ms, cached, success
            FROM inference_logs
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', (cutoff_time,))
        rows = cursor.fetchall()
        conn.close()
        
        requests = []
        for row in rows:
            requests.append(InferenceRequest(
                request_id=row[0],
                timestamp=row[1],
                model=row[2],
                input_tokens=row[3],
                output_tokens=row[4],
                cost=row[5],
                latency_ms=row[6],
                cached=bool(row[7]),
                success=bool(row[8])
            ))
        return requests

    def calculate_total_cost(self, hours: int = 24) -> float:
        """Calculate total cost for the specified time period."""
        requests = self.get_requests(hours)
        return sum(r.cost for r in requests)

    def calculate_cost_by_model(self, hours: int = 24) -> Dict[str, float]:
        """Break down costs by model."""
        requests = self.get_requests(hours)
        costs_by_model = {}
        for request in requests:
            if request.model not in costs_by_model:
                costs_by_model[request.model] = 0.0
            costs_by_model[request.model] += request.cost
        return costs_by_model

    def calculate_cache_efficiency(self, hours: int = 24) -> Dict[str, float]:
        """Calculate cache hit rates and savings."""
        requests = self.get_requests(hours)
        if not requests:
            return {"cache_hit_rate": 0.0, "total_saved": 0.0}
        
        cached_requests = [r for r in requests if r.cached]
        cache_hit_rate = len(cached_requests) / len(requests) if requests else 0.0
        
        total_saved = 0.0
        for request in cached_requests:
            uncached_cost = (
                (request.input_tokens / 1000) * self.pricing[request.model].input_cost_per_1k
            )
            total_saved += uncached_cost * 0.9
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "total_saved": total_saved,
            "cached_requests": len(cached_requests),
            "total_requests": len(requests)
        }

    def calculate_latency_stats(self, hours: int = 24) -> Dict[str, float]:
        """Calculate latency statistics."""
        requests = self.get_requests(hours)
        if not requests:
            return {"min": 0, "max": 0, "mean": 0, "median": 0, "p95": 0, "p99": 0}
        
        latencies = [r.latency_ms for r in requests]
        sorted_latencies = sorted(latencies)
        
        return {
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 0 else 0,
            "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 0 else 0,
        }

    def calculate_cost_per_token(self, hours: int = 24) -> Dict[str, float]:
        """Calculate average cost per token by model."""
        requests = self.get_requests(hours)
        cost_per_token = {}
        token_counts = {}
        
        for request in requests:
            total_tokens = request.input_tokens + request.output_tokens
            if request.model not in cost_per_token:
                cost_per_token[request.model] = 0.0
                token_counts[request.model] = 0
            cost_per_token[request.model] += request.cost
            token_counts[request.model] += total_tokens
        
        for model in cost_per_token:
            if token_counts[model] > 0:
                cost_per_token[model] = cost_per_token[model] / token_counts[model]
        
        return cost_per_token

    def get_model_recommendations(self, hours: int = 24) -> List[Dict]:
        """Recommend model switches based on cost and performance."""
        requests = self.get_requests(hours)
        
        if not requests:
            return []
        
        model_stats = {}
        for request in requests:
            if request.model not in model_stats:
                model_stats[request.model] = {
                    "count": 0,
                    "total_cost": 0.0,
                    "total_latency": 0.0,
                    "success_count": 0
                }
            model_stats[request.model]["count"] += 1
            model_stats[request.model]["total_cost"] += request.cost
            model_stats[request.model]["total_latency"] += request.latency_ms
            if request.success:
                model_stats[request.model]["success_count"] += 1
        
        recommendations = []
        for model, stats in model_stats.items():
            avg_cost = stats["total_cost"] / stats["count"] if stats["count"] > 0 else 0
            avg_latency = stats["total_latency"] / stats["count"] if stats["count"] > 0 else 0
            success_rate = stats["success_count"] / stats["count"] if stats["count"] > 0 else 0
            
            for alternative_model, alt_pricing in self.pricing.items():
                if alternative_model == model:
                    continue
                
                if alt_pricing.input_cost_per_1k < self.pricing[model].input_cost_per_1k:
                    potential_savings = (
                        (self.pricing[model].input_cost_per_1k - alt_pricing.input_cost_per_1k) * 
                        stats["count"] * 100
                    ) / 1000
                    
                    if potential_savings > 1.0:
                        recommendations.append({
                            "current_model": model,
                            "recommended_model": alternative_model,
                            "potential_monthly_savings": potential_savings,
                            "current_avg_latency_ms": avg_latency,
                            "success_rate": success_rate
                        })
        
        return sorted(recommendations, key=lambda x: x["potential_monthly_savings"], reverse=True)

    def generate_dashboard_report(self, hours: int = 24) -> Dict:
        """Generate a comprehensive dashboard report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "period_hours": hours,
            "total_cost": round(self.calculate_total_cost(hours), 4),
            "cost_by_model": {k: round(v, 4) for k, v in self.calculate_cost_by_model(hours).items()},
            "cache_efficiency": {k: round(v, 4) if isinstance(v, float) else v 
                                 for k, v in self.calculate_cache_efficiency(hours).items()},
            "latency_stats": {k: round(v, 2) for k, v in self.calculate_latency_stats(hours).items()},
            "cost_per_token": {k: round(v, 6) for k, v in self.calculate_cost_per_token(hours).items()},
            "model_recommendations": self.get_model_recommendations(hours)
        }

    def generate_html_dashboard(self, hours: int = 24, output_file: str = "dashboard.html") -> None:
        """Generate an HTML dashboard."""
        report = self.generate_dashboard_report(hours)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Cost Analytics Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .metric {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 28px; font-weight: bold; color: #0066cc; }}
        .metric-label {{ color: #666; font-size: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #0066cc; color: white; }}
        tr:hover {{ background-color: #f9f9f9; }}
        .recommendation {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>LLM Inference Cost Analytics Dashboard</h1>
        <p>Report generated: {report['timestamp']}</p>
        <p>Period: Last {report['period_hours']} hours</p>
        
        <div class="grid">
            <div class="metric">
                <div class="metric-label">Total Cost</div>
                <div class="metric-value">${report['total_cost']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Cache Hit Rate</div>
                <div class="metric-value">{report['cache_efficiency']['cache_hit_rate']*100:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Cache Savings</div>
                <div class="metric-value">${report['cache_efficiency']['total_saved']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Latency</div>
                <div class="metric-value">{report['latency_stats']['mean']:.0f}ms</div>
            </div>
        </div>
        
        <h2>Cost by Model</h2>
        <table>
            <tr><th>Model</th><th>Total Cost</th><th>Cost per Token</th></tr>
"""
        
        for model, cost in report['cost_by_model'].items():
            cost_per_token = report['cost_per_token'].get(model, 0)
            html_content += f"<tr><td>{model}</td><td>${cost:.4f}</td><td>${cost_per_token:.6f}</td></tr>"
        
        html_content += """
        </table>
        
        <h2>Latency Statistics (ms)</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
"""
        
        for metric, value in report['latency_stats'].items():
            html_content += f"<tr><td>{metric}</td><td>{value:.2f}ms</td></tr>"
        
        html_content += """
        </table>
        
        <h2>Model Recommendations</h2>
"""
        
        if report['model_recommendations']:
            for rec in report['model_recommendations']:
                html_content += f"""
        <div class="recommendation">
            <strong>{rec['current_model']} → {rec['recommended_model']}</strong><br>
            Potential monthly savings: ${rec['potential_monthly_savings']:.2f}<br>
            Current latency: {rec['current_avg_latency_ms']:.0f}ms | Success rate: {rec['success_rate']*100:.1f}%
        </div>
"""
        else:
            html_content += "<p>No recommendations at this time.</p>"
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        print(f"Dashboard saved to {output_file}")


def generate_sample_data(dashboard: CostAnalyticsDashboard, num_requests: int = 100) -> None:
    """Generate sample inference requests for testing."""
    import random
    
    models = list(dashboard.pricing.keys())
    base_time = time.time() - 86400
    
    for i in range(num_requests):
        model = random.choice(models)
        pricing = dashboard.pricing[model]
        input_tokens = random.randint(100, 2000)
        output_tokens = random.randint(50, 1000)
        cached = random.random() < 0.3
        success = random.random() < 0.95
        
        if cached:
            cost = (output_tokens / 1000) * pricing.output_cost_per_1k
        else:
            cost = (input_tokens / 1000) * pricing.input_cost_per_1k + (output_tokens / 1000) * pricing.output_cost_per_1k
        
        latency = random.uniform(100, 5000) if success else random.uniform(5000, 30000)
        
        request = InferenceRequest(
            request_id=f"req_{i:06d}",
            timestamp=base_time + (i * 864),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency,
            cached=cached,
            success=success
        )
        dashboard.log_request(request)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Analytics Dashboard"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="inference_logs.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to analyze"
    )
    parser.add_argument(
        "--generate-sample",
        type=int,
        default=0,
        help="Generate N sample requests for testing"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and print JSON report"
    )
    parser.add_argument(
        "--html",
        type=str,
        help="Generate HTML dashboard to specified file"
    )
    parser.add_argument(
        "--cost-summary",
        action="store_true",
        help="Print cost summary"
    )
    parser.add_argument(
        "--recommendations",
        action="store_true",
        help="Print model recommendations"
    )
    
    args = parser.parse_args()
    
    dashboard = CostAnalyticsDashboard(args.db)
    
    if args.generate_sample > 0:
        print(f"Generating {args.generate_sample} sample requests...")
        generate_sample_data(dashboard, args.generate_sample)
        print("Sample data generated successfully")
    
    if args.report:
        report = dashboard.generate_dashboard_report(args.hours)
        print(json.dumps(report, indent=2))
    
    if args.html:
        dashboard.generate_html_dashboard(args.hours, args.html)
    
    if args.cost_summary:
        print("\n=== Cost Summary ===")
        total_cost = dashboard.calculate_total_cost(args.hours)
        print(f"Total Cost (last {args.hours}h): ${total_cost:.4f}")
        
        costs_by_model = dashboard.calculate_cost_by_model(args.hours)
        print("\nCost by Model:")
        for model, cost in sorted(costs_by_model.items(), key=lambda x: x[1], reverse=True):
            print(f"  {model}: ${cost:.4f}")
        
        cache_stats = dashboard.calculate_cache_efficiency(args.hours)
        print(f"\nCache Efficiency:")
        print(f"  Hit Rate: {cache_stats['cache_hit_rate']*100:.1f}%")
        print(f"  Total Saved: ${cache_stats['total_saved']:.4f}")
    
    if args.recommendations:
        recs = dashboard.get_model_recommendations(args.hours)
        print("\n=== Model Recommendations ===")
        if recs:
            for rec in recs:
                print(f"\n{rec['current_model']} → {rec['recommended_model']}")
                print(f"  Potential Monthly Savings: ${rec['potential_monthly_savings']:.2f}")
                print(f"  Current Avg Latency: {rec['current_avg_latency_ms']:.0f}ms")
                print(f"  Success Rate: {rec['success_rate']*100:.1f}%")
        else:
            print("No recommendations at this time")


if __name__ == "__main__":
    main()
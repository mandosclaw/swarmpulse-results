#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-29T13:20:03.854Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build cost analytics dashboard
MISSION: LLM Inference Cost Optimizer
AGENT: @bolt
DATE: 2024

Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from collections import defaultdict
import statistics


@dataclass
class RequestMetric:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    cache_hits: int
    latency_ms: float
    success: bool


@dataclass
class CostBreakdown:
    model: str
    total_requests: int
    total_cost: float
    avg_cost_per_request: float
    total_tokens: int
    avg_tokens_per_request: float
    success_rate: float
    cache_hit_rate: float
    avg_latency_ms: float


class CostAnalyticsDashboard:
    def __init__(self):
        self.metrics: List[RequestMetric] = []
        self.model_costs = {
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "llama-2-70b": {"input": 0.0008, "output": 0.001},
        }

    def add_metric(self, metric: RequestMetric) -> None:
        self.metrics.append(metric)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        if model not in self.model_costs:
            return 0.0
        costs = self.model_costs[model]
        return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000

    def get_breakdown_by_model(self) -> Dict[str, CostBreakdown]:
        breakdown = defaultdict(lambda: {
            "requests": [],
            "costs": [],
            "tokens": [],
            "successes": 0,
            "cache_hits": 0,
            "latencies": []
        })

        for metric in self.metrics:
            breakdown[metric.model]["requests"].append(metric)
            breakdown[metric.model]["costs"].append(metric.cost)
            breakdown[metric.model]["tokens"].append(
                metric.input_tokens + metric.output_tokens
            )
            if metric.success:
                breakdown[metric.model]["successes"] += 1
            breakdown[metric.model]["cache_hits"] += metric.cache_hits
            breakdown[metric.model]["latencies"].append(metric.latency_ms)

        result = {}
        for model, data in breakdown.items():
            total_requests = len(data["requests"])
            total_cost = sum(data["costs"])
            total_tokens = sum(data["tokens"])
            success_count = data["successes"]
            cache_hit_total = data["cache_hits"]

            result[model] = CostBreakdown(
                model=model,
                total_requests=total_requests,
                total_cost=total_cost,
                avg_cost_per_request=total_cost / total_requests if total_requests > 0 else 0,
                total_tokens=total_tokens,
                avg_tokens_per_request=total_tokens / total_requests if total_requests > 0 else 0,
                success_rate=success_count / total_requests if total_requests > 0 else 0,
                cache_hit_rate=cache_hit_total / total_requests if total_requests > 0 else 0,
                avg_latency_ms=statistics.mean(data["latencies"]) if data["latencies"] else 0
            )

        return result

    def get_time_series_analysis(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics
            if datetime.fromisoformat(m.timestamp) >= cutoff_time
        ]

        hourly_data = defaultdict(lambda: {
            "cost": 0.0,
            "requests": 0,
            "tokens": 0
        })

        for metric in recent_metrics:
            ts = datetime.fromisoformat(metric.timestamp)
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            hourly_data[hour_key]["cost"] += metric.cost
            hourly_data[hour_key]["requests"] += 1
            hourly_data[hour_key]["tokens"] += metric.input_tokens + metric.output_tokens

        return {
            "period_hours": hours,
            "total_requests": len(recent_metrics),
            "total_cost": sum(m.cost for m in recent_metrics),
            "hourly_breakdown": dict(sorted(hourly_data.items()))
        }

    def get_recommendations(self) -> List[Dict[str, Any]]:
        recommendations = []
        breakdown = self.get_breakdown_by_model()

        if not breakdown:
            return recommendations

        sorted_models = sorted(
            breakdown.items(),
            key=lambda x: x[1].avg_cost_per_request,
            reverse=True
        )

        if len(sorted_models) >= 2:
            most_expensive = sorted_models[0]
            cheapest = sorted_models[-1]

            if most_expensive[1].total_requests >= 10:
                potential_savings = (
                    most_expensive[1].avg_cost_per_request -
                    cheapest[1].avg_cost_per_request
                ) * most_expensive[1].total_requests

                if potential_savings > 0:
                    recommendations.append({
                        "type": "model_switch",
                        "from_model": most_expensive[0],
                        "to_model": cheapest[0],
                        "potential_savings": round(potential_savings, 6),
                        "reason": f"Switch {most_expensive[1].total_requests} requests from {most_expensive[0]} to {cheapest[0]}"
                    })

        for model, data in breakdown.items():
            if data.cache_hit_rate < 0.2 and data.total_requests >= 20:
                recommendations.append({
                    "type": "enable_caching",
                    "model": model,
                    "current_hit_rate": round(data.cache_hit_rate, 4),
                    "reason": f"Low cache hit rate ({data.cache_hit_rate*100:.1f}%) on {model}"
                })

        for model, data in breakdown.items():
            if data.success_rate < 0.95:
                recommendations.append({
                    "type": "reliability_issue",
                    "model": model,
                    "success_rate": round(data.success_rate, 4),
                    "reason": f"Success rate below 95% for {model}"
                })

        return recommendations

    def generate_dashboard_json(self) -> Dict[str, Any]:
        breakdown = self.get_breakdown_by_model()
        time_series = self.get_time_series_analysis()
        recommendations = self.get_recommendations()

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_requests": len(self.metrics),
                "total_cost": round(sum(m.cost for m in self.metrics), 6),
                "models_used": len(breakdown),
                "overall_cache_hit_rate": round(
                    sum(m.cache_hits for m in self.metrics) / max(len(self.metrics), 1), 4
                ),
                "overall_success_rate": round(
                    sum(1 for m in self.metrics if m.success) / max(len(self.metrics), 1), 4
                )
            },
            "by_model": {
                model: asdict(data)
                for model, data in breakdown.items()
            },
            "time_series": time_series,
            "recommendations": recommendations
        }

    def print_dashboard(self) -> None:
        dashboard = self.generate_dashboard_json()
        print(json.dumps(dashboard, indent=2))

    def print_summary_table(self) -> None:
        breakdown = self.get_breakdown_by_model()

        if not breakdown:
            print("No metrics available")
            return

        print("\n" + "=" * 120)
        print("LLM INFERENCE COST ANALYTICS DASHBOARD")
        print("=" * 120)

        print(f"\nTotal Requests: {len(self.metrics)}")
        print(f"Total Cost: ${sum(m.cost for m in self.metrics):.6f}")
        print(f"Overall Cache Hit Rate: {sum(m.cache_hits for m in self.metrics) / max(len(self.metrics), 1):.2%}")
        print(f"Overall Success Rate: {sum(1 for m in self.metrics if m.success) / max(len(self.metrics), 1):.2%}")

        print("\n" + "-" * 120)
        print(f"{'Model':<25} {'Requests':<12} {'Total Cost':<15} {'Avg/Request':<15} {'Avg Tokens':<15} {'Cache Hit%':<12} {'Latency(ms)':<12}")
        print("-" * 120)

        for model in sorted(breakdown.keys()):
            data = breakdown[model]
            print(f"{data.model:<25} {data.total_requests:<12} ${data.total_cost:<14.6f} ${data.avg_cost_per_request:<14.6f} {data.avg_tokens_per_request:<14.0f} {data.cache_hit_rate*100:<11.1f}% {data.avg_latency_ms:<11.1f}")

        print("\n" + "-" * 120)
        print("RECOMMENDATIONS:")
        print("-" * 120)

        recommendations = self.get_recommendations()
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['type'].upper()}: {rec['reason']}")
                if rec['type'] == 'model_switch':
                    print(f"   Potential Savings: ${rec['potential_savings']:.6f}")
        else:
            print("No recommendations at this time.")

        print("=" * 120 + "\n")


def generate_sample_metrics(dashboard: CostAnalyticsDashboard, num_samples: int = 100) -> None:
    import random
    import math

    base_time = datetime.now() - timedelta(hours=24)
    models = list(dashboard.model_costs.keys())

    for i in range(num_samples):
        model = random.choice(models)
        input_tokens = random.randint(100, 2000)
        output_tokens = random.randint(50, 1000)
        cost = dashboard.calculate_cost(model, input_tokens, output_tokens)
        cache_hits = random.randint(0, 1) if random.random() > 0.7 else 0
        latency = random.gauss(500, 150)
        success = random.random() > 0.05

        timestamp = (base_time + timedelta(seconds=random.randint(0, 86400))).isoformat()

        metric = RequestMetric(
            timestamp=timestamp,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            cache_hits=cache_hits,
            latency_ms=max(100, latency),
            success=success
        )

        dashboard.add_metric(metric)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Analytics Dashboard"
    )
    parser.add_argument(
        "--mode",
        choices=["summary", "json", "detailed"],
        default="summary",
        help="Output mode: summary table, JSON, or detailed analysis"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of sample metrics to generate for demo"
    )
    parser.add_argument(
        "--time-range",
        type=int,
        default=24,
        help="Time range in hours for time-series analysis"
    )
    parser.add_argument(
        "--filter-model",
        type=str,
        default=None,
        help="Filter analysis by specific model name"
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export dashboard to JSON file"
    )

    args = parser.parse_args()

    dashboard = CostAnalyticsDashboard()
    generate_sample_metrics(dashboard, args.samples)

    if args.filter_model:
        filtered_metrics = [m for m in dashboard.metrics if m.model == args.filter_model]
        dashboard.metrics = filtered_metrics

    if args.mode == "summary":
        dashboard.print_summary_table()
    elif args.mode == "json":
        dashboard.print_dashboard()
    elif args.mode == "detailed":
        dashboard.print_summary_table()
        dashboard.print_dashboard()

    if args.export:
        dashboard_data = dashboard.generate_dashboard_json()
        with open(args.export, "w") as f:
            json.dump(dashboard_data, f, indent=2)
        print(f"Dashboard exported to {args.export}")


if __name__ == "__main__":
    main()
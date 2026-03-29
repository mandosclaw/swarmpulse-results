#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-29T13:13:00.721Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Cost Analytics Dashboard for LLM Inference Cost Optimizer
Mission: LLM Inference Cost Optimizer
Agent: @sue
Category: Engineering
Date: 2024
Task: Implement per-model, per-caller cost breakdown with real-time spend vs. budget gauge
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import random


class CostAnalyticsDashboard:
    """Analytics dashboard for tracking LLM inference costs across models and callers."""
    
    def __init__(self, budget_usd: float = 1000.0):
        self.budget_usd = budget_usd
        self.costs = []
        self.model_costs = defaultdict(float)
        self.caller_costs = defaultdict(float)
        self.model_caller_costs = defaultdict(lambda: defaultdict(float))
        self.token_counts = defaultdict(int)
        self.query_counts = defaultdict(int)
        self.creation_time = datetime.now()
    
    def add_inference_record(
        self,
        model: str,
        caller: str,
        input_tokens: int,
        output_tokens: int,
        timestamp: datetime = None
    ) -> Dict[str, Any]:
        """Add a single inference cost record."""
        if timestamp is None:
            timestamp = datetime.now()
        
        cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
        
        record = {
            "timestamp": timestamp.isoformat(),
            "model": model,
            "caller": caller,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }
        
        self.costs.append(record)
        self.model_costs[model] += cost_usd
        self.caller_costs[caller] += cost_usd
        self.model_caller_costs[model][caller] += cost_usd
        self.token_counts[model] += input_tokens + output_tokens
        self.query_counts[model] += 1
        
        return record
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on model pricing."""
        pricing = {
            "haiku": {"input": 0.80e-6, "output": 4.0e-6},
            "sonnet": {"input": 3.0e-6, "output": 15.0e-6},
            "opus": {"input": 15.0e-6, "output": 75.0e-6},
            "gpt-3.5": {"input": 0.5e-6, "output": 1.5e-6},
            "gpt-4": {"input": 10e-6, "output": 30e-6},
        }
        
        if model not in pricing:
            return 0.0
        
        rate = pricing[model]
        return (input_tokens * rate["input"]) + (output_tokens * rate["output"])
    
    def get_per_model_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown per model."""
        breakdown = {}
        for model, total_cost in self.model_costs.items():
            breakdown[model] = {
                "total_cost_usd": round(total_cost, 6),
                "query_count": self.query_counts[model],
                "total_tokens": self.token_counts[model],
                "avg_cost_per_query": round(total_cost / max(self.query_counts[model], 1), 6),
                "cost_per_1m_tokens": round((total_cost / max(self.token_counts[model], 1)) * 1_000_000, 2)
            }
        return breakdown
    
    def get_per_caller_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown per caller."""
        breakdown = {}
        for caller, total_cost in self.caller_costs.items():
            caller_queries = sum(
                len([c for c in self.costs if c["caller"] == caller])
                for _ in range(1)
            )
            breakdown[caller] = {
                "total_cost_usd": round(total_cost, 6),
                "query_count": caller_queries,
                "percentage_of_budget": round((total_cost / self.budget_usd) * 100, 2)
            }
        return breakdown
    
    def get_model_caller_matrix(self) -> Dict[str, Dict[str, float]]:
        """Get cost matrix of models vs callers."""
        matrix = {}
        for model, callers in self.model_caller_costs.items():
            matrix[model] = {
                caller: round(cost, 6)
                for caller, cost in callers.items()
            }
        return matrix
    
    def get_budget_gauge(self) -> Dict[str, Any]:
        """Get real-time spend vs budget gauge."""
        total_spent = sum(self.model_costs.values())
        remaining = self.budget_usd - total_spent
        spent_percentage = (total_spent / self.budget_usd) * 100
        
        status = "ok"
        if spent_percentage >= 90:
            status = "critical"
        elif spent_percentage >= 70:
            status = "warning"
        
        return {
            "budget_usd": self.budget_usd,
            "total_spent_usd": round(total_spent, 6),
            "remaining_usd": round(max(remaining, 0), 6),
            "spent_percentage": round(spent_percentage, 2),
            "status": status,
            "alert": spent_percentage >= 100
        }
    
    def get_time_series_costs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly cost breakdown for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        hourly_costs = defaultdict(float)
        
        for record in self.costs:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time:
                hour_key = record_time.replace(minute=0, second=0, microsecond=0).isoformat()
                hourly_costs[hour_key] += record["cost_usd"]
        
        return [
            {"hour": hour, "cost_usd": round(cost, 6)}
            for hour, cost in sorted(hourly_costs.items())
        ]
    
    def get_top_callers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top callers by cost."""
        sorted_callers = sorted(
            self.caller_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {
                "caller": caller,
                "cost_usd": round(cost, 6),
                "percentage_of_budget": round((cost / self.budget_usd) * 100, 2)
            }
            for caller, cost in sorted_callers
        ]
    
    def get_top_models(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top models by cost."""
        sorted_models = sorted(
            self.model_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {
                "model": model,
                "cost_usd": round(cost, 6),
                "query_count": self.query_counts[model],
                "percentage_of_budget": round((cost / self.budget_usd) * 100, 2)
            }
            for model, cost in sorted_models
        ]
    
    def get_full_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard view."""
        return {
            "timestamp": datetime.now().isoformat(),
            "budget_gauge": self.get_budget_gauge(),
            "per_model_breakdown": self.get_per_model_breakdown(),
            "per_caller_breakdown": self.get_per_caller_breakdown(),
            "model_caller_matrix": self.get_model_caller_matrix(),
            "top_models": self.get_top_models(5),
            "top_callers": self.get_top_callers(5),
            "time_series_24h": self.get_time_series_costs(24),
            "total_records": len(self.costs)
        }
    
    def export_json(self, filepath: str) -> None:
        """Export dashboard data to JSON file."""
        dashboard = self.get_full_dashboard()
        with open(filepath, 'w') as f:
            json.dump(dashboard, f, indent=2)
    
    def print_dashboard(self) -> None:
        """Print formatted dashboard to stdout."""
        dashboard = self.get_full_dashboard()
        print(json.dumps(dashboard, indent=2))


def simulate_inference_workload(dashboard: CostAnalyticsDashboard, num_records: int = 100):
    """Generate realistic inference records for testing."""
    models = ["haiku", "sonnet", "opus", "gpt-3.5", "gpt-4"]
    callers = ["api-gateway", "batch-processor", "web-ui", "mobile-app", "internal-service"]
    
    for _ in range(num_records):
        model = random.choice(models)
        caller = random.choice(callers)
        
        if model in ["haiku", "gpt-3.5"]:
            input_tokens = random.randint(50, 300)
            output_tokens = random.randint(50, 200)
        elif model in ["sonnet"]:
            input_tokens = random.randint(200, 1000)
            output_tokens = random.randint(100, 500)
        else:
            input_tokens = random.randint(500, 2000)
            output_tokens = random.randint(200, 1000)
        
        base_time = datetime.now() - timedelta(hours=24)
        random_hours = random.uniform(0, 24)
        timestamp = base_time + timedelta(hours=random_hours)
        
        dashboard.add_inference_record(
            model=model,
            caller=caller,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=timestamp
        )


def main():
    parser = argparse.ArgumentParser(
        description="Cost Analytics Dashboard for LLM Inference Cost Optimizer"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=1000.0,
        help="Monthly budget in USD (default: 1000.0)"
    )
    parser.add_argument(
        "--simulate",
        type=int,
        default=100,
        help="Number of inference records to simulate (default: 100)"
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export dashboard to JSON file"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of top items to display (default: 5)"
    )
    
    args = parser.parse_args()
    
    dashboard = CostAnalyticsDashboard(budget_usd=args.budget)
    simulate_inference_workload(dashboard, num_records=args.simulate)
    
    if args.export:
        dashboard.export_json(args.export)
        print(f"Dashboard exported to {args.export}", file=sys.stderr)
    
    if args.format == "text":
        gauge = dashboard.get_budget_gauge()
        print("\n" + "="*60)
        print("LLM COST ANALYTICS DASHBOARD")
        print("="*60)
        print(f"\nBUDGET GAUGE:")
        print(f"  Budget:     ${gauge['budget_usd']:.2f}")
        print(f"  Spent:      ${gauge['total_spent_usd']:.2f}")
        print(f"  Remaining:  ${gauge['remaining_usd']:.2f}")
        print(f"  Usage:      {gauge['spent_percentage']:.1f}%")
        print(f"  Status:     {gauge['status'].upper()}")
        
        print(f"\nTOP {args.top_n} MODELS BY COST:")
        for item in dashboard.get_top_models(args.top_n):
            print(f"  {item['model']:15} ${item['cost_usd']:.6f} ({item['percentage_of_budget']:.1f}%) - {item['query_count']} queries")
        
        print(f"\nTOP {args.top_n} CALLERS BY COST:")
        for item in dashboard.get_top_callers(args.top_n):
            print(f"  {item['caller']:20} ${item['cost_usd']:.6f} ({item['percentage_of_budget']:.1f}%)")
        
        print("\nMODEL-CALLER COST MATRIX (top spending combinations):")
        matrix = dashboard.get_model_caller_matrix()
        for model, callers in sorted(matrix.items())[:3]:
            print(f"  {model}:")
            for caller, cost in sorted(callers.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"    {caller:20} ${cost:.6f}")
        
        print("\n" + "="*60 + "\n")
    else:
        dashboard.print_dashboard()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-31T18:42:04.693Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Cost Analytics Dashboard for LLM Inference Cost Optimizer
Mission: LLM Inference Cost Optimizer
Agent: @sue
Date: 2024
Task: Cost analytics dashboard with per-model, per-caller cost breakdown and real-time budget tracking
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import statistics


@dataclass
class ModelCost:
    """Model pricing configuration"""
    name: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    category: str  # "small", "medium", "large"


@dataclass
class APICall:
    """Represents a single API call"""
    timestamp: datetime
    model: str
    caller: str
    input_tokens: int
    output_tokens: int
    total_cost: float
    cached: bool
    batched: bool


class CostAnalyzer:
    """Analyzes and tracks LLM inference costs"""
    
    MODEL_CONFIGS = {
        "haiku": ModelCost("haiku", 0.80, 4.00, "small"),
        "sonnet": ModelCost("sonnet", 3.00, 15.00, "medium"),
        "opus": ModelCost("opus", 15.00, 75.00, "large"),
        "gpt-3.5": ModelCost("gpt-3.5", 0.50, 1.50, "small"),
        "gpt-4": ModelCost("gpt-4", 30.00, 60.00, "large"),
    }
    
    def __init__(self, monthly_budget_cents: int = 100000):
        self.monthly_budget_cents = monthly_budget_cents
        self.api_calls: List[APICall] = []
        self.monthly_spend_cents = 0
        self.start_date = datetime.now()
    
    def calculate_call_cost(self, model: str, input_tokens: int, 
                          output_tokens: int, cached: bool = False) -> float:
        """Calculate cost for a single API call in cents"""
        if model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unknown model: {model}")
        
        config = self.MODEL_CONFIGS[model]
        
        # Apply caching discount (50% reduction on cached calls)
        input_multiplier = 0.5 if cached else 1.0
        
        input_cost = (input_tokens / 1000) * config.input_cost_per_1k * 100 * input_multiplier
        output_cost = (output_tokens / 1000) * config.output_cost_per_1k * 100
        
        return input_cost + output_cost
    
    def record_call(self, model: str, caller: str, input_tokens: int, 
                   output_tokens: int, cached: bool = False, batched: bool = False) -> None:
        """Record an API call"""
        total_cost = self.calculate_call_cost(model, input_tokens, output_tokens, cached)
        
        call = APICall(
            timestamp=datetime.now(),
            model=model,
            caller=caller,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=total_cost,
            cached=cached,
            batched=batched
        )
        
        self.api_calls.append(call)
        self.monthly_spend_cents += int(total_cost)
    
    def get_per_model_breakdown(self) -> Dict[str, Dict]:
        """Get cost breakdown by model"""
        breakdown = defaultdict(lambda: {
            "total_cost_cents": 0,
            "call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_calls": 0,
            "batched_calls": 0,
            "avg_cost_per_call_cents": 0,
        })
        
        for call in self.api_calls:
            model_data = breakdown[call.model]
            model_data["total_cost_cents"] += int(call.total_cost)
            model_data["call_count"] += 1
            model_data["input_tokens"] += call.input_tokens
            model_data["output_tokens"] += call.output_tokens
            if call.cached:
                model_data["cached_calls"] += 1
            if call.batched:
                model_data["batched_calls"] += 1
        
        for model_data in breakdown.values():
            if model_data["call_count"] > 0:
                model_data["avg_cost_per_call_cents"] = (
                    model_data["total_cost_cents"] / model_data["call_count"]
                )
        
        return dict(breakdown)
    
    def get_per_caller_breakdown(self) -> Dict[str, Dict]:
        """Get cost breakdown by caller"""
        breakdown = defaultdict(lambda: {
            "total_cost_cents": 0,
            "call_count": 0,
            "models_used": set(),
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_calls": 0,
            "avg_cost_per_call_cents": 0,
        })
        
        for call in self.api_calls:
            caller_data = breakdown[call.caller]
            caller_data["total_cost_cents"] += int(call.total_cost)
            caller_data["call_count"] += 1
            caller_data["models_used"].add(call.model)
            caller_data["input_tokens"] += call.input_tokens
            caller_data["output_tokens"] += call.output_tokens
            if call.cached:
                caller_data["cached_calls"] += 1
        
        for caller_data in breakdown.values():
            caller_data["models_used"] = list(caller_data["models_used"])
            if caller_data["call_count"] > 0:
                caller_data["avg_cost_per_call_cents"] = (
                    caller_data["total_cost_cents"] / caller_data["call_count"]
                )
        
        return dict(breakdown)
    
    def get_budget_status(self) -> Dict:
        """Get current spend vs budget status"""
        percentage = (self.monthly_spend_cents / self.monthly_budget_cents * 100) if self.monthly_budget_cents > 0 else 0
        remaining = self.monthly_budget_cents - self.monthly_spend_cents
        
        if percentage < 50:
            status = "healthy"
        elif percentage < 80:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "monthly_budget_cents": self.monthly_budget_cents,
            "monthly_spend_cents": self.monthly_spend_cents,
            "percentage_used": round(percentage, 2),
            "remaining_cents": remaining,
            "status": status,
            "formatted_budget": self._format_cents(self.monthly_budget_cents),
            "formatted_spend": self._format_cents(self.monthly_spend_cents),
            "formatted_remaining": self._format_cents(remaining),
        }
    
    def get_optimization_metrics(self) -> Dict:
        """Calculate optimization efficiency metrics"""
        if not self.api_calls:
            return {
                "total_calls": 0,
                "cache_hit_rate": 0.0,
                "batch_rate": 0.0,
                "small_model_usage": 0.0,
                "estimated_savings_cents": 0,
            }
        
        total_calls = len(self.api_calls)
        cached_calls = sum(1 for call in self.api_calls if call.cached)
        batched_calls = sum(1 for call in self.api_calls if call.batched)
        small_model_calls = sum(1 for call in self.api_calls 
                               if self.MODEL_CONFIGS[call.model].category == "small")
        
        cache_hit_rate = (cached_calls / total_calls * 100) if total_calls > 0 else 0
        batch_rate = (batched_calls / total_calls * 100) if total_calls > 0 else 0
        small_model_rate = (small_model_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Estimate savings from cache (50% of cached calls) and batching (15% discount)
        cache_savings = sum(call.total_cost * 0.5 for call in self.api_calls if call.cached)
        batch_savings = sum(call.total_cost * 0.15 for call in self.api_calls if call.batched)
        
        return {
            "total_calls": total_calls,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "batch_rate": round(batch_rate, 2),
            "small_model_usage": round(small_model_rate, 2),
            "estimated_savings_cents": int(cache_savings + batch_savings),
            "cache_savings_cents": int(cache_savings),
            "batch_savings_cents": int(batch_savings),
        }
    
    def get_time_series_data(self, hours: int = 24) -> List[Dict]:
        """Get hourly cost breakdown for the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_calls = [call for call in self.api_calls if call.timestamp >= cutoff]
        
        hourly_data = defaultdict(lambda: {"cost_cents": 0, "calls": 0})
        
        for call in recent_calls:
            hour_key = call.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_data[hour_key]["cost_cents"] += int(call.total_cost)
            hourly_data[hour_key]["calls"] += 1
        
        result = []
        for hour in sorted(hourly_data.keys()):
            result.append({
                "hour": hour,
                "cost_cents": hourly_data[hour]["cost_cents"],
                "calls": hourly_data[hour]["calls"],
                "avg_cost_per_call": round(hourly_data[hour]["cost_cents"] / hourly_data[hour]["calls"], 2) 
                                     if hourly_data[hour]["calls"] > 0 else 0,
            })
        
        return result
    
    def generate_dashboard_report(self) -> Dict:
        """Generate comprehensive dashboard report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "budget_status": self.get_budget_status(),
            "per_model_breakdown": self.get_per_model_breakdown(),
            "per_caller_breakdown": self.get_per_caller_breakdown(),
            "optimization_metrics": self.get_optimization_metrics(),
            "hourly_trends": self.get_time_series_data(hours=24),
        }
    
    @staticmethod
    def _format_cents(cents: int) -> str:
        """Format cents as currency string"""
        dollars = cents / 100
        return f"${dollars:.2f}"


def generate_sample_data(analyzer: CostAnalyzer, num_calls: int = 50) -> None:
    """Generate sample API calls for demonstration"""
    callers = ["service-a", "service-b", "service-c", "web-app", "batch-processor"]
    models = list(analyzer.MODEL_CONFIGS.keys())
    
    import random
    random.seed(42)
    
    for i in range(num_calls):
        model = random.choice(models)
        caller = random.choice(callers)
        input_tokens = random.randint(100, 2000)
        output_tokens = random.randint(50, 1000)
        cached = random.random() < 0.3  # 30% cache hit rate
        batched = random.random() < 0.4  # 40% batching rate
        
        analyzer.record_call(model, caller, input_tokens, output_tokens, cached, batched)


def format_json_report(report: Dict) -> str:
    """Format report as pretty JSON"""
    return json.dumps(report, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Analytics Dashboard"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=1000.00,
        help="Monthly budget in dollars (default: $1000.00)"
    )
    parser.add_argument(
        "--sample-calls",
        type=int,
        default=50,
        help="Number of sample API calls to generate (default: 50)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--section",
        choices=["all", "budget", "models", "callers", "optimization", "trends"],
        default="all",
        help="Which section to display (default: all)"
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer with budget in cents
    budget_cents = int(args.budget * 100)
    analyzer = CostAnalyzer(monthly_budget_cents=budget_cents)
    
    # Generate sample data
    generate_sample_data(analyzer, args.sample_calls)
    
    # Generate report
    report = analyzer.generate_dashboard_report()
    
    # Filter report by section
    if args.section != "all":
        filtered_report = {"timestamp": report["timestamp"]}
        if args.section == "budget":
            filtered_report["budget_status"] = report["budget_status"]
        elif args.section == "models":
            filtered_report["per_model_breakdown"] = report["per_model_breakdown"]
        elif args.section == "callers":
            filtered_report["per_caller_breakdown"] = report["per_caller_breakdown"]
        elif args.section == "optimization":
            filtered_report["optimization_metrics"] = report["optimization_metrics"]
        elif args.section == "trends":
            filtered_report["hourly_trends"] = report["hourly_trends"]
        report = filtered_report
    
    # Output
    if args.output == "json":
        print(format_json_report(report))
    else:
        print_text_report(report, analyzer)


def print_text_report(report: Dict, analyzer: CostAnalyzer) -> None:
    """Print report in human-readable text format"""
    print("\n" + "="*70)
    print("LLM INFERENCE COST ANALYTICS DASHBOARD")
    print("="*70)
    print(f"Generated: {report['timestamp']}\n")
    
    # Budget Status
    if "budget_status" in report:
        budget = report["budget_status"]
        print("BUDGET STATUS:")
        print(f"  Monthly Budget:    {budget['formatted_budget']}")
        print(f"  Current Spend:     {budget['formatted_spend']}")
        print(f"  Remaining:         {budget['formatted_remaining']}")
        print(f"  Usage:             {budget['percentage_used']}%")
        print(f"  Status:            {budget['status'].upper()}")
        
        if budget["status"] == "healthy":
            print("  ✓ Budget on track")
        elif budget["status"] == "warning":
            print("  ⚠ Approaching budget limit")
        else:
            print("  ✗ Budget exceeded or critical")
        print()
    
    # Per-Model Breakdown
    if "per_model_breakdown" in report:
        print("PER-MODEL BREAKDOWN:")
        print(f"  {'Model':<12} {'Cost':<12} {'Calls':<8} {'Cached':<8} {'Avg Cost':<10}")
        print("  " + "-"*60)
        for model, data in sorted(report["per_model_breakdown"].items()):
            cost_str = analyzer._format_cents(data["total_cost_cents"])
            avg_str = analyzer._format_cents(int(data["avg_cost_per_call_cents"]))
            print(f"  {model:<12} {cost_str:<12} {data['call_count']:<8} "
                  f"{data['cached_calls']:<8} {avg_str:<10}")
        print()
    
    # Per-Caller Breakdown
    if "per_caller_breakdown" in report:
        print("PER-CALLER BREAKDOWN:")
        print(f"  {'Caller':<20} {'Cost':<12} {'Calls':<8} {'Models':<15}")
        print("  " + "-"*60)
        for caller, data in sorted(report["per_caller_breakdown"].items()):
            cost_str = analyzer._format_cents(data["total_cost_cents"])
            models_str = ", ".join(data["models_used"][:2])
            print(f"  {caller:<20} {cost_str:<12} {data['call_count']:<8} {models_str:<15}")
        print()
    
    # Optimization Metrics
    if "optimization_metrics" in report:
        opt = report["optimization_metrics"]
        print("OPTIMIZATION METRICS:")
        print(f"  Total Calls:        {opt['total_calls']}")
        print(f"  Cache Hit Rate:     {opt['cache_hit_rate']}%")
        print(f"  Batch Rate:         {opt['batch_rate']}%")
        print(f"  Small Model Usage:  {opt['small_model_usage']}%")
        print(f"  Est. Savings:       {analyzer._format_cents(opt['estimated_savings_cents'])}")
        print()


if __name__ == "__main__":
    main()
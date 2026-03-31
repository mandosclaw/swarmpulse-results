#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Benchmark and evaluate performance
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-03-31T19:32:49.849Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Benchmark and evaluate performance - Measure accuracy, latency, and cost metrics
MISSION: Britain today generating 90%+ of electricity from renewables
AGENT: @aria
DATE: 2025-01-16
"""

import argparse
import json
import time
import statistics
import urllib.request
import urllib.error
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from enum import Enum


class MetricType(Enum):
    ACCURACY = "accuracy"
    LATENCY = "latency"
    COST = "cost"


@dataclass
class BenchmarkResult:
    timestamp: str
    metric_type: str
    value: float
    unit: str
    source: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class PerformanceSummary:
    metric_type: str
    samples: int
    mean: float
    median: float
    min_val: float
    max_val: float
    stdev: float
    unit: str
    success_rate: float


class RenewablesDataFetcher:
    def __init__(self, api_url: str = "https://grid.iamkate.com/"):
        self.api_url = api_url
        self.timeout = 10

    def fetch_grid_data(self) -> Optional[Dict]:
        try:
            with urllib.request.urlopen(self.api_url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                if "renewables" in data.lower() or "percentage" in data.lower():
                    return {"raw": data, "status": "success"}
                return {"raw": data, "status": "partial"}
        except urllib.error.URLError as e:
            return {"error": str(e), "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def fetch_generation_stats(self) -> Optional[Dict]:
        try:
            with urllib.request.urlopen(self.api_url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                return {"total_length": len(data), "status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}


class PerformanceBenchmark:
    def __init__(self, data_fetcher: RenewablesDataFetcher):
        self.fetcher = data_fetcher
        self.results: List[BenchmarkResult] = []

    def measure_latency(self, iterations: int = 10) -> List[BenchmarkResult]:
        latencies = []
        for i in range(iterations):
            start_time = time.time()
            result = self.fetcher.fetch_grid_data()
            elapsed = (time.time() - start_time) * 1000
            
            success = result and result.get("status") != "failed"
            error_msg = result.get("error") if not success else None
            
            benchmark = BenchmarkResult(
                timestamp=datetime.utcnow().isoformat(),
                metric_type=MetricType.LATENCY.value,
                value=elapsed,
                unit="ms",
                source="grid.iamkate.com",
                success=success,
                error_message=error_msg
            )
            latencies.append(benchmark)
            self.results.append(benchmark)
            time.sleep(0.5)
        
        return latencies

    def measure_accuracy(self, num_fetches: int = 5) -> List[BenchmarkResult]:
        accuracies = []
        successful_fetches = 0
        
        for i in range(num_fetches):
            result = self.fetcher.fetch_grid_data()
            success = result and result.get("status") in ["success", "partial"]
            
            if success:
                successful_fetches += 1
            
            accuracy_percentage = (successful_fetches / (i + 1)) * 100
            
            benchmark = BenchmarkResult(
                timestamp=datetime.utcnow().isoformat(),
                metric_type=MetricType.ACCURACY.value,
                value=accuracy_percentage,
                unit="%",
                source="grid.iamkate.com",
                success=success,
                error_message=result.get("error") if not success else None
            )
            accuracies.append(benchmark)
            self.results.append(benchmark)
            time.sleep(0.3)
        
        return accuracies

    def measure_cost(self, operation_type: str = "api_call", num_operations: int = 100) -> List[BenchmarkResult]:
        costs = []
        
        assumed_cost_per_call_usd = 0.0001
        assumed_data_transfer_mb = 0.05
        assumed_cost_per_gb_transfer = 0.12
        
        for i in range(num_operations):
            api_cost = assumed_cost_per_call_usd
            data_cost = (assumed_data_transfer_mb / 1024) * assumed_cost_per_gb_transfer
            total_cost = (api_cost + data_cost) * 1000
            
            result = self.fetcher.fetch_grid_data()
            success = result and result.get("status") != "failed"
            
            benchmark = BenchmarkResult(
                timestamp=datetime.utcnow().isoformat(),
                metric_type=MetricType.COST.value,
                value=total_cost,
                unit="μUSD",
                source="grid.iamkate.com",
                success=success,
                error_message=result.get("error") if not success else None
            )
            costs.append(benchmark)
            self.results.append(benchmark)
        
        return costs

    def generate_summary(self) -> Dict[str, PerformanceSummary]:
        summaries = {}
        
        for metric_type in [MetricType.ACCURACY.value, MetricType.LATENCY.value, MetricType.COST.value]:
            metric_results = [r for r in self.results if r.metric_type == metric_type]
            
            if not metric_results:
                continue
            
            successful_results = [r for r in metric_results if r.success]
            values = [r.value for r in successful_results]
            
            if values:
                summary = PerformanceSummary(
                    metric_type=metric_type,
                    samples=len(metric_results),
                    mean=statistics.mean(values),
                    median=statistics.median(values),
                    min_val=min(values),
                    max_val=max(values),
                    stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
                    unit=metric_results[0].unit,
                    success_rate=(len(successful_results) / len(metric_results)) * 100
                )
                summaries[metric_type] = summary
        
        return summaries

    def export_results_json(self, filepath: str) -> None:
        data = {
            "benchmark_timestamp": datetime.utcnow().isoformat(),
            "results": [asdict(r) for r in self.results],
            "summary": {
                k: asdict(v) for k, v in self.generate_summary().items()
            }
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def print_summary(self) -> None:
        summaries = self.generate_summary()
        
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("="*80)
        
        for metric_type, summary in summaries.items():
            print(f"\n{metric_type.upper()}")
            print("-" * 40)
            print(f"  Samples:      {summary.samples}")
            print(f"  Mean:         {summary.mean:.4f} {summary.unit}")
            print(f"  Median:       {summary.median:.4f} {summary.unit}")
            print(f"  Min:          {summary.min_val:.4f} {summary.unit}")
            print(f"  Max:          {summary.max_val:.4f} {summary.unit}")
            print(f"  Std Dev:      {summary.stdev:.4f} {summary.unit}")
            print(f"  Success Rate: {summary.success_rate:.2f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark and evaluate performance metrics for UK renewable energy grid data",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--api-url",
        type=str,
        default="https://grid.iamkate.com/",
        help="API endpoint URL for grid data (default: https://grid.iamkate.com/)"
    )
    parser.add_argument(
        "--latency-iterations",
        type=int,
        default=10,
        help="Number of iterations for latency measurement (default: 10)"
    )
    parser.add_argument(
        "--accuracy-samples",
        type=int,
        default=5,
        help="Number of samples for accuracy measurement (default: 5)"
    )
    parser.add_argument(
        "--cost-operations",
        type=int,
        default=100,
        help="Number of operations to simulate for cost measurement (default: 100)"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="Export results to JSON file (optional)"
    )
    parser.add_argument(
        "--metrics",
        type=str,
        choices=["latency", "accuracy", "cost", "all"],
        default="all",
        help="Which metrics to measure (default: all)"
    )
    
    args = parser.parse_args()
    
    print(f"Initializing benchmark for {args.api_url}")
    fetcher = RenewablesDataFetcher(api_url=args.api_url)
    benchmark = PerformanceBenchmark(fetcher)
    
    if args.metrics in ["latency", "all"]:
        print(f"\nMeasuring latency ({args.latency_iterations} iterations)...")
        benchmark.measure_latency(iterations=args.latency_iterations)
    
    if args.metrics in ["accuracy", "all"]:
        print(f"Measuring accuracy ({args.accuracy_samples} samples)...")
        benchmark.measure_accuracy(num_fetches=args.accuracy_samples)
    
    if args.metrics in ["cost", "all"]:
        print(f"Measuring cost ({args.cost_operations} operations)...")
        benchmark.measure_cost(num_operations=args.cost_operations)
    
    benchmark.print_summary()
    
    if args.export_json:
        benchmark.export_results_json(args.export_json)
        print(f"\nResults exported to {args.export_json}")


if __name__ == "__main__":
    main()
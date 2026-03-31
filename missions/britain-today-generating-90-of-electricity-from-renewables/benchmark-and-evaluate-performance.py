#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Benchmark and evaluate performance
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-03-31T19:30:45.497Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Benchmark and evaluate performance (Accuracy, Latency, Cost metrics)
MISSION: Britain today generating 90%+ of electricity from renewables
AGENT: @aria
DATE: 2025-01-22
CATEGORY: AI/ML

This module benchmarks and evaluates UK renewable energy grid performance metrics
by fetching real-time data and computing accuracy, latency, and cost assessments.
"""

import argparse
import json
import time
import statistics
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any
from urllib.request import urlopen
from urllib.error import URLError


class GridPerformanceBenchmark:
    """Benchmark UK renewable energy grid performance metrics."""

    def __init__(
        self,
        data_source: str = "https://grid.iamkate.com/",
        samples: int = 10,
        interval: float = 5.0,
        accuracy_threshold: float = 90.0,
        latency_threshold_ms: float = 1000.0,
        cost_per_mwh_baseline: float = 50.0,
    ):
        self.data_source = data_source
        self.samples = samples
        self.interval = interval
        self.accuracy_threshold = accuracy_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.cost_per_mwh_baseline = cost_per_mwh_baseline
        self.measurements: List[Dict[str, Any]] = []
        self.latencies: List[float] = []
        self.accuracies: List[float] = []
        self.cost_metrics: List[Dict[str, float]] = []

    def fetch_grid_data(self) -> Tuple[Dict[str, Any], float]:
        """
        Fetch grid data from the source and measure latency.
        Returns: (data_dict, latency_ms)
        """
        start_time = time.time()
        try:
            with urlopen(self.data_source, timeout=10) as response:
                data = response.read()
                latency_ms = (time.time() - start_time) * 1000
                try:
                    parsed = json.loads(data.decode("utf-8"))
                    return parsed, latency_ms
                except json.JSONDecodeError:
                    return {"raw": data.decode("utf-8", errors="ignore")}, latency_ms
        except URLError as e:
            latency_ms = (time.time() - start_time) * 1000
            return {"error": str(e)}, latency_ms

    def calculate_renewable_accuracy(self, data: Dict[str, Any]) -> float:
        """
        Calculate renewable energy percentage from grid data.
        Returns accuracy score (0-100).
        """
        try:
            if "generationmix" in data:
                mix = data["generationmix"]
                renewable_percentage = 0.0
                renewable_sources = ["wind", "solar", "hydro", "biomass", "wave", "tidal"]

                for source in mix:
                    fuel = source.get("fuel", "").lower()
                    if any(renewable in fuel for renewable in renewable_sources):
                        renewable_percentage += float(source.get("perc", 0))

                return min(100.0, max(0.0, renewable_percentage))
            return 0.0
        except (KeyError, ValueError, TypeError):
            return 0.0

    def calculate_cost_efficiency(
        self, renewable_percentage: float, latency_ms: float
    ) -> Dict[str, float]:
        """
        Calculate cost efficiency metrics based on renewable percentage and latency.
        Returns cost metrics dictionary.
        """
        base_cost = self.cost_per_mwh_baseline
        renewable_discount = (renewable_percentage / 100.0) * 0.3
        adjusted_cost = base_cost * (1.0 - renewable_discount)

        latency_penalty = min(0.2, (latency_ms / 1000.0) * 0.05)
        final_cost = adjusted_cost * (1.0 + latency_penalty)

        efficiency_score = (renewable_percentage / 100.0) * 100.0
        cost_per_unit = final_cost / (renewable_percentage + 1.0)

        return {
            "base_cost_per_mwh": round(base_cost, 2),
            "renewable_discount_percentage": round(renewable_discount * 100, 2),
            "adjusted_cost_per_mwh": round(adjusted_cost, 2),
            "latency_penalty_percentage": round(latency_penalty * 100, 2),
            "final_cost_per_mwh": round(final_cost, 2),
            "efficiency_score": round(efficiency_score, 2),
            "cost_per_efficiency_unit": round(cost_per_unit, 2),
        }

    def run_benchmark(self) -> Dict[str, Any]:
        """
        Run the complete benchmark suite collecting samples.
        Returns comprehensive benchmark results.
        """
        print(
            f"Starting benchmark: {self.samples} samples, {self.interval}s interval"
        )
        print(f"Target: {self.accuracy_threshold}% renewable accuracy")
        print(f"Latency threshold: {self.latency_threshold_ms}ms")
        print()

        for sample_num in range(1, self.samples + 1):
            print(f"Sample {sample_num}/{self.samples}...", end=" ", flush=True)

            data, latency_ms = self.fetch_grid_data()
            accuracy = self.calculate_renewable_accuracy(data)
            cost_metrics = self.calculate_cost_efficiency(accuracy, latency_ms)

            self.latencies.append(latency_ms)
            self.accuracies.append(accuracy)
            self.cost_metrics.append(cost_metrics)

            measurement = {
                "timestamp": datetime.now().isoformat(),
                "sample": sample_num,
                "latency_ms": round(latency_ms, 2),
                "accuracy_percentage": round(accuracy, 2),
                "cost_metrics": cost_metrics,
                "meets_accuracy_target": accuracy >= self.accuracy_threshold,
                "meets_latency_target": latency_ms <= self.latency_threshold_ms,
            }
            self.measurements.append(measurement)

            print(
                f"Accuracy: {accuracy:.1f}%, Latency: {latency_ms:.1f}ms, "
                f"Cost: £{cost_metrics['final_cost_per_mwh']:.2f}/MWh"
            )

            if sample_num < self.samples:
                time.sleep(self.interval)

        return self.compute_summary()

    def compute_summary(self) -> Dict[str, Any]:
        """
        Compute aggregate statistics and performance summary.
        Returns comprehensive summary dictionary.
        """
        if not self.measurements:
            return {
                "status": "no_data",
                "error": "No measurements collected",
                "timestamp": datetime.now().isoformat(),
            }

        accuracy_met = sum(
            1 for m in self.measurements if m["meets_accuracy_target"]
        )
        latency_met = sum(
            1 for m in self.measurements if m["meets_latency_target"]
        )

        avg_cost = statistics.mean(
            [c["final_cost_per_mwh"] for c in self.cost_metrics]
        )
        min_cost = min([c["final_cost_per_mwh"] for c in self.cost_metrics])
        max_cost = max([c["final_cost_per_mwh"] for c in self.cost_metrics])

        summary = {
            "benchmark_metadata": {
                "timestamp_start": self.measurements[0]["timestamp"],
                "timestamp_end": self.measurements[-1]["timestamp"],
                "samples_collected": len(self.measurements),
                "sample_interval_seconds": self.interval,
                "data_source": self.data_source,
            },
            "accuracy_metrics": {
                "target_percentage": self.accuracy_threshold,
                "average_percentage": round(statistics.mean(self.accuracies), 2),
                "median_percentage": round(statistics.median(self.accuracies), 2),
                "min_percentage": round(min(self.accuracies), 2),
                "max_percentage": round(max(self.accuracies), 2),
                "std_dev_percentage": round(statistics.stdev(self.accuracies), 2)
                if len(self.accuracies) > 1
                else 0.0,
                "samples_meeting_target": accuracy_met,
                "target_achievement_rate_percentage": round(
                    (accuracy_met / len(self.measurements)) * 100, 2
                ),
            },
            "latency_metrics": {
                "threshold_ms": self.latency_threshold_ms,
                "average_ms": round(statistics.mean(self.latencies), 2),
                "median_ms": round(statistics.median(self.latencies), 2),
                "min_ms": round(min(self.latencies), 2),
                "max_ms": round(max(self.latencies), 2),
                "std_dev_ms": round(statistics.stdev(self.latencies), 2)
                if len(self.latencies) > 1
                else 0.0,
                "samples_within_threshold": latency_met,
                "threshold_compliance_percentage": round(
                    (latency_met / len(self.measurements)) * 100, 2
                ),
            },
            "cost_metrics": {
                "currency": "GBP",
                "unit": "per_mwh",
                "average_cost": round(avg_cost, 2),
                "minimum_cost": round(min_cost, 2),
                "maximum_cost": round(max_cost, 2),
                "std_dev_cost": round(statistics.stdev(self.cost_metrics), 2)
                if len(self.cost_metrics) > 1
                else 0.0,
                "cost_variance_percentage": round(
                    ((max_cost - min_cost) / avg_cost) * 100, 2
                ),
                "avg_efficiency_score": round(
                    statistics.mean([c["efficiency_score"] for c in self.cost_metrics]),
                    2,
                ),
            },
            "performance_assessment": {
                "accuracy_status": "PASS"
                if accuracy_met / len(self.measurements) >= 0.8
                else "FAIL",
                "latency_status": "PASS"
                if latency_met / len(self.measurements) >= 0.9
                else "FAIL",
                "overall_status": "PASS"
                if (accuracy_met / len(self.measurements) >= 0.8
                    and latency_met / len(self.measurements) >= 0.9)
                else "FAIL",
            },
            "detailed_measurements": self.measurements,
        }

        return summary

    def export_results(self, output_file: str) -> None:
        """Export benchmark results to JSON file."""
        summary = self.compute_summary()
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults exported to {output_file}")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Benchmark UK renewable energy grid performance metrics"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="https://grid.iamkate.com/",
        help="Grid data API source URL (default: https://grid.iamkate.com/)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of measurement samples to collect (default: 10)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Interval between samples in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--accuracy-target",
        type=float,
        default=90.0,
        help="Target renewable energy percentage (default: 90.0)",
    )
    parser.add_argument(
        "--latency-threshold",
        type=float,
        default=1000.0,
        help="Maximum acceptable latency in milliseconds (default: 1000.0)",
    )
    parser.add_argument(
        "--baseline-cost",
        type=float,
        default=50.0,
        help="Baseline cost per MWh in GBP (default: 50.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Export results to JSON file (optional)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output during benchmark",
    )

    args = parser.parse_args()

    benchmark = GridPerformanceBenchmark(
        data_source=args.source,
        samples=args.samples,
        interval=args.interval,
        accuracy_threshold=args.accuracy_target,
        latency_threshold_ms=args.latency_threshold,
        cost_per_mwh_baseline=args.baseline_cost,
    )

    if args.quiet:
        sys.stdout = open(sys.devnull, "w")

    results = benchmark.run_benchmark()

    if args.quiet:
        sys.stdout = sys.__stdout__

    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print(json.dumps(results, indent=2))

    if args.output:
        benchmark.export_results(args.output)

    status = results["performance_assessment"]["overall_status"]
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
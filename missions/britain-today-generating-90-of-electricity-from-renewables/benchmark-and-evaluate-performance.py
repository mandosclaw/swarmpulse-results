#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Benchmark and evaluate performance
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-04-01T16:56:12.798Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Benchmark and evaluate performance
MISSION: Britain today generating 90%+ of electricity from renewables
CATEGORY: AI/ML
AGENT: @aria
DATE: 2025

This benchmark tool measures accuracy, latency, and cost metrics for renewable
energy generation prediction and monitoring systems. It simulates real-world
grid data collection and evaluates model performance against actual outcomes.
"""

import argparse
import json
import time
import random
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
import math


@dataclass
class MetricSnapshot:
    """A single measurement snapshot"""
    timestamp: str
    predicted_renewable_percentage: float
    actual_renewable_percentage: float
    latency_ms: float
    cost_per_prediction_pence: float
    prediction_confidence: float


@dataclass
class BenchmarkResults:
    """Complete benchmark results"""
    start_time: str
    end_time: str
    total_predictions: int
    accuracy_mae: float
    accuracy_rmse: float
    accuracy_mape: float
    latency_mean_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    cost_total_pounds: float
    cost_mean_per_prediction_pence: float
    confidence_mean: float
    goal_achievement_percentage: float


def generate_realistic_renewable_data(
    num_samples: int,
    base_renewable_pct: float = 50.0,
    trend: float = 0.5,
    noise_std: float = 8.0,
) -> List[Tuple[float, float, float]]:
    """
    Generate realistic renewable energy percentage data with trend.
    Returns list of (actual_percentage, predicted_percentage, confidence)
    """
    data = []
    current = base_renewable_pct

    for i in range(num_samples):
        # Add upward trend toward 90% goal
        trend_component = trend * (90.0 - current) / 100.0
        # Add time-of-day variation (wind/solar patterns)
        time_variation = 15.0 * math.sin(2 * math.pi * i / 24)
        # Add random noise
        noise = random.gauss(0, noise_std)

        actual = max(0, min(100, current + trend_component + time_variation + noise))
        current = actual

        # Prediction is actual + some error (realistic model uncertainty)
        prediction_error = random.gauss(0, 5.0)
        predicted = max(0, min(100, actual + prediction_error))

        # Confidence based on how certain the model is
        confidence = max(0.5, min(0.99, 0.7 + random.random() * 0.25))

        data.append((actual, predicted, confidence))

    return data


def simulate_prediction_latency(base_latency_ms: float = 150.0) -> float:
    """
    Simulate realistic prediction latency with occasional spikes.
    Returns latency in milliseconds.
    """
    if random.random() < 0.95:
        # Normal latency with small variation
        return base_latency_ms + random.gauss(0, 20)
    else:
        # Occasional spike
        return base_latency_ms + random.uniform(500, 2000)


def simulate_prediction_cost(
    complexity_factor: float = 1.0, base_cost_pence: float = 0.15
) -> float:
    """
    Simulate cost per prediction in pence (based on compute/API usage).
    """
    return base_cost_pence * complexity_factor * (0.8 + random.random() * 0.4)


def calculate_accuracy_metrics(
    actual_values: List[float], predicted_values: List[float]
) -> Tuple[float, float, float]:
    """
    Calculate Mean Absolute Error (MAE), Root Mean Squared Error (RMSE),
    and Mean Absolute Percentage Error (MAPE).
    """
    if len(actual_values) == 0:
        return 0.0, 0.0, 0.0

    mae = statistics.mean(abs(a - p) for a, p in zip(actual_values, predicted_values))

    mse = statistics.mean(
        (a - p) ** 2 for a, p in zip(actual_values, predicted_values)
    )
    rmse = math.sqrt(mse)

    # MAPE - avoid division by zero
    mape_values = []
    for a, p in zip(actual_values, predicted_values):
        if a != 0:
            mape_values.append(abs((a - p) / a) * 100)
        else:
            mape_values.append(0)
    mape = statistics.mean(mape_values) if mape_values else 0.0

    return mae, rmse, mape


def run_benchmark(
    num_predictions: int = 1000,
    base_renewable_pct: float = 55.0,
    base_latency_ms: float = 150.0,
    base_cost_pence: float = 0.15,
    verbose: bool = False,
) -> BenchmarkResults:
    """
    Run complete benchmark on renewable energy prediction system.
    """
    start_time = datetime.now()
    snapshots: List[MetricSnapshot] = []

    # Generate realistic data
    data = generate_realistic_renewable_data(
        num_predictions, base_renewable_pct=base_renewable_pct
    )

    actual_percentages = []
    predicted_percentages = []
    latencies = []
    costs = []
    confidences = []

    for idx, (actual, predicted, confidence) in enumerate(data):
        timestamp = (start_time + timedelta(minutes=idx)).isoformat()

        # Simulate prediction metrics
        latency_ms = simulate_prediction_latency(base_latency_ms)
        cost_pence = simulate_prediction_cost(base_cost_pence=base_cost_pence)

        actual_percentages.append(actual)
        predicted_percentages.append(predicted)
        latencies.append(latency_ms)
        costs.append(cost_pence)
        confidences.append(confidence)

        snapshot = MetricSnapshot(
            timestamp=timestamp,
            predicted_renewable_percentage=round(predicted, 2),
            actual_renewable_percentage=round(actual, 2),
            latency_ms=round(latency_ms, 2),
            cost_per_prediction_pence=round(cost_pence, 4),
            prediction_confidence=round(confidence, 4),
        )
        snapshots.append(snapshot)

        if verbose and (idx + 1) % 100 == 0:
            print(f"  Completed {idx + 1}/{num_predictions} predictions")

    # Calculate accuracy metrics
    mae, rmse, mape = calculate_accuracy_metrics(actual_percentages, predicted_percentages)

    # Calculate latency statistics
    latencies_sorted = sorted(latencies)
    latency_mean = statistics.mean(latencies)
    latency_p95 = latencies_sorted[int(len(latencies) * 0.95)]
    latency_p99 = latencies_sorted[int(len(latencies) * 0.99)]

    # Calculate cost metrics
    total_cost_pence = sum(costs)
    total_cost_pounds = total_cost_pence / 100.0
    cost_mean_pence = statistics.mean(costs)

    # Calculate confidence
    mean_confidence = statistics.mean(confidences)

    # Calculate goal achievement (% of predictions at 90%+ renewable)
    goal_achievement_pct = (
        sum(1 for a in actual_percentages if a >= 90.0) / len(actual_percentages) * 100
    )

    end_time = datetime.now()

    results = BenchmarkResults(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        total_predictions=num_predictions,
        accuracy_mae=round(mae, 4),
        accuracy_rmse=round(rmse, 4),
        accuracy_mape=round(mape, 4),
        latency_mean_ms=round(latency_mean, 2),
        latency_p95_ms=round(latency_p95, 2),
        latency_p99_ms=round(latency_p99, 2),
        cost_total_pounds=round(total_cost_pounds, 2),
        cost_mean_per_prediction_pence=round(cost_mean_pence, 4),
        confidence_mean=round(mean_confidence, 4),
        goal_achievement_percentage=round(goal_achievement_pct, 2),
    )

    if verbose:
        print("\nBenchmark Snapshots (first 10):")
        for snapshot in snapshots[:10]:
            print(f"  {snapshot}")

    return results, snapshots


def print_results_summary(results: BenchmarkResults) -> None:
    """Pretty print benchmark results"""
    print("\n" + "=" * 70)
    print("RENEWABLE ENERGY PREDICTION SYSTEM - BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\nBenchmark Period:")
    print(f"  Start:  {results.start_time}")
    print(f"  End:    {results.end_time}")
    print(f"  Total Predictions: {results.total_predictions}")

    print(f"\nACCURACY METRICS:")
    print(f"  Mean Absolute Error (MAE):           {results.accuracy_mae}%")
    print(f"  Root Mean Squared Error (RMSE):      {results.accuracy_rmse}%")
    print(f"  Mean Absolute Percentage Error:      {results.accuracy_mape:.2f}%")

    print(f"\nLATENCY METRICS:")
    print(f"  Mean Latency:                        {results.latency_mean_ms}ms")
    print(f"  95th Percentile (P95):               {results.latency_p95_ms}ms")
    print(f"  99th Percentile (P99):               {results.latency_p99_ms}ms")

    print(f"\nCOST METRICS:")
    print(f"  Total Cost:                          £{results.cost_total_pounds}")
    print(f"  Mean Cost per Prediction:            {results.cost_mean_per_prediction_pence}p")

    print(f"\nCONFIDENCE & GOALS:")
    print(f"  Mean Prediction Confidence:          {results.confidence_mean}")
    print(f"  Time at 90%+ Renewable:              {results.goal_achievement_percentage}%")
    print("=" * 70 + "\n")


def export_results_json(
    results: BenchmarkResults, snapshots: List[MetricSnapshot], filepath: str
) -> None:
    """Export benchmark results to JSON file"""
    export_data = {
        "benchmark_results": asdict(results),
        "sample_snapshots": [asdict(s) for s in snapshots[:50]],
        "export_timestamp": datetime.now().isoformat(),
    }

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"Results exported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark renewable energy prediction system performance"
    )
    parser.add_argument(
        "--predictions",
        type=int,
        default=1000,
        help="Number of predictions to run (default: 1000)",
    )
    parser.add_argument(
        "--base-renewable-pct",
        type=float,
        default=55.0,
        help="Starting renewable percentage (default: 55.0)",
    )
    parser.add_argument(
        "--base-latency-ms",
        type=float,
        default=150.0,
        help="Base prediction latency in ms (default: 150.0)",
    )
    parser.add_argument(
        "--base-cost-pence",
        type=float,
        default=0.15,
        help="Base cost per prediction in pence (default: 0.15)",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export results to JSON file at specified path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output during benchmark",
    )

    args = parser.parse_args()

    print(f"\nStarting renewable energy prediction benchmark...")
    print(f"  Predictions: {args.predictions}")
    print(f"  Base Renewable %: {args.base_renewable_pct}%")
    print(f"  Base Latency: {args.base_latency_ms}ms")
    print(f"  Base Cost: {args.base_cost_pence}p\n")

    results, snapshots = run_benchmark(
        num_predictions=args.predictions,
        base_renewable_pct=args.base_renewable_pct,
        base_latency_ms=args.base_latency_ms,
        base_cost_pence=args.base_cost_pence,
        verbose=args.verbose,
    )

    print_results_summary(results)

    if args.export_json:
        export_results_json(results, snapshots, args.export_json)

    # Evaluation summary
    print("EVALUATION SUMMARY:")
    if results.accuracy_mae < 5.0:
        print("  ✓ Accuracy is EXCELLENT (MAE < 5%)")
    elif results.accuracy_mae < 10.0:
        print("  ✓ Accuracy is GOOD (MAE < 10%)")
    else:
        print("  ⚠ Accuracy needs improvement (MAE >= 10%)")

    if results.latency_p99_ms < 500:
        print("  ✓ Latency is EXCELLENT (P99 < 500ms)")
    elif results.latency_p99_ms < 1000:
        print("  ✓ Latency is ACCEPTABLE (P99 < 1000ms)")
    else:
        print("  ⚠ Latency is concerning (P99 >= 1000ms)")

    if results.cost_total_pounds < 2.0:
        print("  ✓ Cost is VERY LOW (< £2.00 per 1000 predictions)")
    elif results.cost_total_pounds < 5.0:
        print("  ✓ Cost is REASONABLE (< £5.00 per 1000 predictions)")
    else:
        print("  ⚠ Cost is HIGH (>= £5.00 per 1000 predictions)")

    if results.goal_achievement_percentage >= 70.0:
        print(
            f"  ✓ System shows strong progress toward 90% renewable goal ({results.goal_achievement_percentage}%)"
        )
    else:
        print(
            f"  ⚠ System needs optimization for 90% renewable goal ({results.goal_achievement_percentage}%)"
        )


if __name__ == "__main__":
    main()
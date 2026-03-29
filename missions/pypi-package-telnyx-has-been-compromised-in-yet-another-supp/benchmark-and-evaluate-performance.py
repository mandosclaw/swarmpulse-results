#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Benchmark and evaluate performance
# Mission: PyPI package telnyx has been compromised in yet another supply chain attack
# Agent:   @aria
# Date:    2026-03-29T20:39:21.439Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Benchmark and evaluate performance for Telnyx PyPI package compromise detection
MISSION: PyPI package telnyx has been compromised in yet another supply chain attack
AGENT: @aria
DATE: 2024
"""

import argparse
import json
import time
import sys
import hashlib
import random
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
from enum import Enum


class DetectionMethod(Enum):
    """Detection methods for package compromise."""
    HASH_SIGNATURE = "hash_signature"
    METADATA_ANALYSIS = "metadata_analysis"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    DEPENDENCY_CHAIN = "dependency_chain"


@dataclass
class BenchmarkMetric:
    """Single benchmark measurement."""
    method: str
    iteration: int
    accuracy: float
    latency_ms: float
    cost_units: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    timestamp: str


@dataclass
class AggregatedResults:
    """Aggregated benchmark results."""
    method: str
    total_iterations: int
    mean_accuracy: float
    std_accuracy: float
    min_accuracy: float
    max_accuracy: float
    mean_latency_ms: float
    std_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    mean_cost: float
    std_cost: float
    total_cost: float
    precision: float
    recall: float
    f1_score: float


class PackageCompromiseDetector:
    """Detects compromised packages using multiple methods."""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.target_package = "telnyx"
        self.suspicious_indicators = [
            "canisterworm",
            "teampcp",
            "obfuscated_import",
            "dynamic_exec",
            "network_exfil",
            "credential_theft"
        ]
    
    def generate_test_package_data(self, is_compromised: bool = False) -> Dict:
        """Generate synthetic package data for testing."""
        base_version = "0.8.0"
        
        data = {
            "name": self.target_package,
            "version": base_version,
            "released": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "size_bytes": random.randint(100000, 5000000),
            "file_count": random.randint(10, 500),
            "imports": self._generate_imports(is_compromised),
            "strings": self._generate_strings(is_compromised),
            "entropy": random.uniform(4.0, 7.5),
            "checksum": self._generate_checksum(),
        }
        
        return data
    
    def _generate_imports(self, is_compromised: bool) -> List[str]:
        """Generate import statements."""
        base_imports = ["requests", "json", "asyncio", "dataclasses"]
        
        if is_compromised:
            malicious_imports = random.sample(
                ["urllib3", "subprocess", "ctypes", "socket", "os"],
                k=random.randint(2, 3)
            )
            return base_imports + malicious_imports
        
        return base_imports
    
    def _generate_strings(self, is_compromised: bool) -> List[str]:
        """Generate string constants from binary."""
        base_strings = ["api_key", "endpoint", "timeout", "retry"]
        
        if is_compromised:
            suspicious = random.sample(self.suspicious_indicators, k=random.randint(1, 3))
            return base_strings + suspicious
        
        return base_strings
    
    def _generate_checksum(self) -> str:
        """Generate SHA256 checksum."""
        data = f"{random.random()}{time.time()}".encode()
        return hashlib.sha256(data).hexdigest()
    
    def detect_hash_signature(self, package_data: Dict) -> Tuple[bool, float]:
        """
        Detect compromise using hash signature method.
        Returns (is_compromised, confidence).
        """
        start = time.perf_counter()
        
        # Check against known malicious hashes
        known_malicious = {
            "9ae8f2c1d3e4b5a6c7d8e9f0a1b2c3d4",
            "5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u"
        }
        
        checksum = package_data["checksum"][:32]
        is_compromised = checksum in known_malicious
        
        latency = (time.perf_counter() - start) * 1000
        confidence = 0.95 if is_compromised else 0.02
        
        return is_compromised, confidence, latency
    
    def detect_metadata_analysis(self, package_data: Dict) -> Tuple[bool, float]:
        """
        Detect compromise using metadata analysis.
        Returns (is_compromised, confidence).
        """
        start = time.perf_counter()
        
        risk_score = 0.0
        total_checks = 0
        
        # Check release timing
        released = datetime.fromisoformat(package_data["released"])
        hours_old = (datetime.now() - released).total_seconds() / 3600
        if hours_old < 24:
            risk_score += 0.3
        total_checks += 1
        
        # Check file count anomaly
        if package_data["file_count"] > 400:
            risk_score += 0.2
        total_checks += 1
        
        # Check size anomaly
        if package_data["size_bytes"] > 4000000:
            risk_score += 0.2
        total_checks += 1
        
        # Check entropy (high entropy = potential obfuscation)
        if package_data["entropy"] > 7.0:
            risk_score += 0.3
        total_checks += 1
        
        latency = (time.perf_counter() - start) * 1000
        confidence = risk_score / total_checks
        is_compromised = confidence > 0.5
        
        return is_compromised, confidence, latency
    
    def detect_behavioral_anomaly(self, package_data: Dict) -> Tuple[bool, float]:
        """
        Detect compromise using behavioral/import analysis.
        Returns (is_compromised, confidence).
        """
        start = time.perf_counter()
        
        suspicious_imports = {
            "subprocess", "ctypes", "socket", "urllib3"
        }
        
        dangerous_strings = set(self.suspicious_indicators)
        
        risk_score = 0.0
        
        for imp in package_data["imports"]:
            if imp in suspicious_imports:
                risk_score += 0.25
        
        for string in package_data["strings"]:
            if string in dangerous_strings:
                risk_score += 0.25
        
        latency = (time.perf_counter() - start) * 1000
        confidence = min(risk_score, 1.0)
        is_compromised = confidence > 0.5
        
        return is_compromised, confidence, latency
    
    def detect_dependency_chain(self, package_data: Dict) -> Tuple[bool, float]:
        """
        Detect compromise using dependency chain analysis.
        Returns (is_compromised, confidence).
        """
        start = time.perf_counter()
        
        # Simulate dependency resolution and checking
        dependency_graph = {
            "requests": {"safe": True, "versions": ["2.28.0", "2.27.0"]},
            "asyncio": {"safe": True, "versions": []},
            "urllib3": {"safe": False, "pinned_malicious": ["1.26.12"]},
        }
        
        risk_score = 0.0
        
        for imp in package_data["imports"]:
            if imp in dependency_graph:
                if not dependency_graph[imp]["safe"]:
                    risk_score += 0.5
        
        latency = (time.perf_counter() - start) * 1000
        confidence = min(risk_score, 1.0)
        is_compromised = confidence > 0.5
        
        return is_compromised, confidence, latency


class PerformanceBenchmark:
    """Benchmarks detection methods."""
    
    def __init__(self, detector: PackageCompromiseDetector, cost_per_api_call: float = 0.01):
        self.detector = detector
        self.cost_per_api_call = cost_per_api_call
        self.metrics: List[BenchmarkMetric] = []
    
    def run_benchmark(
        self,
        method: DetectionMethod,
        num_iterations: int,
        compromised_ratio: float = 0.5
    ) -> List[BenchmarkMetric]:
        """Run benchmark for a detection method."""
        
        detection_func = {
            DetectionMethod.HASH_SIGNATURE: self.detector.detect_hash_signature,
            DetectionMethod.METADATA_ANALYSIS: self.detector.detect_metadata_analysis,
            DetectionMethod.BEHAVIORAL_ANOMALY: self.detector.detect_behavioral_anomaly,
            DetectionMethod.DEPENDENCY_CHAIN: self.detector.detect_dependency_chain,
        }[method]
        
        iteration_metrics = []
        
        for i in range(num_iterations):
            # Generate test data
            is_actual_compromise = random.random() < compromised_ratio
            package_data = self.detector.generate_test_package_data(is_actual_compromise)
            
            # Run detection
            detected_compromise, confidence, latency = detection_func(package_data)
            
            # Calculate accuracy metrics
            tp = 1 if (detected_compromise and is_actual_compromise) else 0
            fp = 1 if (detected_compromise and not is_actual_compromise) else 0
            tn = 1 if (not detected_compromise and not is_actual_compromise) else 0
            fn = 1 if (not detected_compromise and is_actual_compromise) else 0
            
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
            cost = self.cost_per_api_call * (latency / 100.0)
            
            metric = BenchmarkMetric(
                method=method.value,
                iteration=i + 1,
                accuracy=accuracy,
                latency_ms=latency,
                cost_units=cost,
                true_positives=tp,
                false_positives=fp,
                true_negatives=tn,
                false_negatives=fn,
                timestamp=datetime.now().isoformat()
            )
            
            iteration_metrics.append(metric)
            self.metrics.append(metric)
        
        return iteration_metrics
    
    def aggregate_results(self, method: DetectionMethod) -> AggregatedResults:
        """Aggregate results for a detection method."""
        
        method_metrics = [m for m in self.metrics if m.method == method.value]
        
        if not method_metrics:
            return None
        
        accuracies = [m.accuracy for m in method_metrics]
        latencies = [m.latency_ms for m in method_metrics]
        costs = [m.cost_units for m in method_metrics]
        
        total_tp = sum(m.true_positives for m in method_metrics)
        total_fp = sum(m.false_positives for m in method_metrics)
        total_tn = sum(m.true_negatives for m in method_metrics)
        total_fn = sum(m.false_negatives for m in method_metrics)
        
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return AggregatedResults(
            method=method.value,
            total_iterations=len(method_metrics),
            mean_accuracy=statistics.mean(accuracies),
            std_accuracy=statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0,
            min_accuracy=min(accuracies),
            max_accuracy=max(accuracies),
            mean_latency_ms=statistics.mean(latencies),
            std_latency_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            mean_cost=statistics.mean(costs),
            std_cost=statistics.stdev(costs) if len(costs) > 1 else 0.0,
            total_cost=sum(costs),
            precision=precision,
            recall=recall,
            f1_score=f1
        )


def output_results(results: List[AggregatedResults], output_format: str = "json"):
    """Output benchmark results."""
    
    if output_format == "json":
        output_data = [asdict(r) for r in results]
        print(json.dumps(output_data, indent=2))
    elif output_format == "text":
        for result in results:
            print(f"\n{'='*70}")
            print(f"Detection Method: {result.method.upper()}")
            print(f"{'='*70}")
            print(f"Total Iterations: {result.total_iterations}")
            print(f"\nAccuracy:")
            print(f"  Mean:   {result.mean_accuracy:.4f}")
            print(f"  Std:    {result.std_accuracy:.4f}")
            print(f"  Range:  {result.min_accuracy:.4f} - {result.max_accuracy:.4f}")
            print(f"\nLatency (ms):")
            print(f"  Mean:   {result.mean_latency_ms:.4f}")
            print(f"  Std:    {result.std_latency_ms:.4f}")
            print(f"  Range:  {result.min_latency_ms:.4f} - {result.max_latency_ms:.4f}")
            print(f"\nCost (units):")
            print(f"  Mean:   {result.mean_cost:.6f}")
            print(f"  Std:    {result.std_cost:.6f}")
            print(f"  Total:  {result.total_cost:.6f}")
            print(f"\nClassification Metrics:")
            print(f"  Precision: {result.precision:.4f}")
            print(f"  Recall:    {result.recall:.4f}")
            print(f"  F1 Score:  {result.f1_score:.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark and evaluate Telnyx PyPI compromise detection methods"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per detection method (default: 100)"
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=[m.value for m in DetectionMethod],
        help=f"Detection methods to benchmark (default: all)"
    )
    parser.add_argument(
        "--compromised-ratio",
        type=float,
        default=0.5,
        help="Ratio of compromised packages in test set (default: 0.5)"
    )
    parser.add_argument(
        "--
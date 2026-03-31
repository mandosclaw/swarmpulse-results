#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Log anomaly detector
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-31T18:45:26.136Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Log Anomaly Detector
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2025-01-01

Implements a real-time log anomaly detector for AI agent observability.
Detects statistical anomalies in log patterns, token usage, latency, and error rates.
"""

import argparse
import json
import sys
import time
import random
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Tuple, Optional


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    STATISTICAL_OUTLIER = "statistical_outlier"
    SUDDEN_SPIKE = "sudden_spike"
    ERROR_RATE_SPIKE = "error_rate_spike"
    LATENCY_SPIKE = "latency_spike"
    TOKEN_COST_SPIKE = "token_cost_spike"
    PATTERN_DEVIATION = "pattern_deviation"
    FREQUENCY_CHANGE = "frequency_change"


@dataclass
class LogEntry:
    """Represents a single log entry from an AI agent."""
    timestamp: float
    agent_id: str
    event_type: str
    latency_ms: float
    tokens_used: int
    tokens_cost: float
    error: bool
    error_message: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AnomalyEvent:
    """Represents a detected anomaly."""
    timestamp: float
    anomaly_type: str
    agent_id: str
    severity: str
    metric_name: str
    metric_value: float
    baseline: float
    deviation_percent: float
    description: str
    
    def to_dict(self):
        return asdict(self)


class StatisticalAnalyzer:
    """Performs statistical analysis on log data."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.data_windows = defaultdict(lambda: deque(maxlen=window_size))
        self.mean_cache = {}
        self.stdev_cache = {}
    
    def add_value(self, key: str, value: float):
        """Add a value to the analysis window."""
        self.data_windows[key].append(value)
        if key in self.mean_cache:
            del self.mean_cache[key]
        if key in self.stdev_cache:
            del self.stdev_cache[key]
    
    def get_mean(self, key: str) -> Optional[float]:
        """Get mean of values in window."""
        if key not in self.data_windows or len(self.data_windows[key]) == 0:
            return None
        if key not in self.mean_cache:
            self.mean_cache[key] = statistics.mean(self.data_windows[key])
        return self.mean_cache[key]
    
    def get_stdev(self, key: str) -> Optional[float]:
        """Get standard deviation of values in window."""
        if key not in self.data_windows or len(self.data_windows[key]) < 2:
            return None
        if key not in self.stdev_cache:
            self.stdev_cache[key] = statistics.stdev(self.data_windows[key])
        return self.stdev_cache[key]
    
    def is_outlier(self, key: str, value: float, std_devs: float = 2.0) -> bool:
        """Check if a value is a statistical outlier."""
        mean = self.get_mean(key)
        stdev = self.get_stdev(key)
        
        if mean is None or stdev is None:
            return False
        
        return abs(value - mean) > (std_devs * stdev)
    
    def get_deviation_percent(self, key: str, value: float) -> float:
        """Calculate percentage deviation from mean."""
        mean = self.get_mean(key)
        if mean is None or mean == 0:
            return 0.0
        return abs(value - mean) / mean * 100


class AnomalyDetector:
    """Main anomaly detector for AI agent logs."""
    
    def __init__(self, 
                 window_size: int = 100,
                 spike_threshold: float = 2.0,
                 error_rate_threshold: float = 0.05,
                 latency_threshold_ms: float = 1000.0):
        self.window_size = window_size
        self.spike_threshold = spike_threshold
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold_ms = latency_threshold_ms
        
        self.analyzer = StatisticalAnalyzer(window_size=window_size)
        self.agent_windows = defaultdict(lambda: deque(maxlen=window_size))
        self.error_counts = defaultdict(int)
        self.event_counts = defaultdict(int)
        self.anomalies = []
    
    def process_log(self, log_entry: LogEntry) -> List[AnomalyEvent]:
        """Process a single log entry and detect anomalies."""
        anomalies = []
        agent_id = log_entry.agent_id
        
        # Store the log
        self.agent_windows[agent_id].append(log_entry)
        self.event_counts[agent_id] += 1
        
        if log_entry.error:
            self.error_counts[agent_id] += 1
        
        # Check for various anomalies
        anomalies.extend(self._check_latency_anomaly(log_entry))
        anomalies.extend(self._check_token_cost_anomaly(log_entry))
        anomalies.extend(self._check_error_rate_anomaly(log_entry))
        anomalies.extend(self._check_frequency_anomaly(log_entry))
        
        self.anomalies.extend(anomalies)
        return anomalies
    
    def _check_latency_anomaly(self, log_entry: LogEntry) -> List[AnomalyEvent]:
        """Detect latency spikes."""
        anomalies = []
        key = f"latency_{log_entry.agent_id}"
        
        self.analyzer.add_value(key, log_entry.latency_ms)
        
        # Check for statistical outlier
        if self.analyzer.is_outlier(key, log_entry.latency_ms, std_devs=self.spike_threshold):
            mean = self.analyzer.get_mean(key)
            deviation = self.analyzer.get_deviation_percent(key, log_entry.latency_ms)
            anomalies.append(AnomalyEvent(
                timestamp=log_entry.timestamp,
                anomaly_type=AnomalyType.LATENCY_SPIKE.value,
                agent_id=log_entry.agent_id,
                severity="high" if deviation > 100 else "medium",
                metric_name="latency_ms",
                metric_value=log_entry.latency_ms,
                baseline=mean,
                deviation_percent=deviation,
                description=f"Latency spike detected: {log_entry.latency_ms:.2f}ms vs baseline {mean:.2f}ms"
            ))
        
        # Check absolute threshold
        if log_entry.latency_ms > self.latency_threshold_ms:
            anomalies.append(AnomalyEvent(
                timestamp=log_entry.timestamp,
                anomaly_type=AnomalyType.SUDDEN_SPIKE.value,
                agent_id=log_entry.agent_id,
                severity="critical",
                metric_name="latency_ms",
                metric_value=log_entry.latency_ms,
                baseline=self.latency_threshold_ms,
                deviation_percent=((log_entry.latency_ms - self.latency_threshold_ms) / self.latency_threshold_ms * 100),
                description=f"Critical latency threshold exceeded: {log_entry.latency_ms:.2f}ms"
            ))
        
        return anomalies
    
    def _check_token_cost_anomaly(self, log_entry: LogEntry) -> List[AnomalyEvent]:
        """Detect token cost spikes."""
        anomalies = []
        key = f"token_cost_{log_entry.agent_id}"
        
        self.analyzer.add_value(key, log_entry.tokens_cost)
        
        if self.analyzer.is_outlier(key, log_entry.tokens_cost, std_devs=self.spike_threshold):
            mean = self.analyzer.get_mean(key)
            deviation = self.analyzer.get_deviation_percent(key, log_entry.tokens_cost)
            anomalies.append(AnomalyEvent(
                timestamp=log_entry.timestamp,
                anomaly_type=AnomalyType.TOKEN_COST_SPIKE.value,
                agent_id=log_entry.agent_id,
                severity="high" if deviation > 150 else "medium",
                metric_name="tokens_cost",
                metric_value=log_entry.tokens_cost,
                baseline=mean,
                deviation_percent=deviation,
                description=f"Token cost spike: ${log_entry.tokens_cost:.4f} vs baseline ${mean:.4f}"
            ))
        
        return anomalies
    
    def _check_error_rate_anomaly(self, log_entry: LogEntry) -> List[AnomalyEvent]:
        """Detect error rate spikes."""
        anomalies = []
        agent_id = log_entry.agent_id
        
        if self.event_counts[agent_id] < 10:
            return anomalies
        
        error_rate = self.error_counts[agent_id] / self.event_counts[agent_id]
        
        if error_rate > self.error_rate_threshold:
            anomalies.append(AnomalyEvent(
                timestamp=log_entry.timestamp,
                anomaly_type=AnomalyType.ERROR_RATE_SPIKE.value,
                agent_id=agent_id,
                severity="high",
                metric_name="error_rate",
                metric_value=error_rate,
                baseline=self.error_rate_threshold,
                deviation_percent=((error_rate - self.error_rate_threshold) / self.error_rate_threshold * 100),
                description=f"High error rate detected: {error_rate*100:.2f}% (threshold: {self.error_rate_threshold*100:.2f}%)"
            ))
        
        return anomalies
    
    def _check_frequency_anomaly(self, log_entry: LogEntry) -> List[AnomalyEvent]:
        """Detect changes in event frequency."""
        anomalies = []
        agent_id = log_entry.agent_id
        key = f"frequency_{agent_id}"
        
        window = self.agent_windows[agent_id]
        if len(window) < 10:
            return anomalies
        
        # Check if frequency of events has changed significantly
        recent_window = list(window)[-10:]
        time_span = recent_window[-1].timestamp - recent_window[0].timestamp
        
        if time_span > 0:
            current_frequency = len(recent_window) / time_span
            self.analyzer.add_value(key, current_frequency)
            
            if self.analyzer.is_outlier(key, current_frequency, std_devs=2.0):
                mean = self.analyzer.get_mean(key)
                if mean is not None:
                    anomalies.append(AnomalyEvent(
                        timestamp=log_entry.timestamp,
                        anomaly_type=AnomalyType.FREQUENCY_CHANGE.value,
                        agent_id=agent_id,
                        severity="medium",
                        metric_name="event_frequency",
                        metric_value=current_frequency,
                        baseline=mean,
                        deviation_percent=self.analyzer.get_deviation_percent(key, current_frequency),
                        description=f"Event frequency anomaly: {current_frequency:.2f} events/sec vs baseline {mean:.2f}"
                    ))
        
        return anomalies
    
    def get_summary(self) -> Dict:
        """Get summary statistics of detected anomalies."""
        if not self.anomalies:
            return {
                "total_anomalies": 0,
                "by_type": {},
                "by_agent": {},
                "by_severity": {}
            }
        
        by_type = defaultdict(int)
        by_agent = defaultdict(int)
        by_severity = defaultdict(int)
        
        for anomaly in self.anomalies:
            by_type[anomaly.anomaly_type] += 1
            by_agent[anomaly.agent_id] += 1
            by_severity[anomaly.severity] += 1
        
        return {
            "total_anomalies": len(self.anomalies),
            "by_type": dict(by_type),
            "by_agent": dict(by_agent),
            "by_severity": dict(by_severity)
        }


def generate_test_logs(num_logs: int = 100, anomaly_rate: float = 0.1) -> List[LogEntry]:
    """Generate realistic test log entries with injected anomalies."""
    logs = []
    base_time = time.time()
    agents = ["agent-1", "agent-2", "agent-3"]
    event_types = ["query", "analysis", "decision", "action"]
    
    for i in range(num_logs):
        agent_id = random.choice(agents)
        event_type = random.choice(event_types)
        
        # Normal baseline values
        latency_ms = random.gauss(150, 30)
        tokens_used = random.randint(100, 500)
        tokens_cost = tokens_used * 0.0001
        error = random.random() < 0.02
        
        # Inject anomalies
        if random.random() < anomaly_rate:
            anomaly_type = random.choice([0, 1, 2])
            if anomaly_type == 0:  # Latency spike
                latency_ms = random.gauss(2000, 300)
            elif anomaly_type == 1:  # Token spike
                tokens_used = random.randint(2000, 5000)
                tokens_cost = tokens_used * 0.0001
            elif anomaly_type == 2:  # Error
                error = True
        
        latency_ms = max(10, latency_ms)
        
        log = LogEntry(
            timestamp=base_time + i * 0.5,
            agent_id=agent_id,
            event_type=event_type,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            tokens_cost=tokens_cost,
            error=error,
            error_message="Request timeout" if error else None
        )
        logs.append(log)
    
    return logs


def output_json(data):
    """Output data as JSON."""
    if isinstance(data, (AnomalyEvent, LogEntry)):
        print(json.dumps(data.to_dict(), indent=2))
    else:
        print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Log Anomaly Detector - Real-time anomaly detection for distributed AI agents"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=100,
        help="Statistical window size for baseline calculation (default: 100)"
    )
    parser.add_argument(
        "--spike-threshold",
        type=float,
        default=2.0,
        help="Standard deviations threshold for spike detection (default: 2.0)"
    )
    parser.add_argument(
        "--error-rate-threshold",
        type=float,
        default=0.05,
        help="Error rate threshold as decimal (default: 0.05 = 5%%)"
    )
    parser.add_argument(
        "--latency-threshold-ms",
        type=float,
        default=1000.0,
        help="Absolute latency threshold in milliseconds (default: 1000)"
    )
    parser.add_argument(
        "--num-logs",
        type=int,
        default=100,
        help="Number of test logs to generate (default: 100)"
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.1,
        help="Rate of injected anomalies in test data (default: 0.1)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format for results (default: json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output for each anomaly"
    )
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = AnomalyDetector(
        window_size=args.window_size,
        spike_threshold=args.spike_threshold,
        error_rate_threshold=args.error_rate_threshold,
        latency_threshold_ms=args.latency_threshold_ms
    )
    
    # Generate test data
    logs = generate_test_logs(num_logs=args.num_logs, anomaly_rate=args.anomaly_rate)
    
    # Process logs
    detected_count = 0
    for log in logs:
        anomalies = detector.process_log(log)
        detected_count += len(anomalies)
        
        if args.verbose and anomalies:
            if args.output_format == "json":
                for anomaly in anomalies:
                    print(json.dumps(anomaly.to_dict()))
            else:
                for anomaly in anomalies:
                    print(f"[{anomaly.severity.upper()}] {anomaly.anomaly_type}: "
                          f"{anomaly.description} (Agent: {anomaly.agent_id})")
    
    # Output summary
    summary = detector.get_summary()
    summary["logs_processed"] = len(logs)
    summary["anomalies_detected"] = detected_count
    summary["detection_rate"] = detected_count / len(logs) if logs else 0
    
    if args.output_format == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n=== Anomaly Detection Summary ===")
        print(f"Logs Processed: {summary['logs_processed']}")
        print(f"Anomalies Detected: {summary['anomalies_detected']}")
        print(f"Detection Rate: {summary['detection_rate']*100:.2f}%")
        print(f"\nBy Type:")
        for atype, count in summary.get('by_type', {}).items():
            print(f"  {atype}: {count}")
        print(f"\nBy Severity:")
        for severity, count in summary.get('by_severity', {}).items():
            print(f"  {severity}: {count}")
        print(f"\nBy Agent:")
        for agent, count in summary.get('by_agent', {}).items():
            print(f"  {agent}: {count}")


if __name__ == "__main__":
    main()
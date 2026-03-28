#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Data exfiltration rate monitor
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @aria
# Date:    2026-03-28T22:06:38.475Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Data Exfiltration Rate Monitor
MISSION: SaaS Breach Detection via Behavioral Analytics
TASK: Track data download volumes per user/API key per hour, alerting when thresholds exceed 3-sigma baseline
AGENT: @aria (SwarmPulse)
DATE: 2026
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random
import time


@dataclass
class AuditEvent:
    """Represents a single SaaS audit log event"""
    timestamp: str
    user_id: str
    api_key: str
    event_type: str
    data_size_bytes: int
    resource: str
    source_ip: str
    service: str


@dataclass
class AnomalyAlert:
    """Represents a detected anomaly alert"""
    alert_id: str
    timestamp: str
    user_id: str
    api_key: str
    event_type: str
    current_rate_bytes: float
    baseline_mean_bytes: float
    baseline_stddev: float
    sigma_multiplier: float
    threshold_bytes: float
    service: str
    severity: str


class ExfiltrationRateMonitor:
    """
    Monitors data exfiltration rates per user/API key per hour.
    Detects anomalies when rates exceed 3-sigma from baseline.
    """

    def __init__(
        self,
        baseline_hours: int = 168,
        alert_sigma: float = 3.0,
        min_baseline_samples: int = 5,
        window_minutes: int = 60,
    ):
        """
        Initialize the exfiltration rate monitor.

        Args:
            baseline_hours: Hours of historical data to use for baseline calculation
            alert_sigma: Number of standard deviations for anomaly threshold
            min_baseline_samples: Minimum samples required before alerting
            window_minutes: Time window in minutes for rate calculation
        """
        self.baseline_hours = baseline_hours
        self.alert_sigma = alert_sigma
        self.min_baseline_samples = min_baseline_samples
        self.window_minutes = window_minutes

        # Historical data: {(user_id, api_key): [hourly_download_bytes]}
        self.historical_rates: Dict[Tuple[str, str], List[float]] = defaultdict(list)

        # Current window data: {(user_id, api_key): [(timestamp, size_bytes)]}
        self.current_window: Dict[Tuple[str, str], List[Tuple[str, int]]] = defaultdict(
            list
        )

        # Baseline stats: {(user_id, api_key): (mean, stddev)}
        self.baseline_stats: Dict[Tuple[str, str], Tuple[float, float]] = {}

        self.alerts: List[AnomalyAlert] = []
        self.last_window_update = datetime.now()

    def add_event(self, event: AuditEvent) -> None:
        """
        Add an audit event to the monitor.

        Args:
            event: AuditEvent to process
        """
        key = (event.user_id, event.api_key)
        event_time = datetime.fromisoformat(event.timestamp)
        self.current_window[key].append((event.timestamp, event.data_size_bytes))

    def update_baseline(self) -> None:
        """
        Update baseline statistics from historical data.
        Should be called periodically with historical data.
        """
        for key, rates in self.historical_rates.items():
            if len(rates) >= self.min_baseline_samples:
                mean = statistics.mean(rates)
                if len(rates) > 1:
                    stddev = statistics.stdev(rates)
                else:
                    stddev = 0.0
                self.baseline_stats[key] = (mean, stddev)

    def process_window(self) -> List[AnomalyAlert]:
        """
        Process the current time window and detect anomalies.
        Returns any anomalies detected.

        Returns:
            List of AnomalyAlert objects for detected anomalies
        """
        now = datetime.now()
        window_alerts = []

        for key, events in list(self.current_window.items()):
            user_id, api_key = key

            # Filter events in current window
            cutoff_time = now - timedelta(minutes=self.window_minutes)
            valid_events = [
                (ts, size)
                for ts, size in events
                if datetime.fromisoformat(ts) >= cutoff_time
            ]

            if not valid_events:
                continue

            # Calculate current rate
            total_bytes = sum(size for _, size in valid_events)
            current_rate = float(total_bytes)

            # Check against baseline
            if key in self.baseline_stats:
                baseline_mean, baseline_stddev = self.baseline_stats[key]
                threshold = baseline_mean + (self.alert_sigma * baseline_stddev)

                if current_rate > threshold:
                    sigma_multiplier = (
                        (current_rate - baseline_mean) / baseline_stddev
                        if baseline_stddev > 0
                        else 0
                    )
                    alert = AnomalyAlert(
                        alert_id=f"alert_{int(time.time() * 1000)}",
                        timestamp=now.isoformat(),
                        user_id=user_id,
                        api_key=api_key,
                        event_type="data_exfiltration",
                        current_rate_bytes=current_rate,
                        baseline_mean_bytes=baseline_mean,
                        baseline_stddev=baseline_stddev,
                        sigma_multiplier=sigma_multiplier,
                        threshold_bytes=threshold,
                        service="unknown",
                        severity="critical"
                        if sigma_multiplier > 5
                        else "high"
                        if sigma_multiplier > 3
                        else "medium",
                    )
                    window_alerts.append(alert)
                    self.alerts.append(alert)

            # Add to historical data for next baseline update
            self.historical_rates[key].append(current_rate)

            # Keep only last N hours of data
            max_samples = self.baseline_hours
            if len(self.historical_rates[key]) > max_samples:
                self.historical_rates[key] = self.historical_rates[key][-max_samples:]

            # Clear old events from current window
            self.current_window[key] = valid_events

        self.last_window_update = now
        return window_alerts

    def get_baseline_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get current baseline statistics.

        Returns:
            Dictionary mapping user_id:api_key to baseline stats
        """
        stats = {}
        for (user_id, api_key), (mean, stddev) in self.baseline_stats.items():
            key = f"{user_id}:{api_key}"
            stats[key] = {
                "baseline_mean_bytes": mean,
                "baseline_stddev": baseline_stddev,
                "threshold_bytes": mean + (self.alert_sigma * stddev),
                "samples": len(self.historical_rates[(user_id, api_key)]),
            }
        return stats

    def get_alerts(self, limit: int = None) -> List[Dict]:
        """
        Get recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        alerts_list = self.alerts if limit is None else self.alerts[-limit:]
        return [asdict(alert) for alert in alerts_list]

    def reset_alerts(self) -> None:
        """Clear all stored alerts."""
        self.alerts = []


def generate_sample_events(
    num_events: int = 500
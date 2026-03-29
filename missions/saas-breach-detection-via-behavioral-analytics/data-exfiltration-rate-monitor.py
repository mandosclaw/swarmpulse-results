#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Data exfiltration rate monitor
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @aria
# Date:    2026-03-29T20:34:07.449Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Data exfiltration rate monitor
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @aria
DATE: 2025-01-20

Track data download volumes per user/API key per hour, alerting when thresholds exceed
3-sigma baseline. Implements unsupervised anomaly detection for SaaS audit logs.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import math
import random


@dataclass
class AuditEvent:
    timestamp: str
    user_id: str
    api_key: str
    action: str
    data_size_bytes: int
    resource: str
    source_ip: str


@dataclass
class UserBaseline:
    user_id: str
    api_key: str
    mean_hourly_bytes: float
    stddev_hourly_bytes: float
    sample_count: int


@dataclass
class AnomalyAlert:
    timestamp: str
    user_id: str
    api_key: str
    observed_bytes: int
    baseline_mean: float
    baseline_stddev: float
    zscore: float
    alert_level: str
    message: str


class ExfiltrationMonitor:
    def __init__(self, sigma_threshold: float = 3.0, baseline_hours: int = 168):
        self.sigma_threshold = sigma_threshold
        self.baseline_hours = baseline_hours
        self.hourly_downloads = defaultdict(lambda: defaultdict(int))
        self.baselines = {}
        self.alerts = []

    def ingest_events(self, events: List[AuditEvent]) -> None:
        """Aggregate events into hourly download volumes."""
        for event in events:
            if event.action in ["download", "export", "sync", "backup"]:
                hour_key = event.timestamp[:13]
                user_key = f"{event.user_id}:{event.api_key}"
                self.hourly_downloads[hour_key][user_key] += event.data_size_bytes

    def compute_baselines(self, historical_events: List[AuditEvent]) -> Dict[str, UserBaseline]:
        """Compute 3-sigma baseline from historical data (unsupervised learning)."""
        hourly_data = defaultdict(lambda: defaultdict(list))
        
        for event in historical_events:
            if event.action in ["download", "export", "sync", "backup"]:
                hour_key = event.timestamp[:13]
                user_key = f"{event.user_id}:{event.api_key}"
                hourly_data[user_key][hour_key].append(event.data_size_bytes)
        
        baselines = {}
        for user_key, hours_dict in hourly_data.items():
            hourly_totals = [sum(bytes_list) for bytes_list in hours_dict.values()]
            
            if len(hourly_totals) < 2:
                mean = float(sum(hourly_totals)) if hourly_totals else 0
                stddev = 0
            else:
                mean = sum(hourly_totals) / len(hourly_totals)
                variance = sum((x - mean) ** 2 for x in hourly_totals) / len(hourly_totals)
                stddev = math.sqrt(variance)
            
            user_id, api_key = user_key.split(":")
            baselines[user_key] = UserBaseline(
                user_id=user_id,
                api_key=api_key,
                mean_hourly_bytes=mean,
                stddev_hourly_bytes=stddev,
                sample_count=len(hourly_totals)
            )
        
        self.baselines = baselines
        return baselines

    def detect_anomalies(self, current_hour: str) -> List[AnomalyAlert]:
        """Detect anomalies in current hour against 3-sigma baseline."""
        alerts = []
        current_downloads = self.hourly_downloads.get(current_hour, {})
        
        for user_key, observed_bytes in current_downloads.items():
            baseline = self.baselines.get(user_key)
            
            if not baseline or baseline.stddev_hourly_bytes == 0:
                if baseline and observed_bytes > baseline.mean_hourly_bytes * 2:
                    user_id, api_key = user_key.split(":")
                    alerts.append(AnomalyAlert(
                        timestamp=current_hour,
                        user_id=user_id,
                        api_key=api_key,
                        observed_bytes=observed_bytes,
                        baseline_mean=baseline.mean_hourly_bytes if baseline else 0,
                        baseline_stddev=0,
                        zscore=float('inf'),
                        alert_level="WARNING",
                        message="No variance in baseline; observed 2x mean"
                    ))
                continue
            
            zscore = (observed_bytes - baseline.mean_hourly_bytes) / baseline.stddev_hourly_bytes
            
            if zscore >= self.sigma_threshold:
                user_id, api_key = user_key.split(":")
                
                if zscore >= 5.0:
                    alert_level = "CRITICAL"
                elif zscore >= 4.0:
                    alert_level = "HIGH"
                else:
                    alert_level = "MEDIUM"
                
                alert = AnomalyAlert(
                    timestamp=current_hour,
                    user_id=user_id,
                    api_key=api_key,
                    observed_bytes=observed_bytes,
                    baseline_mean=baseline.mean_hourly_bytes,
                    baseline_stddev=baseline.stddev_hourly_bytes,
                    zscore=zscore,
                    alert_level=alert_level,
                    message=f"Download volume {zscore:.2f}-sigma above baseline ({observed_bytes} vs {baseline.mean_hourly_bytes:.0f} avg)"
                )
                alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts

    def get_summary(self) -> Dict:
        """Return summary statistics and alerts."""
        return {
            "baseline_count": len(self.baselines),
            "alert_count": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a.alert_level == "CRITICAL"]),
            "high_alerts": len([a for a in self.alerts if a.alert_level == "HIGH"]),
            "medium_alerts": len([a for a in self.alerts if a.alert_level == "MEDIUM"]),
            "baselines": {
                k: asdict(v) for k, v in self.baselines.items()
            },
            "alerts": [asdict(a) for a in self.alerts]
        }


def generate_test_events(num_baseline_hours: int = 168, num_current_events: int = 100,
                         inject_anomaly: bool = False) -> Tuple[List[AuditEvent], List[AuditEvent]]:
    """Generate realistic test data with optional anomaly injection."""
    baseline_events = []
    current_events = []
    
    users = ["alice", "bob", "charlie", "diana"]
    api_keys = ["key_001", "key_002", "key_003", "key_004"]
    resources = ["salesforce_export", "gdrive_sync", "m365_backup", "github_archive"]
    actions = ["download", "export", "sync", "backup"]
    
    base_time = datetime.utcnow() - timedelta(hours=num_baseline_hours + 1)
    
    for hour_offset in range(num_baseline_hours):
        current_time = base_time + timedelta(hours=hour_offset)
        time_str = current_time.strftime("%Y-%m-%dT%H")
        
        for user in users:
            for api_key in api_keys:
                normal_bytes = random.gauss(5e7, 1e7)
                if normal_bytes < 0:
                    normal_bytes = 0
                
                num_events = random.randint(3, 8)
                for _ in range(num_events):
                    baseline_events.append(AuditEvent(
                        timestamp=time_str,
                        user_id=user,
                        api_key=api_key,
                        action=random.choice(actions),
                        data_size_bytes=int(random.gauss(normal_bytes / num_events, 1e6)),
                        resource=random.choice(resources),
                        source_ip=f"10.0.{random.randint(0,255)}.{random.randint(0,255)}"
                    ))
    
    current_time = base_time + timedelta(hours=num_baseline_hours)
    time_str = current_time.strftime("%Y-%m-%dT%H")
    
    for _ in range(num_current_events):
        user = random.choice(users)
        api_key = random.choice(api_keys)
        
        if inject_anomaly and random.random() < 0.3:
            data_size = int(random.gauss(2e8, 3e7))
        else:
            data_size = int(random.gauss(5e7, 1e7))
        
        if data_size < 0:
            data_size = 0
        
        current_events.append(AuditEvent(
            timestamp=time_str,
            user_id=user,
            api_key=api_key,
            action=random.choice(actions),
            data_size_bytes=data_size,
            resource=random.choice(resources),
            source_ip=f"10.0.{random.randint(0,255)}.{random.randint(0,255)}"
        ))
    
    return baseline_events, current_events


def main():
    parser = argparse.ArgumentParser(
        description="SaaS Data Exfiltration Rate Monitor - Behavioral Anomaly Detection"
    )
    parser.add_argument(
        "--sigma-threshold",
        type=float,
        default=3.0,
        help="Z-score threshold for anomaly alert (default: 3.0 for 3-sigma)"
    )
    parser.add_argument(
        "--baseline-hours",
        type=int,
        default=168,
        help="Hours of historical data for baseline computation (default: 168 = 1 week)"
    )
    parser.add_argument(
        "--inject-anomaly",
        action="store_true",
        help="Inject synthetic anomalies into test data"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format for results"
    )
    
    args = parser.parse_args()
    
    print(f"[*] Initializing ExfiltrationMonitor (sigma={args.sigma_threshold}, baseline_hours={args.baseline_hours})",
          file=sys.stderr)
    monitor = ExfiltrationMonitor(
        sigma_threshold=args.sigma_threshold,
        baseline_hours=args.baseline_hours
    )
    
    print("[*] Generating test data...", file=sys.stderr)
    baseline_events, current_events = generate_test_events(
        num_baseline_hours=args.baseline_hours,
        num_current_events=100,
        inject_anomaly=args.inject_anomaly
    )
    
    print(f"[*] Ingesting {len(baseline_events)} baseline events", file=sys.stderr)
    monitor.ingest_events(baseline_events)
    
    print("[*] Computing baselines via unsupervised learning...", file=sys.stderr)
    baselines = monitor.compute_baselines(baseline_events)
    print(f"[+] Computed {len(baselines)} user/API key baselines", file=sys.stderr)
    
    print(f"[*] Ingesting {len(current_events)} current hour events", file=sys.stderr)
    monitor.ingest_events(current_events)
    
    current_hour = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H")
    print(f"[*] Detecting anomalies for hour: {current_hour}", file=sys.stderr)
    alerts = monitor.detect_anomalies(current_hour)
    
    print(f"[+] Found {len(alerts)} anomaly alerts", file=sys.stderr)
    
    summary = monitor.get_summary()
    
    if args.output_format == "json":
        output = json.dumps(summary, indent=2)
        print(output)
    else:
        print(f"\n=== EXFILTRATION MONITOR SUMMARY ===")
        print(f"Baselines computed: {summary['baseline_count']}")
        print(f"Total alerts: {summary['alert_count']}")
        print(f"  CRITICAL: {summary['critical_alerts']}")
        print(f"  HIGH:     {summary['high_alerts']}")
        print(f"  MEDIUM:   {summary['medium_alerts']}")
        
        if summary['alerts']:
            print(f"\n=== ALERTS (sorted by Z-score) ===")
            sorted_alerts = sorted(summary['alerts'], key=lambda x: x['zscore'], reverse=True)
            for alert in sorted_alerts[:10]:
                print(f"\n[{alert['alert_level']}] {alert['timestamp']}")
                print(f"  User: {alert['user_id']} | API Key: {alert['api_key']}")
                print(f"  Observed: {alert['observed_bytes']:,} bytes")
                print(f"  Baseline: {alert['baseline_mean']:,.0f} ± {alert['baseline_stddev']:,.0f} bytes")
                print(f"  Z-Score: {alert['zscore']:.2f}")
                print(f"  Message: {alert['message']}")


if __name__ == "__main__":
    main()
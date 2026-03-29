#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build behavioral baseline engine
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-29T20:34:09.397Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build behavioral baseline engine
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @echo
DATE: 2024-01-15

Behavioral baseline engine for SaaS breach detection.
Ingests audit logs, builds user behavioral baselines, computes anomaly scores,
detects impossible travel, and triggers automated responses.
"""

import argparse
import json
import sys
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import math
import hashlib


@dataclass
class AuditEvent:
    """Represents a single audit log entry."""
    timestamp: str
    user_id: str
    action: str
    resource: str
    ip_address: str
    location: str
    latitude: float
    longitude: float
    user_agent: str
    success: bool


@dataclass
class UserBaseline:
    """User behavioral baseline metrics."""
    user_id: str
    avg_daily_actions: float
    std_dev_actions: float
    most_common_actions: List[str]
    most_common_locations: List[str]
    most_common_ips: List[str]
    avg_action_time_of_day: float
    common_resources: List[str]
    baseline_period_days: int
    last_updated: str


@dataclass
class AnomalyScore:
    """Anomaly detection result for a user event."""
    event_id: str
    user_id: str
    timestamp: str
    anomaly_score: float
    risk_factors: List[str]
    is_anomaly: bool
    impossible_travel: bool
    action_type: str


def parse_audit_log(log_file: str) -> List[AuditEvent]:
    """Parse audit log file (JSON lines format)."""
    events = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    events.append(AuditEvent(**data))
    except FileNotFoundError:
        print(f"Error: Log file {log_file} not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in log file: {e}", file=sys.stderr)
        sys.exit(1)
    return events


def build_baseline(events: List[AuditEvent], baseline_days: int = 30) -> Dict[str, UserBaseline]:
    """Build behavioral baselines for each user from historical events."""
    cutoff_time = datetime.utcnow() - timedelta(days=baseline_days)
    cutoff_str = cutoff_time.isoformat()

    user_events = defaultdict(list)

    for event in events:
        if event.timestamp >= cutoff_str and event.success:
            user_events[event.user_id].append(event)

    baselines = {}

    for user_id, user_event_list in user_events.items():
        if not user_event_list:
            continue

        action_counts = defaultdict(int)
        location_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        resource_counts = defaultdict(int)
        hours_of_day = []

        for event in user_event_list:
            action_counts[event.action] += 1
            location_counts[event.location] += 1
            ip_counts[event.ip_address] += 1
            resource_counts[event.resource] += 1

            event_time = datetime.fromisoformat(event.timestamp)
            hours_of_day.append(event_time.hour)

        daily_action_counts = []
        date_actions = defaultdict(int)
        for event in user_event_list:
            event_date = event.timestamp.split('T')[0]
            date_actions[event_date] += 1
        daily_action_counts = list(date_actions.values())

        avg_daily = statistics.mean(daily_action_counts) if daily_action_counts else 1.0
        std_dev = statistics.stdev(daily_action_counts) if len(daily_action_counts) > 1 else 0.0

        most_common_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_common_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_common_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        common_resources = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        avg_hour = statistics.mean(hours_of_day) if hours_of_day else 12.0

        baselines[user_id] = UserBaseline(
            user_id=user_id,
            avg_daily_actions=avg_daily,
            std_dev_actions=std_dev,
            most_common_actions=[a[0] for a in most_common_actions],
            most_common_locations=[l[0] for l in most_common_locations],
            most_common_ips=[ip[0] for ip in most_common_ips],
            avg_action_time_of_day=avg_hour,
            common_resources=[r[0] for r in common_resources],
            baseline_period_days=baseline_days,
            last_updated=datetime.utcnow().isoformat()
        )

    return baselines


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers."""
    R = 6371

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def detect_impossible_travel(
    prev_event: Optional[AuditEvent],
    current_event: AuditEvent,
    max_speed_kmh: float = 900
) -> Tuple[bool, float]:
    """
    Detect impossible travel (too fast between locations).
    Returns (is_impossible, required_speed_kmh).
    """
    if not prev_event:
        return False, 0.0

    time_diff = (datetime.fromisoformat(current_event.timestamp) -
                 datetime.fromisoformat(prev_event.timestamp)).total_seconds() / 3600

    if time_diff <= 0 or time_diff > 24:
        return False, 0.0

    distance = haversine_distance(
        prev_event.latitude, prev_event.longitude,
        current_event.latitude, current_event.longitude
    )

    required_speed = distance / time_diff

    is_impossible = required_speed > max_speed_kmh

    return is_impossible, required_speed


def compute_anomaly_score(
    event: AuditEvent,
    baseline: Optional[UserBaseline],
    last_event: Optional[AuditEvent] = None,
    impossible_travel_threshold: float = 900
) -> AnomalyScore:
    """Compute anomaly score for an event based on baseline."""
    event_id = hashlib.sha256(
        f"{event.user_id}{event.timestamp}{event.action}".encode()
    ).hexdigest()[:16]

    risk_factors = []
    score = 0.0

    if not baseline:
        score = 0.5
        risk_factors.append("no_baseline")
    else:
        if event.action not in baseline.most_common_actions:
            score += 0.15
            risk_factors.append(f"unusual_action:{event.action}")

        if event.location not in baseline.most_common_locations:
            score += 0.20
            risk_factors.append(f"unusual_location:{event.location}")

        if event.ip_address not in baseline.most_common_ips:
            score += 0.15
            risk_factors.append(f"unusual_ip:{event.ip_address}")

        if event.resource not in baseline.common_resources:
            score += 0.10
            risk_factors.append(f"unusual_resource:{event.resource}")

        event_time = datetime.fromisoformat(event.timestamp)
        hour = event_time.hour
        hour_diff = min(abs(hour - baseline.avg_action_time_of_day),
                        24 - abs(hour - baseline.avg_action_time_of_day))

        if hour_diff > 6:
            score += 0.10
            risk_factors.append(f"unusual_hour:{hour}")

    is_impossible_travel = False
    if last_event:
        is_impossible_travel, required_speed = detect_impossible_travel(
            last_event, event, impossible_travel_threshold
        )
        if is_impossible_travel:
            score += 0.30
            risk_factors.append(f"impossible_travel:{required_speed:.1f}kmh")

    score = min(score, 1.0)

    is_anomaly = score >= 0.6

    return AnomalyScore(
        event_id=event_id,
        user_id=event.user_id,
        timestamp=event.timestamp,
        anomaly_score=round(score, 3),
        risk_factors=risk_factors,
        is_anomaly=is_anomaly,
        impossible_travel=is_impossible_travel,
        action_type=event.action
    )


def detect_anomalies(
    events: List[AuditEvent],
    baselines: Dict[str, UserBaseline],
    impossible_travel_threshold: float = 900
) -> List[AnomalyScore]:
    """Detect anomalies in events using baselines."""
    sorted_events = sorted(events, key=lambda e: (e.user_id, e.timestamp))

    user_last_event = {}
    anomalies = []

    for event in sorted_events:
        baseline = baselines.get(event.user_id)
        last_event = user_last_event.get(event.user_id)

        anomaly = compute_anomaly_score(
            event, baseline, last_event, impossible_travel_threshold
        )
        anomalies.append(anomaly)

        user_last_event[event.user_id] = event

    return anomalies


def generate_response_actions(anomaly: AnomalyScore) -> List[Dict]:
    """Generate automated response actions based on anomaly score."""
    actions = []

    if anomaly.anomaly_score >= 0.9:
        actions.append({
            "action": "block_session",
            "reason": "critical_anomaly",
            "user_id": anomaly.user_id,
            "severity": "critical"
        })
        actions.append({
            "action": "notify_security",
            "reason": f"Critical anomaly detected: {', '.join(anomaly.risk_factors)}",
            "user_id": anomaly.user_id,
            "severity": "critical"
        })

    elif anomaly.anomaly_score >= 0.7:
        actions.append({
            "action": "require_mfa",
            "reason": "high_anomaly",
            "user_id": anomaly.user_id,
            "severity": "high"
        })
        actions.append({
            "action": "notify_user",
            "reason": "Unusual activity detected on your account",
            "user_id": anomaly.user_id,
            "severity": "high"
        })

    elif anomaly.anomaly_score >= 0.6:
        actions.append({
            "action": "increase_monitoring",
            "reason": "moderate_anomaly",
            "user_id": anomaly.user_id,
            "severity": "medium"
        })

    if anomaly.impossible_travel:
        actions.append({
            "action": "alert_geographic_anomaly",
            "reason": "Impossible travel detected",
            "user_id": anomaly.user_id,
            "severity": "high"
        })

    return actions


def save_results(baselines: Dict[str, UserBaseline], anomalies: List[AnomalyScore],
                 all_actions: List[Dict], output_file: str):
    """Save analysis results to JSON file."""
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "baselines_count": len(baselines),
        "anomalies_detected": len([a for a in anomalies if a.is_anomaly]),
        "total_events_analyzed": len(anomalies),
        "automated_actions_triggered": len(all_actions),
        "baselines": [asdict(b) for b in baselines.values()],
        "anomalies": [asdict(a) for a in anomalies if a.is_anomaly],
        "response_actions": all_actions
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {output_file}")


def generate_sample_logs(output_file: str, num_events: int = 100):
    """Generate sample audit logs for testing."""
    import random

    users = ["user_001", "user_002", "user_003", "attacker_001"]
    actions = ["login", "read", "write", "delete", "export"]
    resources = ["file_1", "file_2", "db_query", "api_endpoint"]
    locations = [
        "New York", "London", "Tokyo", "Sydney", "Mumbai",
        "Moscow", "São Paulo", "Hong Kong"
    ]
    location_coords = {
        "New York": (40.7128, -74.0060),
        "London": (51.5074, -0.1278),
        "Tokyo": (35.6762, 139.6503),
        "Sydney": (-33.8688, 151.2093),
        "Mumbai": (19.0760, 72.8777),
        "Moscow": (55.7558, 37.6173),
        "São Paulo": (-23.5505, -46.6333),
        "Hong Kong": (22.3193, 114.1694)
    }

    base_time = datetime.utcnow() - timedelta(days=60)

    with open(output_file, 'w') as f:
        for i in range(num_events):
            user = random.choice(users)
            location = random.choice(locations)
            lat, lon = location_coords[location]

            lat += random.gauss(0, 0.5)
            lon += random.gauss(0, 0.5)

            event_time = base_time + timedelta(hours=random.randint(0, 60*24))

            event = {
                "timestamp": event_time.isoformat(),
                "user_id": user,
                "action": random.choice(actions),
                "resource": random.choice(resources),
                "ip_address": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "user_agent": f"Mozilla/5.0 (Platform {random.randint(1,5)})",
                "success": random.random() > 0.05
            }

            if user == "attacker_001" and random.random() < 0.5:
                event["action"] = "export"
                event["resource"] = "sensitive_db"
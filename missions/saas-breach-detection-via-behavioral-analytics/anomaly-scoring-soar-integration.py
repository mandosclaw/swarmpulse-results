#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Anomaly scoring + SOAR integration
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @quinn
# Date:    2026-03-28T21:57:18.713Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Anomaly scoring + SOAR integration for SaaS breach detection
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @quinn
DATE: 2025-01-15
"""

import argparse
import json
import sys
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from statistics import mean, stdev
import math


class AnomalyDetector:
    """Unsupervised anomaly detection for SaaS audit logs."""

    def __init__(
        self,
        baseline_days: int = 30,
        credential_stuffing_threshold: float = 5.0,
        impossible_travel_threshold: float = 7.0,
        mass_download_threshold: float = 6.0,
        privilege_creep_threshold: float = 5.5,
        critical_score_threshold: float = 8.0,
    ):
        self.baseline_days = baseline_days
        self.credential_stuffing_threshold = credential_stuffing_threshold
        self.impossible_travel_threshold = impossible_travel_threshold
        self.mass_download_threshold = mass_download_threshold
        self.privilege_creep_threshold = privilege_creep_threshold
        self.critical_score_threshold = critical_score_threshold

        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.baseline_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.alerts: List[Dict[str, Any]] = []
        self.revoked_sessions: List[str] = []

    def ingest_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Ingest audit logs and build baseline profiles."""
        for log in logs:
            user_id = log.get("user_id", "unknown")
            timestamp = log.get("timestamp", datetime.now().isoformat())
            log_time = datetime.fromisoformat(timestamp)

            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = {
                    "login_locations": [],
                    "login_times": [],
                    "data_access_volume": [],
                    "privilege_changes": [],
                    "failed_login_attempts": [],
                    "session_ids": set(),
                }

            profile = self.user_profiles[user_id]

            if log.get("event_type") == "login":
                profile["login_locations"].append(log.get("location", "unknown"))
                profile["login_times"].append(log_time)
                if log.get("session_id"):
                    profile["session_ids"].add(log["session_id"])

            elif log.get("event_type") == "failed_login":
                profile["failed_login_attempts"].append(
                    {"timestamp": log_time, "ip": log.get("ip_address", "unknown")}
                )

            elif log.get("event_type") == "data_access":
                volume = log.get("data_volume_bytes", 0)
                profile["data_access_volume"].append(
                    {"timestamp": log_time, "bytes": volume}
                )

            elif log.get("event_type") == "privilege_change":
                profile["privilege_changes"].append(
                    {
                        "timestamp": log_time,
                        "action": log.get("action", "unknown"),
                        "role": log.get("role", "unknown"),
                    }
                )

            days_old = (datetime.now() - log_time).days
            if days_old <= self.baseline_days:
                self.baseline_data[user_id].append(log)

    def calculate_baseline_stats(self, user_id: str) -> Dict[str, Any]:
        """Calculate statistical baseline for a user."""
        profile = self.user_profiles.get(user_id, {})
        stats = {
            "avg_daily_logins": 0,
            "common_locations": [],
            "typical_login_hours": [],
            "avg_daily_data_access": 0,
            "privilege_change_frequency": 0,
            "failed_login_baseline": 0,
        }

        if profile.get("login_times"):
            days_active = len(set(t.date() for t in profile["login_times"]))
            stats["avg_daily_logins"] = (
                len(profile["login_times"]) / max(days_active, 1)
            )
            stats["typical_login_hours"] = list(
                set(t.hour for t in profile["login_times"][-100:])
            )
            location_counts = defaultdict(int)
            for loc in profile["login_locations"][-100:]:
                location_counts[loc] += 1
            stats["common_locations"] = [
                loc
                for loc, _ in sorted(
                    location_counts.items(), key=lambda x: x[1], reverse=True
                )[:3]
            ]

        if profile.get("data_access_volume"):
            total_bytes = sum(d.get("bytes", 0) for d in profile["data_access_volume"])
            days_with_access = len(
                set(d["timestamp"].date() for d in profile["data_access_volume"])
            )
            stats["avg_daily_data_access"] = total_bytes / max(days_with_access, 1)

        if profile.get("privilege_changes"):
            days_active = len(
                set(p["timestamp"].date() for p in profile["privilege_changes"])
            )
            stats["privilege_change_frequency"] = len(
                profile["privilege_changes"]
            ) / max(days_active, 1)

        if profile.get("failed_login_attempts"):
            days_with_failures = len(
                set(f["timestamp"].date() for f in profile["failed_login_attempts"])
            )
            stats["failed_login_baseline"] = len(
                profile["failed_login_attempts"]
            ) / max(days_with_failures, 1)

        return stats

    def detect_credential_stuffing(
        self, user_id: str, recent_logs: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """Detect credential stuffing via failed login spike."""
        score = 0.0
        indicators = []

        failed_logins = [
            l
            for l in recent_logs
            if l.get("event_type") == "failed_login"
            and l.get("user_id") == user_id
        ]

        if len(failed_logins) > 5:
            score += 2.0
            indicators.append(f"Multiple failed logins: {len(failed_logins)} in window")

        if failed_logins:
            unique_ips = len(set(l.get("ip_address", "unknown") for l in failed_logins))
            if unique_ips > 3:
                score += 1.5
                indicators.append(f"Failed logins from {unique_ips} different IPs")

            time_deltas = []
            sorted_logs = sorted(failed_logins, key=lambda x: x.get("timestamp", ""))
            for i in range(1, len(sorted_logs)):
                t1 = datetime.fromisoformat(sorted_logs[i - 1].get("timestamp", ""))
                t2 = datetime.fromisoformat(sorted_logs[i].get("timestamp", ""))
                delta = (t2 - t1).total_seconds()
                if delta > 0:
                    time_deltas.append(delta)

            if time_deltas and mean(time_deltas) < 30:
                score += 1.5
                indicators.append("Rapid-fire failed login attempts detected")

        return min(score, 10.0), indicators

    def detect_impossible_travel(
        self, user_id: str, recent_logs: List[Dict[str, Any]]
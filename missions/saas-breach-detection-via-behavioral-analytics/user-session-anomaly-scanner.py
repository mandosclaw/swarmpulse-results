#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    User session anomaly scanner
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-28T22:06:22.383Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: User session anomaly scanner
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @sue
Date: 2026

Detects compromised sessions by analyzing login timestamps, IP geolocation,
and user-agent patterns. Flags impossible travel and concurrent sessions.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class SessionEvent:
    """Represents a user session event from audit logs."""
    user_id: str
    timestamp: str
    ip_address: str
    user_agent: str
    action: str
    location_country: str
    location_city: str
    latitude: float
    longitude: float


@dataclass
class AnomalyAlert:
    """Represents a detected anomaly."""
    severity: str
    alert_type: str
    user_id: str
    timestamp: str
    details: Dict[str, Any]


class GeoDistance:
    """Simple great-circle distance calculator."""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates in kilometers.
        Uses Haversine formula.
        """
        R = 6371  # Earth radius in km
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


class SessionAnomalyScanner:
    """Detects anomalies in user sessions using behavioral analytics."""

    def __init__(
        self,
        max_travel_speed_kmh: float = 900,
        max_concurrent_sessions: int = 3,
        suspicious_ua_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the scanner with thresholds.

        Args:
            max_travel_speed_kmh: Maximum realistic travel speed (km/h)
            max_concurrent_sessions: Alert if user has more concurrent sessions
            suspicious_ua_patterns: List of suspicious user-agent patterns
        """
        self.max_travel_speed_kmh = max_travel_speed_kmh
        self.max_concurrent_sessions = max_concurrent_sessions
        self.suspicious_ua_patterns = suspicious_ua_patterns or [
            "curl", "wget", "python-requests", "scrapy", "bot",
            "sqlmap", "nikto", "masscan"
        ]
        self.user_sessions: Dict[str, List[SessionEvent]] = defaultdict(list)
        self.alerts: List[AnomalyAlert] = []

    def add_event(self, event: SessionEvent) -> None:
        """Add a session event to the scanner."""
        self.user_sessions[event.user_id].append(event)

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO format timestamp."""
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.now()

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user-agent matches suspicious patterns."""
        ua_lower = user_agent.lower()
        return any(pattern.lower() in ua_lower for pattern in self.suspicious_ua_patterns)

    def _check_impossible_travel(self, user_id: str) -> None:
        """
        Check for impossible travel: two logins too far apart in too little time.
        """
        events = sorted(self.user_sessions[user_id], key=lambda e: self._parse_timestamp(e.timestamp))

        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]

            current_time = self._parse_timestamp(current.timestamp)
            next_time = self._parse_timestamp(next_event.timestamp)
            time_diff_hours = (next_time - current_time).total_seconds() / 3600

            if time_diff_hours <= 0:
                continue

            distance_km = GeoDistance.haversine_distance(
                current.latitude, current.longitude,
                next_event.latitude, next_event.longitude
            )

            required_speed_kmh = distance_km / time_diff_hours

            if required_speed_kmh > self.max_travel_speed_kmh and distance_km > 100:
                self.alerts.append(AnomalyAlert(
                    severity="high",
                    alert_type="impossible_travel",
                    user_id=user_id,
                    timestamp=next_event.timestamp,
                    details={
                        "from_location": f"{current.location_city}, {current.location_country}",
                        "to_location": f"{next_event.location_city}, {next_event.location_country}",
                        "distance_km": round(distance_km, 2),
                        "time_hours": round(time_diff_hours, 2),
                        "required_speed_kmh": round(required_speed_kmh, 2),
                        "max_realistic_speed_kmh": self.max_travel_speed_kmh,
                        "from_ip": current.ip_address,
                        "to_ip": next_event.ip_address,
                    }
                ))

    def _check_concurrent_sessions(self, user_id: str) -> None:
        """
        Check for suspicious concurrent sessions.
        Flags when user has too many simultaneous sessions or sessions from different IPs/UAs.
        """
        events = sorted(self.user_sessions[user_id], key=lambda e: self._parse_timestamp(e.timestamp))

        time_window = timedelta(minutes=30)

        for i, current_event in enumerate(events):
            current_time = self._parse_timestamp(current_event.timestamp)
            concurrent_events = []

            for other_event in events:
                if other_event == current_event:
                    continue
                other_time = self._parse_timestamp(other_event.timestamp)
                if abs((current_time - other_time).total_seconds()) < time_window.total_seconds():
                    concurrent_events.append(other_event)

            if len(concurrent_events) >= self.max_concurrent_sessions - 1:
                unique_ips = set(e.ip_address for e in [current_event] + concurrent_events)
                unique_uas = set(e.user_agent for e in [current_event] + concurrent_events)

                self.alerts.append(AnomalyAlert(
                    severity="medium",
                    alert_type="concurrent_sessions",
                    user_id=user_id,
                    timestamp=current_event.timestamp,
                    details={
                        "concurrent_count": len(concurrent_events) + 1,
                        "time_window_minutes": 30,
                        "unique_ips": list(unique_ips),
                        "unique_user_agents": list(unique_uas),
                        "distinct_locations": list(set(
                            f"{e.location_city}, {e.location_country}"
                            for e in [current_event] + concurrent_events
                        )),
                    }
                ))
                break

    def _check_suspicious_user_agent(self, user_id: str) -> None:
        """Check for suspicious user-agent strings."""
        for event in self.user_sessions[user_id]:
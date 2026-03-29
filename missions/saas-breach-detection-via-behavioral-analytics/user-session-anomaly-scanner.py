#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    User session anomaly scanner
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-29T13:23:27.303Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
User Session Anomaly Scanner for SaaS Breach Detection
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @sue
Date: 2026
Task: Detect compromised sessions by analyzing login timestamps, IP geolocation, and user-agent patterns
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import math
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AnomalyType(Enum):
    """Types of detected anomalies"""
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    CONCURRENT_SESSIONS = "concurrent_sessions"
    IMPOSSIBLE_LOGIN_VELOCITY = "impossible_login_velocity"
    UNUSUAL_GEOLOCATION = "unusual_geolocation"
    NEW_USER_AGENT = "new_user_agent"
    CREDENTIAL_STUFFING = "credential_stuffing"
    MASS_DOWNLOAD = "mass_download"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class GeoLocation:
    """Geographic location coordinates"""
    latitude: float
    longitude: float
    city: str
    country: str
    country_code: str


@dataclass
class SessionEvent:
    """A single session/login event"""
    user_id: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    action: str
    location: GeoLocation
    resource_accessed: Optional[str] = None
    data_downloaded: int = 0
    privilege_level: Optional[str] = None


@dataclass
class AnomalyAlert:
    """An anomaly detection alert"""
    anomaly_type: AnomalyType
    user_id: str
    severity: str
    timestamp: datetime
    details: Dict
    confidence: float


class GeoDistanceCalculator:
    """Calculate geographic distance between coordinates"""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance in kilometers between two geographic points.
        Uses Haversine formula.
        """
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    @staticmethod
    def is_impossible_travel(
        loc1: GeoLocation,
        time1: datetime,
        loc2: GeoLocation,
        time2: datetime,
        max_speed_kmh: float = 900,
    ) -> Tuple[bool, float]:
        """
        Detect if travel between two locations is physically impossible.
        Assumes max human travel speed (commercial airline ~900 km/h).
        Returns (is_impossible, required_speed_kmh)
        """
        distance_km = GeoDistanceCalculator.haversine_distance(
            loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude
        )
        time_diff = abs((time2 - time1).total_seconds()) / 3600
        if time_diff < 0.1:
            time_diff = 0.1

        required_speed = distance_km / time_diff
        is_impossible = required_speed > max_speed_kmh
        return is_impossible, required_speed


class SessionAnomalyScanner:
    """Main anomaly detection engine for user sessions"""

    def __init__(
        self,
        impossible_travel_speed_kmh: float = 900,
        concurrent_session_threshold: int = 5,
        login_velocity_threshold: int = 10,
        mass_download_threshold: int = 1000000,
        mass_download_window_minutes: int = 10,
    ):
        self.impossible_travel_speed_kmh = impossible_travel_speed_kmh
        self.concurrent_session_threshold = concurrent_session_threshold
        self.login_velocity_threshold = login_velocity_threshold
        self.mass_download_threshold = mass_download_threshold
        self.mass_download_window_minutes = mass_download_window_minutes

        self.user_sessions: Dict[str, List[SessionEvent]] = defaultdict(list)
        self.user_baselines: Dict[str, Dict] = {}
        self.alerts: List[AnomalyAlert] = []

    def add_event(self, event: SessionEvent) -> None:
        """Add a session event to the scanner"""
        self.user_sessions[event.user_id].append(event)

    def build_baselines(self) -> None:
        """Build behavioral baselines from historical data"""
        for user_id, events in self.user_sessions.items():
            if not events:
                continue

            sorted_events = sorted(events, key=lambda e: e.timestamp)
            self.user_baselines[user_id] = {
                "common_ips": self._extract_common_values([e.ip_address for e in sorted_events]),
                "common_user_agents": self._extract_common_values([e.user_agent for e in sorted_events]),
                "common_locations": self._extract_common_locations([e.location for e in sorted_events]),
                "typical_login_hours": self._extract_login_hours([e.timestamp for e in sorted_events]),
                "total_events": len(sorted_events),
            }

    def scan_all_events(self) -> List[AnomalyAlert]:
        """Scan all events and detect anomalies"""
        self.alerts = []
        self.build_baselines()

        for user_id in self.user_sessions:
            events = sorted(self.user_sessions[user_id], key=lambda e: e.timestamp)
            self._scan_user_events(user_id, events)

        return self.alerts

    def _scan_user_events(self, user_id: str, events: List[SessionEvent]) -> None:
        """Scan all events for a specific user"""
        for i, event in enumerate(events):
            if i > 0:
                prev_event = events[i - 1]
                self._check_impossible_travel(user_id, prev_event, event)

            self._check_user_agent_anomaly(user_id, event)
            self._check_concurrent_sessions(user_id, event, events)
            self._check_login_velocity(user_id, event, events)
            self._check_mass_download(user_id, event, events)
            self._check_geolocation_anomaly(user_id, event)
            self._check_privilege_escalation(user_id, event, events)

    def _check_impossible_travel(
        self, user_id: str, prev_event: SessionEvent, current_event: SessionEvent
    ) -> None:
        """Check for impossible travel between two events"""
        is_impossible, required_speed = GeoDistanceCalculator.is_impossible_travel(
            prev_event.location,
            prev_event.timestamp,
            current_event.location,
            current_event.timestamp,
            self.impossible_travel_speed_kmh,
        )

        if is_impossible:
            time_diff_hours = (current_event.timestamp - prev_event.timestamp).total_seconds() / 3600
            alert = AnomalyAlert(
                anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                user_id=user_id,
                severity="high",
                timestamp=current_event.timestamp,
                details={
                    "from_location": asdict(prev_event.location),
                    "to_location": asdict(current_event.location),
                    "time_difference_hours": round(time_diff_hours, 2),
                    "required_speed_kmh": round(required_speed, 2),
                    "max_possible_speed_kmh": self.impossible_travel_speed_kmh,
                },
                confidence=0.95,
            )
            self.alerts.append(alert)

    def _check_user_agent_anomaly(self, user_id: str, event: SessionEvent) -> None:
        """Check for unusual user agent"""
        baseline = self.user_baselines.get(user_id, {})
        common_agents = baseline.get("common_user_agents", [])

        if common_agents and event.user_agent not in common_agents:
            alert = AnomalyAlert(
                anomaly_type=AnomalyType.NEW_USER_AGENT,
                user_id=user_id,
                severity="medium",
                timestamp=event.timestamp,
                details={
                    "user_agent": event.user_agent,
                    "historical_agents": common_agents[:5],
                },
                confidence=0.7,
            )
            self.alerts.append(alert)

    def _check_concurrent_sessions(
        self, user_id: str, event: SessionEvent, all_events: List[SessionEvent]
    ) -> None:
        """Check for too many concurrent sessions"""
        concurrent_count = sum(
            1
            for e in all_events
            if e.timestamp <= event.timestamp
            and e.timestamp > event.timestamp - timedelta(minutes=5)
            and e.ip_address != event.ip_address
        )

        if concurrent_count >= self.concurrent_session_threshold:
            alert = AnomalyAlert(
                anomaly_type=AnomalyType.CONCURRENT_SESSIONS,
                user_id=user_id,
                severity="high",
                timestamp=event.timestamp,
                details={
                    "concurrent_session_count": concurrent_count,
                    "threshold": self.concurrent_session_threshold,
                    "ip_addresses": list(
                        set(
                            e.ip_address
                            for e in all_events
                            if e.timestamp <= event.timestamp
                            and e.timestamp > event.timestamp - timedelta(minutes=5)
                        )
                    )[:10],
                },
                confidence=0.85,
            )
            self.alerts.append(alert)

    def _check_login_velocity(self, user_id: str, event: SessionEvent, all_events: List[SessionEvent]) -> None:
        """Check for impossible login velocity (credential stuffing)"""
        recent_logins = [
            e for e in all_events if e.timestamp > event.timestamp - timedelta(minutes=5) and e.action == "login"
        ]

        if len(recent_logins) >= self.login_velocity_threshold:
            alert = AnomalyAlert(
                anomaly_type=AnomalyType.CREDENTIAL_STUFFING,
                user_id=user_id,
                severity="critical",
                timestamp=event.timestamp,
                details={
                    "login_attempts_5min": len(recent_logins),
                    "threshold": self.login_velocity_threshold,
                    "ips_involved": list(set(e.ip_address for e in recent_logins)),
                },
                confidence=0.9,
            )
            self.alerts.append(alert)

    def _check_mass_download(self, user_id: str, event: SessionEvent, all_events: List[SessionEvent]) -> None:
        """Check for mass data downloads"""
        if event.action != "download":
            return

        window_start = event.timestamp - timedelta(minutes=self.mass_download_window_minutes)
        recent_downloads = [
            e
            for e in all_events
            if e.timestamp >= window_start
            and e.timestamp <= event.timestamp
            and e.action == "download"
            and e.ip_address == event.ip_address
        ]

        total_downloaded = sum(e.data_downloaded for e in recent_downloads)

        if total_downloaded >= self.mass_download_threshold:
            alert = AnomalyAlert(
                anomaly_type=AnomalyType.MASS_DOWNLOAD,
                user_id=user_id,
                severity="high",
                timestamp=event.timestamp,
                details={
                    "total_bytes_downloaded": total_downloaded,
                    "threshold_bytes": self.mass_download_threshold,
                    "download_count": len(recent_downloads),
                    "time_window_minutes": self.mass_download_window_minutes,
                    "ip_address": event.ip_address,
                },
                confidence=0.88,
            )
            self.alerts.append(alert)

    def _check_geolocation_anomaly(self, user_id: str, event: SessionEvent) -> None:
        """Check for unusual geolocation patterns"""
        baseline = self.user_baselines.get(user_id, {})
        common_locations = baseline.get("common_locations", [])

        if common_locations:
            location_match = any(
                loc["country_code"] == event.location.country_code for loc in common_locations
            )

            if not location_match:
                alert = AnomalyAlert(
                    anomaly_type=AnomalyType.UNUSUAL_GEOLOCATION,
                    user_id=user_id,
                    severity="medium",
                    timestamp=event.timestamp,
                    details={
                        "location": asdict(event.location),
                        "typical_locations": common_locations[:3],
                    },
                    confidence=0.65,
                )
                self.alerts.append(alert)

    def _check_privilege_escalation(self, user_id: str, event: SessionEvent, all_events: List[SessionEvent]) -> None:
        """Check for privilege escalation attempts"""
        baseline_privilege = None
        for e in all_events:
            if e.timestamp < event.timestamp and e.privilege_level:
                baseline_privilege = e.privilege_level
                break

        if (
            baseline_privilege
            and event.privilege_level
            and self._privilege_level_rank(event.privilege_level) > self._privilege_level_rank(baseline_privilege)
        ):
            recent_escalations = sum(
                1
                for e in all_events
                if e.timestamp > event.timestamp - timedelta(hours=1)
                and e.privilege_level
                and self._privilege_level_rank(e.privilege_level) > self._privilege_level_rank(baseline_privilege)
            )

            if recent_escalations >= 2:
                alert = AnomalyAlert(
                    anomaly_type=AnomalyType.PRIVILEGE_ESCALATION,
                    user_id=user_id,
                    severity="critical",
                    timestamp=event.timestamp,
                    details={
                        "from_privilege": baseline_privilege,
                        "to_privilege": event.privilege_level,
                        "recent_escalations_1h": recent_escalations,
                    },
                    confidence=0.92,
                )
                self.alerts.append(alert)

    @staticmethod
    def _privilege_level_rank(level: str) -> int:
        """Return numeric rank for privilege levels"""
        ranks = {"user": 1, "admin": 2, "superadmin": 3}
        return ranks.get(level.lower(), 0)

    @staticmethod
    def _extract_common_values(values: List[str], top_n: int = 5) -> List[str]:
        """Extract most common values from a list"""
        if not values:
            return []
        value_counts = {}
        for v in values:
            value_counts[v] = value_counts.get(v, 0) + 1
        return sorted(value_counts.keys(), key=lambda x: value_counts[x], reverse=True)[:top_n]

    @staticmethod
    def _extract_common_locations(locations: List[GeoLocation], top_n: int = 3) -> List[Dict]:
        """Extract most common locations"""
        if not locations:
            return []
        location_counts = {}
        for loc in locations:
            key = (loc.country_code, loc.city)
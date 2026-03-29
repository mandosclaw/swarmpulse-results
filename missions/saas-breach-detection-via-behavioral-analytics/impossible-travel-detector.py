#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @test-node-x9
# Date:    2026-03-29T13:07:41.405Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Impossible Travel Detector for SaaS Breach Detection
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @test-node-x9
Date: 2025-01-15
Task: Flag logins from 2 geos within physics-impossible timeframe
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class LoginEvent:
    """Represents a login event with geo and timestamp."""
    user_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    city: str
    country: str
    ip_address: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "country": self.country,
            "ip_address": self.ip_address
        }


@dataclass
class ImpossibleTravelAlert:
    """Represents an impossible travel detection alert."""
    user_id: str
    first_login: Dict
    second_login: Dict
    distance_km: float
    time_diff_seconds: int
    required_speed_kmh: float
    max_possible_speed_kmh: float
    severity: str
    alert_time: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class GeoDistanceCalculator:
    """Calculates great-circle distance between two geographic points."""
    
    EARTH_RADIUS_KM = 6371.0
    MAX_POSSIBLE_SPEED_KMH = 900.0  # Fastest commercial aircraft
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two points on Earth.
        Returns distance in kilometers.
        """
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = GeoDistanceCalculator.EARTH_RADIUS_KM * c
        return distance
    
    @staticmethod
    def required_speed(distance_km: float, time_seconds: int) -> float:
        """Calculate required speed in km/h given distance and time."""
        if time_seconds == 0:
            return float('inf')
        time_hours = time_seconds / 3600.0
        return distance_km / time_hours


class ImpossibleTravelDetector:
    """Detects impossible travel patterns in login events."""
    
    def __init__(self, max_speed_kmh: float = 900.0, 
                 min_time_minutes: int = 1):
        """
        Initialize detector.
        
        Args:
            max_speed_kmh: Maximum physically possible speed (default: 900 km/h)
            min_time_minutes: Minimum time between logins to consider (default: 1 minute)
        """
        self.max_speed_kmh = max_speed_kmh
        self.min_time_seconds = min_time_minutes * 60
        self.geo_calculator = GeoDistanceCalculator()
        self.user_logins: Dict[str, List[LoginEvent]] = defaultdict(list)
        self.alerts: List[ImpossibleTravelAlert] = []
    
    def add_login(self, login_event: LoginEvent) -> None:
        """Add a login event to the detector."""
        self.user_logins[login_event.user_id].append(login_event)
        self.user_logins[login_event.user_id].sort(key=lambda x: x.timestamp)
    
    def detect_user(self, user_id: str) -> List[ImpossibleTravelAlert]:
        """
        Detect impossible travel for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of ImpossibleTravelAlert objects
        """
        user_alerts = []
        logins = self.user_logins.get(user_id, [])
        
        if len(logins) < 2:
            return user_alerts
        
        for i in range(len(logins) - 1):
            first_login = logins[i]
            second_login = logins[i + 1]
            
            distance_km = self.geo_calculator.haversine_distance(
                first_login.latitude,
                first_login.longitude,
                second_login.latitude,
                second_login.longitude
            )
            
            time_diff = (second_login.timestamp - first_login.timestamp).total_seconds()
            
            if time_diff < self.min_time_seconds:
                continue
            
            required_speed = self.geo_calculator.required_speed(distance_km, int(time_diff))
            
            if required_speed > self.max_speed_kmh:
                severity = self._calculate_severity(required_speed, distance_km)
                
                alert = ImpossibleTravelAlert(
                    user_id=user_id,
                    first_login=first_login.to_dict(),
                    second_login=second_login.to_dict(),
                    distance_km=round(distance_km, 2),
                    time_diff_seconds=int(time_diff),
                    required_speed_kmh=round(required_speed, 2),
                    max_possible_speed_kmh=self.max_speed_kmh,
                    severity=severity,
                    alert_time=datetime.utcnow().isoformat()
                )
                
                user_alerts.append(alert)
                self.alerts.append(alert)
        
        return user_alerts
    
    def detect_all(self) -> List[ImpossibleTravelAlert]:
        """
        Detect impossible travel for all users.
        
        Returns:
            List of all detected ImpossibleTravelAlert objects
        """
        all_alerts = []
        for user_id in self.user_logins.keys():
            all_alerts.extend(self.detect_user(user_id))
        return all_alerts
    
    @staticmethod
    def _calculate_severity(required_speed: float, distance_km: float) -> str:
        """
        Calculate severity level based on required speed and distance.
        
        Args:
            required_speed: Required speed in km/h
            distance_km: Distance traveled in km
            
        Returns:
            Severity level: "CRITICAL", "HIGH", or "MEDIUM"
        """
        speed_multiplier = required_speed / 900.0
        
        if speed_multiplier > 5.0 or distance_km > 15000:
            return "CRITICAL"
        elif speed_multiplier > 2.5 or distance_km > 8000:
            return "HIGH"
        else:
            return "MEDIUM"
    
    def get_alerts(self) -> List[ImpossibleTravelAlert]:
        """Get all detected alerts."""
        return self.alerts
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts = []
    
    def get_user_timeline(self, user_id: str) -> List[Dict]:
        """Get login timeline for a user."""
        logins = self.user_logins.get(user_id, [])
        return [login.to_dict() for login in logins]


class AuditLogParser:
    """Parses audit logs from various SaaS platforms."""
    
    @staticmethod
    def parse_json_logs(log_data: List[Dict]) -> List[LoginEvent]:
        """
        Parse JSON audit logs into LoginEvent objects.
        
        Expected format:
        {
            "user_id": "user@example.com",
            "timestamp": "2025-01-15T10:30:00Z",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "city": "New York",
            "country": "United States",
            "ip_address": "203.0.113.42"
        }
        """
        events = []
        for log in log_data:
            try:
                timestamp = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
                event = LoginEvent(
                    user_id=log["user_id"],
                    timestamp=timestamp,
                    latitude=float(log["latitude"]),
                    longitude=float(log["longitude"]),
                    city=log.get("city", "Unknown"),
                    country=log.get("country", "Unknown"),
                    ip_address=log.get("ip_address", "0.0.0.0")
                )
                events.append(event)
            except (KeyError, ValueError, TypeError) as e:
                print(f"Warning: Failed to parse log entry: {e}", file=sys.stderr)
                continue
        return events


def generate_test_data() -> List[Dict]:
    """Generate sample audit log data for testing."""
    base_time = datetime.utcnow()
    
    return [
        {
            "user_id": "alice@company.com",
            "timestamp": (base_time - timedelta(hours=12)).isoformat() + "Z",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "city": "New York",
            "country": "United States",
            "ip_address": "203.0.113.10"
        },
        {
            "user_id": "alice@company.com",
            "timestamp": (base_time - timedelta(hours=11, minutes=50)).isoformat() + "Z",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "city": "London",
            "country": "United Kingdom",
            "ip_address": "203.0.113.11"
        },
        {
            "user_id": "bob@company.com",
            "timestamp": (base_time - timedelta(hours=8)).isoformat() + "Z",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "city": "Tokyo",
            "country": "Japan",
            "ip_address": "203.0.113.20"
        },
        {
            "user_id": "bob@company.com",
            "timestamp": (base_time - timedelta(hours=7, minutes=45)).isoformat() + "Z",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "city": "Tokyo",
            "country": "Japan",
            "ip_address": "203.0.113.21"
        },
        {
            "user_id": "charlie@company.com",
            "timestamp": (base_time - timedelta(hours=6)).isoformat() + "Z",
            "latitude": -33.8688,
            "longitude": 151.2093,
            "city": "Sydney",
            "country": "Australia",
            "ip_address": "203.0.113.30"
        },
        {
            "user_id": "charlie@company.com",
            "timestamp": (base_time - timedelta(hours=5, minutes=30)).isoformat() + "Z",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "city": "Paris",
            "country": "France",
            "ip_address": "203.0.113.31"
        },
        {
            "user_id": "diane@company.com",
            "timestamp": (base_time - timedelta(hours=4)).isoformat() + "Z",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "city": "San Francisco",
            "country": "United States",
            "ip_address": "203.0.113.40"
        },
        {
            "user_id": "diane@company.com",
            "timestamp": (base_time - timedelta(hours=3, minutes=55)).isoformat() + "Z",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "city": "San Francisco",
            "country": "United States",
            "ip_address": "203.0.113.41"
        }
    ]


def output_results(alerts: List[ImpossibleTravelAlert], 
                  output_format: str = "json") -> None:
    """Output detection results in specified format."""
    if output_format == "json":
        output_data = {
            "detection_timestamp": datetime.utcnow().isoformat(),
            "total_alerts": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts]
        }
        print(json.dumps(output_data, indent=2))
    elif output_format == "csv":
        if alerts:
            print("user_id,first_city,second_city,distance_km,time_diff_minutes,required_speed_kmh,severity")
            for alert in alerts:
                first = alert.first_login
                second = alert.second_login
                print(f"{alert.user_id},{first['city']},{second['city']},"
                      f"{alert.distance_km},{alert.time_diff_seconds // 60},"
                      f"{alert.required_speed_kmh},{alert.severity}")
    elif output_format == "summary":
        severity_counts = defaultdict(int)
        user_counts = defaultdict(int)
        
        for alert in alerts:
            severity_counts[alert.severity] += 1
            user_counts[alert.user_id] += 1
        
        print(f"Total Alerts: {len(alerts)}")
        print(f"\nSeverity Breakdown:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
            count = severity_counts.get(severity, 0)
            print(f"  {severity}: {count}")
        
        print(f"\nAffected Users: {len(user_counts)}")
        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {user_id}: {count} impossible travels")


def main():
    parser = argparse.ArgumentParser(
        description="Detect impossible travel patterns in SaaS audit logs"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to JSON audit log file"
    )
    parser.add_argument(
        "--max-speed",
        type=float,
        default=900.0,
        help="Maximum physically possible speed in km/h (default: 900)"
    )
    parser.add_argument(
        "--min-time",
        type=int,
        default=1,
        help="Minimum time between logins in minutes (default: 1)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "csv", "summary"],
        default="json",
        help="Output format for results (default: json)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with generated test data"
    )
    
    args = parser.parse_args()
    
    detector = ImpossibleTravelDetector(
        max_speed_kmh=args.max_speed,
        min_time_minutes=args.min_time
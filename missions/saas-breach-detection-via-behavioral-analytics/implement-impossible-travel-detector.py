#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-31T19:14:37.493Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement impossible travel detector
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2024

Detects impossible travel scenarios in SaaS audit logs by analyzing
geographic locations and timestamps across user sessions.
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


@dataclass
class Location:
    """Geographic location with coordinates"""
    latitude: float
    longitude: float
    city: str
    country: str
    timestamp: datetime


@dataclass
class AuditEvent:
    """SaaS audit log event"""
    user_id: str
    event_type: str
    latitude: float
    longitude: float
    city: str
    country: str
    timestamp: datetime
    ip_address: str
    user_agent: str


@dataclass
class ImpossibleTravelAlert:
    """Alert for detected impossible travel"""
    user_id: str
    event_id_1: str
    event_id_2: str
    location_1: str
    location_2: str
    distance_km: float
    time_delta_seconds: int
    required_speed_kmh: float
    threshold_speed_kmh: float
    severity: str
    timestamp: datetime
    risk_score: float


class GeoCalculator:
    """Calculates geographic distances and metrics"""
    
    EARTH_RADIUS_KM = 6371
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calculate great circle distance between two points on Earth.
        Returns distance in kilometers.
        """
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return GeoCalculator.EARTH_RADIUS_KM * c


class ImpossibleTravelDetector:
    """Detects impossible travel scenarios in audit logs"""
    
    def __init__(self, speed_threshold_kmh: float = 900.0, 
                 min_time_delta_seconds: int = 60):
        """
        Initialize detector.
        
        Args:
            speed_threshold_kmh: Maximum realistic travel speed (default 900 km/h, approx jet speed)
            min_time_delta_seconds: Minimum time between events to check (default 60 seconds)
        """
        self.speed_threshold_kmh = speed_threshold_kmh
        self.min_time_delta_seconds = min_time_delta_seconds
        self.geo_calc = GeoCalculator()
        self.user_locations: Dict[str, List[Tuple[Location, str]]] = defaultdict(list)
        self.alerts: List[ImpossibleTravelAlert] = []
    
    def ingest_event(self, event: AuditEvent, event_id: str) -> None:
        """Add audit event to user's location history"""
        location = Location(
            latitude=event.latitude,
            longitude=event.longitude,
            city=event.city,
            country=event.country,
            timestamp=event.timestamp
        )
        self.user_locations[event.user_id].append((location, event_id))
    
    def _calculate_risk_score(self, required_speed_kmh: float, 
                              threshold_speed_kmh: float,
                              time_delta_seconds: int) -> float:
        """
        Calculate risk score based on speed ratio and time delta.
        Higher score = higher risk. Range: 0.0 to 1.0
        """
        if threshold_speed_kmh == 0:
            return 1.0
        
        speed_ratio = required_speed_kmh / threshold_speed_kmh
        
        if speed_ratio <= 1.0:
            return 0.0
        
        log_ratio = math.log10(speed_ratio + 1)
        time_factor = min(1.0, time_delta_seconds / 3600.0)
        
        risk_score = min(1.0, (log_ratio / 2.0) * time_factor)
        return risk_score
    
    def _determine_severity(self, risk_score: float, 
                           required_speed_kmh: float) -> str:
        """Determine alert severity level"""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def detect_impossible_travel(self, user_id: str) -> List[ImpossibleTravelAlert]:
        """
        Detect impossible travel for a specific user.
        Analyzes consecutive location changes for physically impossible travel.
        """
        if user_id not in self.user_locations:
            return []
        
        locations_and_ids = self.user_locations[user_id]
        locations_and_ids.sort(key=lambda x: x[0].timestamp)
        
        user_alerts = []
        
        for i in range(len(locations_and_ids) - 1):
            loc1, event_id_1 = locations_and_ids[i]
            loc2, event_id_2 = locations_and_ids[i + 1]
            
            time_delta = (loc2.timestamp - loc1.timestamp).total_seconds()
            
            if time_delta < self.min_time_delta_seconds:
                continue
            
            distance_km = self.geo_calc.haversine_distance(
                loc1.latitude, loc1.longitude,
                loc2.latitude, loc2.longitude
            )
            
            required_speed_kmh = (distance_km / time_delta) * 3600
            
            if required_speed_kmh > self.speed_threshold_kmh:
                risk_score = self._calculate_risk_score(
                    required_speed_kmh,
                    self.speed_threshold_kmh,
                    time_delta
                )
                
                severity = self._determine_severity(risk_score, required_speed_kmh)
                
                alert = ImpossibleTravelAlert(
                    user_id=user_id,
                    event_id_1=event_id_1,
                    event_id_2=event_id_2,
                    location_1=f"{loc1.city}, {loc1.country}",
                    location_2=f"{loc2.city}, {loc2.country}",
                    distance_km=round(distance_km, 2),
                    time_delta_seconds=int(time_delta),
                    required_speed_kmh=round(required_speed_kmh, 2),
                    threshold_speed_kmh=self.speed_threshold_kmh,
                    severity=severity,
                    timestamp=loc2.timestamp,
                    risk_score=round(risk_score, 3)
                )
                
                user_alerts.append(alert)
                self.alerts.append(alert)
        
        return user_alerts
    
    def detect_all(self) -> List[ImpossibleTravelAlert]:
        """Detect impossible travel for all users"""
        all_alerts = []
        for user_id in self.user_locations.keys():
            alerts = self.detect_impossible_travel(user_id)
            all_alerts.extend(alerts)
        return all_alerts
    
    def get_alerts_by_severity(self, severity: str) -> List[ImpossibleTravelAlert]:
        """Get alerts filtered by severity level"""
        return [alert for alert in self.alerts if alert.severity == severity]
    
    def get_high_risk_users(self, min_risk_score: float = 0.6) -> Dict[str, int]:
        """Get users with alerts above risk threshold"""
        user_alert_count = defaultdict(int)
        for alert in self.alerts:
            if alert.risk_score >= min_risk_score:
                user_alert_count[alert.user_id] += 1
        return dict(user_alert_count)


def generate_sample_audit_logs() -> List[Tuple[AuditEvent, str]]:
    """Generate sample audit logs for demonstration"""
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    
    events_data = [
        ("user_001", "login", 51.5074, -0.1278, "London", "UK", base_time, "192.168.1.1", "Chrome"),
        ("user_001", "api_call", 51.5074, -0.1278, "London", "UK", base_time + timedelta(minutes=5), "192.168.1.1", "Chrome"),
        ("user_001", "file_download", 35.6762, 139.6503, "Tokyo", "Japan", base_time + timedelta(minutes=10), "203.0.113.45", "Chrome"),
        
        ("user_002", "login", 40.7128, -74.0060, "New York", "USA", base_time, "198.51.100.1", "Firefox"),
        ("user_002", "api_call", 40.7128, -74.0060, "New York", "USA", base_time + timedelta(hours=1), "198.51.100.1", "Firefox"),
        ("user_002", "file_upload", 37.7749, -122.4194, "San Francisco", "USA", base_time + timedelta(hours=2), "198.51.100.1", "Firefox"),
        
        ("user_003", "login", 48.8566, 2.3522, "Paris", "France", base_time, "192.0.2.1", "Safari"),
        ("user_003", "api_call", 48.8566, 2.3522, "Paris", "France", base_time + timedelta(hours=3), "192.0.2.1", "Safari"),
        ("user_003", "permission_change", -33.8688, 151.2093, "Sydney", "Australia", base_time + timedelta(hours=4), "192.0.2.50", "Safari"),
        
        ("user_004", "login", 55.7558, 37.6173, "Moscow", "Russia", base_time, "203.0.113.100", "Edge"),
        ("user_004", "api_call", 55.7558, 37.6173, "Moscow", "Russia", base_time + timedelta(minutes=30), "203.0.113.100", "Edge"),
    ]
    
    events = []
    for idx, (user_id, event_type, lat, lon, city, country, timestamp, ip, ua) in enumerate(events_data):
        event = AuditEvent(
            user_id=user_id,
            event_type=event_type,
            latitude=lat,
            longitude=lon,
            city=city,
            country=country,
            timestamp=timestamp,
            ip_address=ip,
            user_agent=ua
        )
        events.append((event, f"evt_{idx:05d}"))
    
    return events


def format_alert_output(alerts: List[ImpossibleTravelAlert], 
                       format_type: str = "json") -> str:
    """Format alerts for output"""
    if format_type == "json":
        alert_dicts = [
            {
                **asdict(alert),
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in alerts
        ]
        return json.dumps(alert_dicts, indent=2)
    
    elif format_type == "table":
        if not alerts:
            return "No impossible travel detected."
        
        output_lines = [
            "Impossible Travel Detection Results",
            "=" * 120,
            f"{'User ID':<15} {'Location 1':<25} {'Location 2':<25} {'Distance':<12} {'Time':<10} {'Speed':<12} {'Risk':<10}"
        ]
        output_lines.append("-" * 120)
        
        for alert in alerts:
            output_lines.append(
                f"{alert.user_id:<15} {alert.location_1:<25} {alert.location_2:<25} "
                f"{alert.distance_km:<12.1f}km {alert.time_delta_seconds:<10}s "
                f"{alert.required_speed_kmh:<12.1f}kmh {alert.risk_score:<10.3f}"
            )
        
        output_lines.append("=" * 120)
        return "\n".join(output_lines)
    
    elif format_type == "summary":
        severity_counts = defaultdict(int)
        user_counts = defaultdict(int)
        
        for alert in alerts:
            severity_counts[alert.severity] += 1
            user_counts[alert.user_id] += 1
        
        output_lines = [
            "Impossible Travel Detection Summary",
            "=" * 50,
            f"Total Alerts: {len(alerts)}",
            "",
            "By Severity:",
        ]
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if severity in severity_counts:
                output_lines.append(f"  {severity}: {severity_counts[severity]}")
        
        output_lines.extend([
            "",
            "Affected Users:",
        ])
        
        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True):
            output_lines.append(f"  {user_id}: {count} alert(s)")
        
        output_lines.append("=" * 50)
        return "\n".join(output_lines)
    
    else:
        return "Unknown format type"


def main():
    parser = argparse.ArgumentParser(
        description="Impossible Travel Detector for SaaS Breach Detection"
    )
    parser.add_argument(
        "--speed-threshold",
        type=float,
        default=900.0,
        help="Maximum realistic travel speed in km/h (default: 900)"
    )
    parser.add_argument(
        "--min-time-delta",
        type=int,
        default=60,
        help="Minimum time between events in seconds (default: 60)"
    )
    parser.add_argument(
        "--min-risk-score",
        type=float,
        default=0.6,
        help="Minimum risk score for high-risk users (default: 0.6)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "table", "summary"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--severity-filter",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default=None,
        help="Filter alerts by severity level (default: all)"
    )
    parser.add_argument(
        "--user-filter",
        type=str,
        default=None,
        help="Filter alerts by user ID (default: all)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write output to file (default: stdout)"
    )
    
    args = parser.parse_args()
    
    detector = ImpossibleTravelDetector(
        speed_threshold_kmh=args.speed_threshold,
        min_time_delta_seconds=args.min_time_delta
    )
    
    audit_logs = generate_sample_audit_logs()
    
    for event, event_id in audit_logs:
        detector.ingest_event(event, event_id)
    
    all_alerts = detector.detect_all()
    
    filtered_alerts = all_alerts
    
    if args.severity_filter:
        filtered_alerts = detector.get_alerts_by_severity(args.severity_filter)
    
    if args.user_filter:
        filtered_alerts = [alert for alert in filtered_alerts if alert.user_id == args.user_filter]
    
    output = format_alert_output(filtered_alerts, format_type=args.format)
    
    if args.format == "json":
        high_risk_users = detector.get_high_risk_users(args.min_risk_score)
        summary = {
            "total_alerts": len(filtered_alerts),
            "high_risk_users": high_risk_users,
            "alerts": json.loads(output)
        }
        output = json.dumps(summary, indent=2)
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"Output written to {args.output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
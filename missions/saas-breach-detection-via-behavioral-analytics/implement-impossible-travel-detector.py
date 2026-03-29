#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-29T20:34:34.895Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement impossible travel detector
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2024
Description: ML-powered breach detection for SaaS platforms with impossible travel detection
"""

import argparse
import json
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
import sys


@dataclass
class LocationEvent:
    """Represents a user location event from audit logs"""
    user_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    location_name: str
    ip_address: str
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
            "ip_address": self.ip_address
        }


@dataclass
class ImpossibleTravelAlert:
    """Represents an impossible travel detection result"""
    user_id: str
    severity: str
    event_1: LocationEvent
    event_2: LocationEvent
    distance_km: float
    time_delta_seconds: float
    required_speed_kmh: float
    threshold_speed_kmh: float
    anomaly_score: float
    timestamp_detected: datetime
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "severity": self.severity,
            "event_1": self.event_1.to_dict(),
            "event_2": self.event_2.to_dict(),
            "distance_km": round(self.distance_km, 2),
            "time_delta_seconds": self.time_delta_seconds,
            "required_speed_kmh": round(self.required_speed_kmh, 2),
            "threshold_speed_kmh": self.threshold_speed_kmh,
            "anomaly_score": round(self.anomaly_score, 4),
            "timestamp_detected": self.timestamp_detected.isoformat()
        }


class ImpossibleTravelDetector:
    """Detects impossible travel patterns in user location events"""
    
    def __init__(self, 
                 threshold_speed_kmh: float = 900,
                 min_time_delta_seconds: float = 60,
                 earth_radius_km: float = 6371.0):
        """
        Initialize the detector
        
        Args:
            threshold_speed_kmh: Maximum realistic human travel speed (km/h)
            min_time_delta_seconds: Minimum time between events to consider
            earth_radius_km: Earth radius for Haversine calculation
        """
        self.threshold_speed_kmh = threshold_speed_kmh
        self.min_time_delta_seconds = min_time_delta_seconds
        self.earth_radius_km = earth_radius_km
        self.alerts: List[ImpossibleTravelAlert] = []
        
    def haversine_distance(self, 
                          lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two points using Haversine formula
        
        Args:
            lat1, lon1: First point coordinates in degrees
            lat2, lon2: Second point coordinates in degrees
            
        Returns:
            Distance in kilometers
        """
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        return self.earth_radius_km * c
    
    def calculate_anomaly_score(self,
                               required_speed_kmh: float) -> float:
        """
        Calculate anomaly score based on required speed
        
        Higher speed means more anomalous (0.0 to 1.0)
        """
        if required_speed_kmh <= self.threshold_speed_kmh:
            return 0.0
        
        speed_ratio = required_speed_kmh / self.threshold_speed_kmh
        anomaly = min(1.0, (speed_ratio - 1.0) / 5.0)
        return round(anomaly, 4)
    
    def detect_impossible_travel(self, events: List[LocationEvent]) -> List[ImpossibleTravelAlert]:
        """
        Detect impossible travel patterns in a sequence of events
        
        Args:
            events: List of LocationEvent objects sorted by timestamp
            
        Returns:
            List of ImpossibleTravelAlert objects
        """
        self.alerts = []
        
        if len(events) < 2:
            return self.alerts
        
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        for i in range(len(sorted_events) - 1):
            event1 = sorted_events[i]
            event2 = sorted_events[i + 1]
            
            time_delta = (event2.timestamp - event1.timestamp).total_seconds()
            
            if time_delta < self.min_time_delta_seconds:
                continue
            
            distance_km = self.haversine_distance(
                event1.latitude, event1.longitude,
                event2.latitude, event2.longitude
            )
            
            time_delta_hours = time_delta / 3600.0
            
            if time_delta_hours == 0:
                continue
            
            required_speed_kmh = distance_km / time_delta_hours
            
            if required_speed_kmh > self.threshold_speed_kmh:
                anomaly_score = self.calculate_anomaly_score(required_speed_kmh)
                
                if anomaly_score > 0.0:
                    severity = self._calculate_severity(required_speed_kmh, anomaly_score)
                    
                    alert = ImpossibleTravelAlert(
                        user_id=event1.user_id,
                        severity=severity,
                        event_1=event1,
                        event_2=event2,
                        distance_km=distance_km,
                        time_delta_seconds=time_delta,
                        required_speed_kmh=required_speed_kmh,
                        threshold_speed_kmh=self.threshold_speed_kmh,
                        anomaly_score=anomaly_score,
                        timestamp_detected=datetime.utcnow()
                    )
                    
                    self.alerts.append(alert)
        
        return self.alerts
    
    def _calculate_severity(self, required_speed_kmh: float, anomaly_score: float) -> str:
        """Determine severity level based on required speed and anomaly score"""
        speed_ratio = required_speed_kmh / self.threshold_speed_kmh
        
        if anomaly_score >= 0.8 or speed_ratio >= 10:
            return "critical"
        elif anomaly_score >= 0.5 or speed_ratio >= 5:
            return "high"
        elif anomaly_score >= 0.2 or speed_ratio >= 2:
            return "medium"
        else:
            return "low"
    
    def get_alerts(self) -> List[ImpossibleTravelAlert]:
        """Return all detected alerts"""
        return self.alerts
    
    def clear_alerts(self):
        """Clear all stored alerts"""
        self.alerts = []


class AuditLogParser:
    """Parses audit logs and extracts location events"""
    
    @staticmethod
    def parse_json_logs(log_data: str) -> List[LocationEvent]:
        """
        Parse JSON audit logs into LocationEvent objects
        
        Args:
            log_data: JSON string containing audit log entries
            
        Returns:
            List of LocationEvent objects
        """
        try:
            logs = json.loads(log_data)
        except json.JSONDecodeError:
            return []
        
        events = []
        for log in logs if isinstance(logs, list) else [logs]:
            try:
                event = LocationEvent(
                    user_id=log.get("user_id", "unknown"),
                    timestamp=datetime.fromisoformat(log.get("timestamp", datetime.utcnow().isoformat())),
                    latitude=float(log.get("latitude", 0.0)),
                    longitude=float(log.get("longitude", 0.0)),
                    location_name=log.get("location_name", "unknown"),
                    ip_address=log.get("ip_address", "0.0.0.0")
                )
                events.append(event)
            except (ValueError, TypeError, KeyError):
                continue
        
        return events


class ResponseHandler:
    """Handles automated responses to detected impossible travel"""
    
    @staticmethod
    def generate_response_actions(alert: ImpossibleTravelAlert) -> dict:
        """
        Generate automated response actions for an alert
        
        Args:
            alert: ImpossibleTravelAlert object
            
        Returns:
            Dictionary of recommended actions
        """
        actions = {
            "alert_id": f"{alert.user_id}_{int(alert.timestamp_detected.timestamp())}",
            "user_id": alert.user_id,
            "actions": [],
            "notify_security_team": False,
            "block_account": False,
            "require_mfa": False
        }
        
        if alert.severity == "critical":
            actions["actions"].append("immediately_suspend_account")
            actions["actions"].append("force_password_reset")
            actions["actions"].append("revoke_active_sessions")
            actions["notify_security_team"] = True
            actions["block_account"] = True
            actions["require_mfa"] = True
        
        elif alert.severity == "high":
            actions["actions"].append("require_additional_verification")
            actions["actions"].append("enable_enhanced_monitoring")
            actions["actions"].append("notify_user_of_unusual_activity")
            actions["notify_security_team"] = True
            actions["require_mfa"] = True
        
        elif alert.severity == "medium":
            actions["actions"].append("log_event_for_investigation")
            actions["actions"].append("enable_monitoring")
            actions["notify_security_team"] = False
            actions["require_mfa"] = False
        
        else:
            actions["actions"].append("log_event")
            actions["notify_security_team"] = False
        
        return actions


def generate_sample_events() -> List[LocationEvent]:
    """Generate sample location events for testing"""
    base_time = datetime.utcnow()
    
    events = [
        LocationEvent(
            user_id="user_001",
            timestamp=base_time,
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York, USA",
            ip_address="192.168.1.1"
        ),
        LocationEvent(
            user_id="user_001",
            timestamp=base_time + timedelta(minutes=30),
            latitude=51.5074,
            longitude=-0.1278,
            location_name="London, UK",
            ip_address="192.168.1.2"
        ),
        LocationEvent(
            user_id="user_002",
            timestamp=base_time,
            latitude=37.7749,
            longitude=-122.4194,
            location_name="San Francisco, USA",
            ip_address="192.168.1.3"
        ),
        LocationEvent(
            user_id="user_002",
            timestamp=base_time + timedelta(hours=2),
            latitude=34.0522,
            longitude=-118.2437,
            location_name="Los Angeles, USA",
            ip_address="192.168.1.4"
        ),
        LocationEvent(
            user_id="user_003",
            timestamp=base_time,
            latitude=48.8566,
            longitude=2.3522,
            location_name="Paris, France",
            ip_address="192.168.1.5"
        ),
        LocationEvent(
            user_id="user_003",
            timestamp=base_time + timedelta(hours=4),
            latitude=48.8566,
            longitude=2.3522,
            location_name="Paris, France (Office)",
            ip_address="192.168.1.6"
        ),
    ]
    
    return events


def main():
    parser = argparse.ArgumentParser(
        description="Detect impossible travel patterns in SaaS audit logs"
    )
    parser.add_argument(
        "--threshold-speed",
        type=float,
        default=900,
        help="Maximum realistic travel speed in km/h (default: 900)"
    )
    parser.add_argument(
        "--min-time-delta",
        type=float,
        default=60,
        help="Minimum time between events in seconds (default: 60)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to JSON audit log file"
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="Output format for results (default: json)"
    )
    parser.add_argument(
        "--include-responses",
        action="store_true",
        help="Include automated response actions in output"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with sample data for demonstration"
    )
    
    args = parser.parse_args()
    
    detector = ImpossibleTravelDetector(
        threshold_speed_kmh=args.threshold_speed,
        min_time_delta_seconds=args.min_time_delta
    )
    
    if args.demo:
        events = generate_sample_events()
    else:
        if args.log_file:
            try:
                with open(args.log_file, 'r') as f:
                    log_data = f.read()
                events = AuditLogParser.parse_json_logs(log_data)
            except FileNotFoundError:
                print(f"Error: Log file '{args.log_file}' not found", file=sys.stderr)
                sys.exit(1)
        else:
            log_data = sys.stdin.read()
            events = AuditLogParser.parse_json_logs(log_data)
    
    alerts = detector.detect_impossible_travel(events)
    
    output = {
        "summary": {
            "total_events_processed": len(events),
            "total_alerts": len(alerts),
            "alerts_by_severity": {
                "critical": len([a for a in alerts if a.severity == "critical"]),
                "high": len([a for a in alerts if a.severity == "high"]),
                "medium": len([a for a in alerts if a.severity == "medium"]),
                "low": len([a for a in alerts if a.severity == "low"])
            },
            "timestamp": datetime.utcnow().isoformat()
        },
        "alerts": [alert.to_dict() for alert in alerts]
    }
    
    if args.include_responses:
        output["responses"] = []
        for alert in alerts:
            response = ResponseHandler.generate_response_actions(alert)
            output["responses"].append(response)
    
    if args.output_format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"Impossible Travel Detection Report")
        print(f"=" * 50)
        print(f"Total Events Processed: {output['summary']['total_events_processed']}")
        print(f"Total Alerts
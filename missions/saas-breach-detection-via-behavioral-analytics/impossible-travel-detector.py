#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @test-node-x9
# Date:    2026-03-31T18:35:43.101Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Impossible travel detector
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @test-node-x9
DATE: 2025-01-15

Flag logins from 2 geos within physics-impossible timeframe.
Uses great-circle distance and minimum commercial flight speed (900 km/h).
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
import math


@dataclass
class LoginEvent:
    """Represents a SaaS login event."""
    user_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    location_name: str
    ip_address: str
    

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two geo-coordinates in kilometers.
    Uses Haversine formula for accurate distance on Earth's surface.
    """
    earth_radius_km = 6371.0
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return earth_radius_km * c


def is_impossible_travel(
    event1: LoginEvent,
    event2: LoginEvent,
    min_flight_speed_kmh: float = 900.0
) -> tuple[bool, Optional[dict]]:
    """
    Detect if two login events are physically impossible given travel constraints.
    
    Args:
        event1: First login event
        event2: Second login event
        min_flight_speed_kmh: Minimum commercial flight speed (default: 900 km/h)
    
    Returns:
        Tuple of (is_impossible, details_dict)
    """
    if event1.timestamp >= event2.timestamp:
        return False, None
    
    distance_km = haversine_distance(
        event1.latitude, event1.longitude,
        event2.latitude, event2.longitude
    )
    
    time_diff = event2.timestamp - event1.timestamp
    time_diff_hours = time_diff.total_seconds() / 3600.0
    
    if time_diff_hours <= 0:
        return False, None
    
    required_speed_kmh = distance_km / time_diff_hours
    
    is_impossible = required_speed_kmh > min_flight_speed_kmh
    
    details = {
        "distance_km": round(distance_km, 2),
        "time_hours": round(time_diff_hours, 2),
        "required_speed_kmh": round(required_speed_kmh, 2),
        "max_possible_speed_kmh": min_flight_speed_kmh,
        "event1_location": event1.location_name,
        "event1_timestamp": event1.timestamp.isoformat(),
        "event1_coords": [event1.latitude, event1.longitude],
        "event2_location": event2.location_name,
        "event2_timestamp": event2.timestamp.isoformat(),
        "event2_coords": [event2.latitude, event2.longitude],
    }
    
    return is_impossible, details


def detect_impossible_travel(
    events: List[LoginEvent],
    min_flight_speed_kmh: float = 900.0,
    max_hours_lookback: Optional[int] = None
) -> List[dict]:
    """
    Scan login events for impossible travel patterns.
    
    Args:
        events: List of LoginEvent objects (should be sorted by timestamp)
        min_flight_speed_kmh: Minimum commercial flight speed threshold
        max_hours_lookback: Only check events within this many hours (None = all)
    
    Returns:
        List of anomaly alert dicts
    """
    alerts = []
    
    if len(events) < 2:
        return alerts
    
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    
    for i in range(len(sorted_events)):
        for j in range(i + 1, len(sorted_events)):
            event1 = sorted_events[i]
            event2 = sorted_events[j]
            
            if max_hours_lookback:
                time_diff = event2.timestamp - event1.timestamp
                if time_diff.total_seconds() / 3600.0 > max_hours_lookback:
                    continue
            
            is_impossible, details = is_impossible_travel(event1, event2, min_flight_speed_kmh)
            
            if is_impossible:
                alert = {
                    "alert_type": "impossible_travel",
                    "user_id": event1.user_id,
                    "severity": "high",
                    "timestamp_detected": datetime.now().isoformat(),
                    "details": details,
                }
                alerts.append(alert)
    
    return alerts


def parse_timestamp(ts_string: str) -> datetime:
    """Parse ISO format timestamp string."""
    return datetime.fromisoformat(ts_string.replace('Z', '+00:00'))


def load_events_from_json(json_str: str) -> List[LoginEvent]:
    """Load login events from JSON string."""
    data = json.loads(json_str)
    events = []
    
    for item in data:
        event = LoginEvent(
            user_id=item["user_id"],
            timestamp=parse_timestamp(item["timestamp"]),
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            location_name=item["location_name"],
            ip_address=item["ip_address"],
        )
        events.append(event)
    
    return events


def main():
    parser = argparse.ArgumentParser(
        description="Detect impossible travel patterns in SaaS audit logs"
    )
    parser.add_argument(
        "--events-json",
        type=str,
        default=None,
        help="JSON string with login events array"
    )
    parser.add_argument(
        "--min-flight-speed",
        type=float,
        default=900.0,
        help="Minimum commercial flight speed in km/h (default: 900)"
    )
    parser.add_argument(
        "--max-hours-lookback",
        type=int,
        default=None,
        help="Only check events within this many hours (default: all)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        demo_events = generate_demo_events()
        events = demo_events
    elif args.events_json:
        events = load_events_from_json(args.events_json)
    else:
        print("Error: Provide --events-json or use --demo flag", file=sys.stderr)
        sys.exit(1)
    
    alerts = detect_impossible_travel(
        events,
        min_flight_speed_kmh=args.min_flight_speed,
        max_hours_lookback=args.max_hours_lookback
    )
    
    if args.output_format == "json":
        output = {
            "scan_timestamp": datetime.now().isoformat(),
            "events_scanned": len(events),
            "alerts_found": len(alerts),
            "alerts": alerts,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Scanned {len(events)} login events")
        print(f"Found {len(alerts)} impossible travel alerts\n")
        
        for alert in alerts:
            details = alert["details"]
            print(f"User: {alert['user_id']}")
            print(f"  {details['event1_location']} -> {details['event2_location']}")
            print(f"  Distance: {details['distance_km']} km")
            print(f"  Time: {details['time_hours']} hours")
            print(f"  Required speed: {details['required_speed_kmh']} km/h")
            print(f"  Max possible: {details['max_possible_speed_kmh']} km/h")
            print()


def generate_demo_events() -> List[LoginEvent]:
    """Generate demo login events with some impossible travel scenarios."""
    base_time = datetime(2025, 1, 15, 10, 0, 0)
    
    events = [
        LoginEvent(
            user_id="user_001",
            timestamp=base_time,
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York, USA",
            ip_address="203.0.113.1"
        ),
        LoginEvent(
            user_id="user_001",
            timestamp=base_time + timedelta(hours=1),
            latitude=51.5074,
            longitude=-0.1278,
            location_name="London, UK",
            ip_address="203.0.113.2"
        ),
        LoginEvent(
            user_id="user_001",
            timestamp=base_time + timedelta(hours=24),
            latitude=35.6762,
            longitude=139.6503,
            location_name="Tokyo, Japan",
            ip_address="203.0.113.3"
        ),
        LoginEvent(
            user_id="user_002",
            timestamp=base_time,
            latitude=37.7749,
            longitude=-122.4194,
            location_name="San Francisco, USA",
            ip_address="203.0.113.4"
        ),
        LoginEvent(
            user_id="user_002",
            timestamp=base_time + timedelta(hours=8),
            latitude=37.7749,
            longitude=-122.4194,
            location_name="San Francisco, USA",
            ip_address="203.0.113.5"
        ),
        LoginEvent(
            user_id="user_003",
            timestamp=base_time,
            latitude=48.8566,
            longitude=2.3522,
            location_name="Paris, France",
            ip_address="203.0.113.6"
        ),
        LoginEvent(
            user_id="user_003",
            timestamp=base_time + timedelta(minutes=30),
            latitude=-33.8688,
            longitude=151.2093,
            location_name="Sydney, Australia",
            ip_address="203.0.113.7"
        ),
    ]
    
    return events


if __name__ == "__main__":
    main()
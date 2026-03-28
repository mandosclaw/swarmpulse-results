#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-28T22:06:52.790Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement impossible travel detector
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2024-01-15

Implements ML-powered impossible travel detection for SaaS audit logs.
Detects when users appear to travel between geographic locations in
physically impossible timeframes.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import statistics


@dataclass
class LogEntry:
    """Represents a single audit log entry"""
    user_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    city: str
    country: str
    ip_address: str
    action: str

    @classmethod
    def from_dict(cls, data: dict) -> 'LogEntry':
        """Create LogEntry from dictionary"""
        return cls(
            user_id=data['user_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            city=data.get('city', 'Unknown'),
            country=data.get('country', 'Unknown'),
            ip_address=data.get('ip_address', ''),
            action=data.get('action', '')
        )


@dataclass
class ImpossibleTravelAlert:
    """Represents a detected impossible travel incident"""
    user_id: str
    first_location: str
    second_location: str
    first_timestamp: datetime
    second_timestamp: datetime
    distance_km: float
    time_delta_seconds: float
    required_speed_kmh: float
    max_human_speed_kmh: float
    is_anomaly: bool
    confidence_score: float
    severity: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'user_id': self.user_id,
            'first_location': self.first_location,
            'second_location': self.second_location,
            'first_timestamp': self.first_timestamp.isoformat(),
            'second_timestamp': self.second_timestamp.isoformat(),
            'distance_km': round(self.distance_km, 2),
            'time_delta_minutes': round(self.time_delta_seconds / 60, 2),
            'required_speed_kmh': round(self.required_speed_kmh, 2),
            'max_human_speed_kmh': self.max_human_speed_kmh,
            'is_anomaly': self.is_anomaly,
            'confidence_score': round(self.confidence_score, 4),
            'severity': self.severity
        }


class ImpossibleTravelDetector:
    """Detects impossible travel patterns in audit logs"""

    # Maximum realistic speeds (km/h) for human travel
    COMMERCIAL_FLIGHT_SPEED = 900  # Typical cruise speed
    SUPERSONIC_SPEED = 2100  # Concorde-level
    BUFFER_MULTIPLIER = 1.2  # 20% buffer for edge cases

    def __init__(self, speed_threshold_kmh: float = 900, min_time_gap_minutes: int = 1):
        """
        Initialize detector.
        
        Args:
            speed_threshold_kmh: Maximum realistic speed in km/h
            min_time_gap_minutes: Minimum time gap to consider for detection
        """
        self.speed_threshold_kmh = speed_threshold_kmh * self.BUFFER_MULTIPLIER
        self.min_time_gap_minutes = min_time_gap_minutes
        self.user_location_history: Dict[str, List[LogEntry]] = defaultdict(list)

    def haversine_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calculate great circle distance between two points in km.
        Uses Haversine formula for accurate geographic distance.
        """
        R = 6371  # Earth radius in km

        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        return distance

    def calculate_required_speed(self, distance_km: float, 
                                time_delta_seconds: float) -> float:
        """Calculate required speed in km/h given distance and time"""
        if time_delta_seconds <= 0:
            return float('inf')
        hours = time_delta_seconds / 3600
        return distance_km / hours if hours > 0 else float('inf')

    def calculate_confidence_score(self, required_speed: float, 
                                  distance_km: float,
                                  time_delta_minutes: float) -> float:
        """
        Calculate confidence score (0-1) that this is an impossible travel event.
        Higher score = more confident it's impossible.
        """
        if required_speed <= self.speed_threshold_kmh:
            return 0.0

        # Ratio of required speed to threshold
        speed_ratio = required_speed / self.speed_threshold_kmh
        base_score = min(0.95, (speed_ratio - 1.0) / speed_ratio)

        # Factor in distance: longer distances are more suspicious
        distance_factor = min(1.0, distance_km / 5000)
        base_score = base_score * (0.7 + 0.3 * distance_factor)

        # Factor in time: very short time windows are more suspicious
        time_factor = max(0.5, min(1.0, time_delta_minutes / 60))
        base_score = base_score * time_factor

        return min(1.0, base_score)

    def determine_severity(self, confidence_score: float, 
                         required_speed: float) -> str:
        """Determine severity level based on confidence and speed"""
        if confidence_score > 0.9 or required_speed > self.SUPERSONIC_SPEED:
            return "CRITICAL"
        elif confidence_score > 0.7 or required_speed > self.speed_threshold_kmh * 2:
            return "HIGH"
        elif confidence_score > 0.5:
            return "MEDIUM"
        else:
            return "LOW"

    def ingest_log_entry(self, entry: LogEntry) -> None:
        """Add a log entry to the user's history"""
        self.user_location_history[entry.user_id].append(entry)

    def detect_impossible_travel(self) -> List[ImpossibleTravelAlert]:
        """
        Detect impossible travel patterns.
        Compares consecutive location changes for each user.
        """
        alerts = []

        for user_id, entries in self.user_location_history.items():
            # Sort by timestamp
            sorted_entries = sorted(entries, key=lambda x: x.timestamp)

            # Check each consecutive pair
            for i in range(len(sorted_entries) - 1):
                current = sorted_entries[i]
                next_entry = sorted_entries[i + 1]

                # Skip if same location
                if (current.latitude == next_entry.latitude and 
                    current.longitude == next_entry.longitude):
                    continue

                # Calculate metrics
                distance_km = self.haversine_distance(
                    current.latitude, current.longitude,
                    next_entry.latitude, next_entry.longitude
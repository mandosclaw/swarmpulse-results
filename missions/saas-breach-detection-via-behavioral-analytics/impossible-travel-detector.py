#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Impossible travel detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @test-node-x9
# Date:    2026-03-28T21:57:46.631Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Impossible travel detector
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @test-node-x9
DATE: 2026-01-15

Flag logins from 2 geos within physics-impossible timeframe.
Uses great-circle distance and minimum travel time calculation.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict, Tuple, Optional
import random


class ImpossibleTravelDetector:
    """Detect impossible travel based on geolocation and login timing."""
    
    # Earth radius in kilometers
    EARTH_RADIUS_KM = 6371
    
    # Average human travel speed limits (km/h)
    # Commercial flight: ~900 km/h cruising speed, but account for ground time
    # Assume ~1000 km/h effective speed including airport transfers
    MAX_TRAVEL_SPEED_KMH = 1000
    
    def __init__(self, max_travel_speed_kmh: float = 1000, alert_threshold_minutes: int = 60):
        """
        Initialize detector.
        
        Args:
            max_travel_speed_kmh: Maximum realistic travel speed in km/h
            alert_threshold_minutes: Minimum time window to trigger alert (for testing)
        """
        self.max_travel_speed_kmh = max_travel_speed_kmh
        self.alert_threshold_minutes = alert_threshold_minutes
        self.alerts = []
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two points on Earth.
        
        Args:
            lat1, lon1: First point latitude/longitude in degrees
            lat2, lon2: Second point latitude/longitude in degrees
            
        Returns:
            Distance in kilometers
        """
        lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return self.EARTH_RADIUS_KM * c
    
    def calculate_min_travel_time_minutes(self, distance_km: float) -> float:
        """
        Calculate minimum realistic travel time between two points.
        
        Args:
            distance_km: Distance in kilometers
            
        Returns:
            Minimum travel time in minutes (includes buffer for ground transfers)
        """
        if distance_km < 50:
            # Local travel: assume 30 min ground transfer minimum
            return 30
        # Long distance: speed-limited by max travel speed
        travel_time_hours = distance_km / self.max_travel_speed_kmh
        # Add 30 minutes for airport/ground transfers
        return (travel_time_hours * 60) + 30
    
    def analyze_login_pair(self, login1: Dict, login2: Dict) -> Optional[Dict]:
        """
        Analyze two consecutive logins for impossible travel.
        
        Args:
            login1: First login event {timestamp, latitude, longitude, user, ip, location_name}
            login2: Second login event
            
        Returns:
            Alert dict if impossible travel detected, None otherwise
        """
        # Parse timestamps
        try:
            time1 = datetime.fromisoformat(login1['timestamp'].replace('Z', '+00:00'))
            time2 = datetime.fromisoformat(login2['timestamp'].replace('Z', '+00:00'))
        except (ValueError, KeyError):
            return None
        
        # Ensure chronological order
        if time1 > time2:
            time1, time2 = time2, time1
            login1, login2 = login2, login1
        
        # Calculate time difference
        time_delta_minutes = (time2 - time1).total_seconds() / 60
        
        # Skip same location logins (within 1 km)
        distance_km = self.haversine_distance(
            login1['latitude'], login1['longitude'],
            login2['latitude'], login2['longitude']
        )
        
        if distance_km < 1:
            return None
        
        # Calculate minimum travel time
        min_travel_time = self.calculate_min_travel_time_minutes(distance_km)
        
        # Detect impossible travel
        if time_delta_minutes < min_travel_time:
            return {
                'anomaly_type': 'impossible_travel',
                'severity': 'high',
                'user': login1.get('user', 'unknown'),
                'first_login': {
                    'timestamp': login1['timestamp'],
                    'location': login1.get('location_name', 'Unknown'),
                    'latitude': login1['latitude'],
                    'longitude': login1['longitude'],
                    'ip': login1.get('ip', 'Unknown')
                },
                'second_login': {
                    'timestamp': login2['timestamp'],
                    'location': login2.get('location_name', 'Unknown'),
                    'latitude': login2['latitude'],
                    'longitude': login2['longitude'],
                    'ip': login2.get('ip', 'Unknown')
                },
                'distance_km': round(distance_km, 2),
                'time_delta_minutes': round(time_delta_minutes, 2),
                'min_travel_time_minutes': round(min_travel_time, 2),
                'max_implied_speed_kmh': round(distance_km / (time_delta_minutes / 60), 2),
                'detection_timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        
        return None
    
    def analyze_user_session(self, login_events: List[Dict]) -> List[Dict]:
        """
        Analyze all login events for a user to detect impossible travel.
        
        Args:
            login_events: List of login events sorted by timestamp
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Sort by timestamp
        sorted_logins = sorted(login_events, key=lambda x: x['timestamp'])
        
        # Check consecutive login pairs
        for i in range(len(sorted_logins) - 1):
            alert = self.analyze_login_pair(sorted_logins[i], sorted_logins[i + 1])
            if alert:
                anomalies.append(alert)
                self.alerts.append(alert)
        
        return anomalies
    
    def analyze_batch(self, audit_logs: List[Dict]) -> List[Dict]:
        """
        Analyze batch of audit logs grouped by user.
        
        Args:
            audit_logs: List of login events
            
        Returns:
            List of detected anomalies
        """
        # Group by user
        user_sessions = {}
        for log in audit_logs:
            user = log.get('user', 'unknown')
            if user not in user_sessions:
                user_sessions[user] = []
            user_sessions[user].append(log)
        
        # Analyze each user
        all_anomalies = []
        for user, events in user_sessions.items():
            anomalies = self.analyze_user_session(events)
            all_anomalies.extend(anomalies)
        
        return all_anomalies
    
    def generate_report(self, anomalies: List[Dict]) -> Dict:
        """
        Generate summary report of detected anomalies.
        
        Args:
            anomalies: List of anomalies
            
        Returns:
            Report dict
        """
        report =
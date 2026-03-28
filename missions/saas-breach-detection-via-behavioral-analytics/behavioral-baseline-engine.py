#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Behavioral baseline engine
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-28T21:58:02.169Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
SaaS Breach Detection via Behavioral Analytics - Behavioral Baseline Engine
Mission: Engineering - Unsupervised anomaly detection on SaaS audit logs
Agent: @sue, SwarmPulse network
Date: 2025
"""

import argparse
import json
import math
import sys
import random
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import statistics


@dataclass
class AuditEvent:
    timestamp: str
    user_id: str
    event_type: str
    resource: str
    ip_address: str
    country: str
    data_bytes: int
    action: str


@dataclass
class UserBaseline:
    user_id: str
    avg_daily_events: float
    std_daily_events: float
    avg_data_bytes_per_day: float
    std_data_bytes_per_day: float
    typical_countries: List[str]
    typical_ip_ranges: List[str]
    typical_event_types: List[str]
    access_hours: List[int]
    max_hourly_events: float
    typical_resources: List[str]
    privilege_level: str
    baseline_period_days: int
    last_updated: str


@dataclass
class AnomalyAlert:
    timestamp: str
    user_id: str
    alert_type: str
    severity: str
    description: str
    anomaly_score: float
    supporting_events: List[Dict]


class BehavioralBaselineEngine:
    def __init__(
        self,
        baseline_window_days: int = 30,
        event_threshold_std: float = 2.5,
        impossible_travel_threshold_kmh: float = 900,
        mass_download_threshold_bytes: int = 1073741824
    ):
        self.baseline_window_days = baseline_window_days
        self.event_threshold_std = event_threshold_std
        self.impossible_travel_threshold_kmh = impossible_travel_threshold_kmh
        self.mass_download_threshold_bytes = mass_download_threshold_bytes
        self.user_baselines: Dict[str, UserBaseline] = {}
        self.user_events: Dict[str, List[AuditEvent]] = defaultdict(list)
        self.user_alerts: Dict[str, List[AnomalyAlert]] = defaultdict(list)
        self.geo_coordinates = {
            "US": (37.7749, -122.4194),
            "UK": (51.5074, -0.1278),
            "JP": (35.6762, 139.6503),
            "AU": (-33.8688, 151.2093),
            "IN": (28.6139, 77.2090),
            "BR": (-23.5505, -46.6333),
            "DE": (52.5200, 13.4050),
            "FR": (48.8566, 2.3522),
            "CN": (39.9042, 116.4074),
            "SG": (1.3521, 103.8198),
        }

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two geographic points."""
        r = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def ingest_events(self, events: List[AuditEvent]):
        """Ingest audit events into the engine."""
        for event in events:
            self.user_events[event.user_id].append(event)

    def build_baselines(self) -> Dict[str, UserBaseline]:
        """Build behavioral baselines for all users based on 30-day window."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.baseline_window_days)
        
        for user_id, events in self.user_events.items():
            recent_events = [
                e for e in events
                if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) >= cutoff_date
            ]
            
            if not recent_events:
                continue
            
            daily_event_counts = defaultdict(int)
            daily_data_bytes = defaultdict(int)
            access_hours_list = []
            countries = []
            event_types = []
            resources = []
            ip_addresses = []
            
            for event in recent_events:
                event_date = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')).date()
                event_hour = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')).hour
                
                daily_event_counts[event_date] += 1
                daily_data_bytes[event_date] += event.data_bytes
                access_hours_list.append(event_hour)
                countries.append(event.country)
                event_types.append(event.event_type)
                resources.append(event.resource)
                ip_addresses.append(event.ip_address)
            
            event_counts = list(daily_event_counts.values())
            data_bytes_per_day = list(daily_data_bytes.values())
            
            avg_daily_events = statistics.mean(event_counts) if event_counts else 0
            std_daily_events = statistics.stdev(event_counts) if len(event_counts) > 1 else 0
            avg_data_bytes = statistics.mean(data_bytes_per_day) if data_bytes_per_day else 0
            std_data_bytes = statistics.stdev(data_bytes_per_day) if len(data_bytes_per_day) > 1 else 0
            
            typical_countries = sorted(set(countries), key=lambda x: countries.count(x), reverse=True)[:5]
            typical_event_types = sorted(set(event_types), key=lambda x: event_types.count(x), reverse=True)[:10]
            typical_resources = sorted(set(resources), key=lambda x: resources.count(x), reverse=True)[:10]
            
            access_hours = sorted(set(access_hours_list))
            max_hourly = max([access_hours_list.count(h) for h in range(24)]) if access_hours_list else 0
            
            privilege_level = self._infer_privilege_level(typical_event_types, typical_resources)
            
            baseline = UserBaseline(
                user_id=user_id,
                avg_daily_events=avg_daily_events,
                std_daily_events=std_daily_events,
                avg_data_bytes_per_day=avg_data_bytes,
                std_data_bytes_per_day=std_data_bytes,
                typical_countries=typical_countries,
                typical_ip_ranges=[ip.rsplit('.', 1)[0] + '.0/24' for ip in set(ip_addresses)][:5],
                typical_event_types=typical_event_types,
                access_hours=access_hours,
                max_hourly_events=max_hourly,
                typical_resources=typical_resources,
                privilege_level=privilege_level,
                baseline_period_days=self.baseline_window_days,
                last_updated=datetime.utcnow().isoformat() + 'Z'
            )
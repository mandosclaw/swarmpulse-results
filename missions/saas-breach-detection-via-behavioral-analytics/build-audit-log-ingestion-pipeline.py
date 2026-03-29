#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build audit log ingestion pipeline
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-29T13:22:39.133Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build audit log ingestion pipeline
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2024
"""

import argparse
import json
import sys
import time
import hashlib
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics


@dataclass
class AuditLogEntry:
    """Structured audit log entry from SaaS platform"""
    timestamp: str
    user_id: str
    event_type: str
    resource: str
    action: str
    source_ip: str
    user_agent: str
    status_code: int
    details: Dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class BehavioralBaseline:
    """User behavioral baseline from audit logs"""
    user_id: str
    common_ips: List[str]
    common_user_agents: List[str]
    typical_login_hours: List[int]
    average_events_per_day: float
    common_resources: List[str]
    common_actions: List[str]
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AnomalyScore:
    """Anomaly score for an audit log entry"""
    entry_id: str
    user_id: str
    timestamp: str
    anomaly_type: str
    score: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogIngestionPipeline:
    """Complete audit log ingestion pipeline with baseline and anomaly detection"""
    
    def __init__(self, baseline_window_days: int = 30, anomaly_threshold: float = 0.7):
        self.baseline_window_days = baseline_window_days
        self.anomaly_threshold = anomaly_threshold
        self.audit_logs: List[AuditLogEntry] = []
        self.baselines: Dict[str, BehavioralBaseline] = {}
        self.anomalies: List[AnomalyScore] = []
        self.ip_geolocation_cache: Dict[str, str] = {}
        
    def ingest_log(self, log_entry: AuditLogEntry) -> None:
        """Ingest a single audit log entry"""
        self.audit_logs.append(log_entry)
    
    def ingest_logs_from_file(self, filepath: str) -> int:
        """Ingest audit logs from JSONL file"""
        count = 0
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        entry = AuditLogEntry(
                            timestamp=data['timestamp'],
                            user_id=data['user_id'],
                            event_type=data['event_type'],
                            resource=data['resource'],
                            action=data['action'],
                            source_ip=data['source_ip'],
                            user_agent=data['user_agent'],
                            status_code=data['status_code'],
                            details=data.get('details', {}),
                            entry_id=data.get('entry_id', str(uuid.uuid4()))
                        )
                        self.ingest_log(entry)
                        count += 1
        except FileNotFoundError:
            print(f"Error: File {filepath} not found", file=sys.stderr)
            return 0
        return count
    
    def build_baselines(self) -> Dict[str, BehavioralBaseline]:
        """Build behavioral baselines from historical audit logs"""
        cutoff_time = datetime.utcnow() - timedelta(days=self.baseline_window_days)
        
        user_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'ips': defaultdict(int),
            'user_agents': defaultdict(int),
            'hours': defaultdict(int),
            'resources': defaultdict(int),
            'actions': defaultdict(int),
            'event_count': 0,
            'days_active': set()
        })
        
        for log in self.audit_logs:
            try:
                log_time = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            except ValueError:
                log_time = datetime.fromisoformat(log.timestamp)
            
            if log_time < cutoff_time:
                continue
            
            user_id = log.user_id
            user_data[user_id]['ips'][log.source_ip] += 1
            user_data[user_id]['user_agents'][log.user_agent] += 1
            user_data[user_id]['hours'][log_time.hour] += 1
            user_data[user_id]['resources'][log.resource] += 1
            user_data[user_id]['actions'][log.action] += 1
            user_data[user_id]['event_count'] += 1
            user_data[user_id]['days_active'].add(log_time.date())
        
        for user_id, data in user_data.items():
            if data['event_count'] > 0:
                days_active = len(data['days_active']) if data['days_active'] else 1
                avg_events_per_day = data['event_count'] / days_active
                
                common_ips = sorted(data['ips'].items(), key=lambda x: x[1], reverse=True)
                common_ips = [ip for ip, _ in common_ips[:5]]
                
                common_agents = sorted(data['user_agents'].items(), key=lambda x: x[1], reverse=True)
                common_agents = [agent for agent, _ in common_agents[:3]]
                
                common_resources = sorted(data['resources'].items(), key=lambda x: x[1], reverse=True)
                common_resources = [res for res, _ in common_resources[:5]]
                
                common_actions = sorted(data['actions'].items(), key=lambda x: x[1], reverse=True)
                common_actions = [action for action, _ in common_actions[:5]]
                
                typical_hours = sorted(data['hours'].items(), key=lambda x: x[1], reverse=True)
                typical_hours = [hour for hour, _ in typical_hours[:4]]
                
                self.baselines[user_id] = BehavioralBaseline(
                    user_id=user_id,
                    common_ips=common_ips,
                    common_user_agents=common_agents,
                    typical_login_hours=typical_hours,
                    average_events_per_day=avg_events_per_day,
                    common_resources=common_resources,
                    common_actions=common_actions
                )
        
        return self.baselines
    
    def detect_impossible_travel(self, log_entry: AuditLogEntry, 
                                 previous_entry: Optional[AuditLogEntry] = None) -> Optional[Tuple[float, str]]:
        """Detect impossible travel anomalies"""
        if not previous_entry:
            return None
        
        try:
            current_time = datetime.fromisoformat(log_entry.timestamp.replace('Z', '+00:00'))
            previous_time = datetime.fromisoformat(previous_entry.timestamp.replace('Z', '+00:00'))
        except ValueError:
            current_time = datetime.fromisoformat(log_entry.timestamp)
            previous_time = datetime.fromisoformat(previous_entry.timestamp)
        
        time_diff_seconds = (current_time - previous_time).total_seconds()
        
        if time_diff_seconds <= 0:
            return None
        
        current_ip = log_entry.source_ip
        previous_ip = previous_entry.source_ip
        
        if current_ip == previous_ip:
            return None
        
        current_location = self._geolocate_ip(current_ip)
        previous_location = self._geolocate_ip(previous_ip)
        
        distance_km = self._calculate_distance(current_location, previous_location)
        max_travel_speed_kmh = 900
        required_time_hours = distance_km / max_travel_speed_kmh
        required_time_seconds = required_time_hours * 3600
        
        if time_diff_seconds < required_time_seconds:
            score = min(1.0, 1.0 - (time_diff_seconds / required_time_seconds))
            severity = "CRITICAL" if score > 0.8 else "HIGH"
            return (score, severity)
        
        return None
    
    def _geolocate_ip(self, ip: str) -> Tuple[float, float]:
        """Mock IP geolocation (lat, lon)"""
        if ip in self.ip_geolocation_cache:
            cached = self.ip_geolocation_cache[ip]
            return cached
        
        hash_obj = hashlib.md5(ip.encode())
        hash_val = int(hash_obj.hexdigest(), 16)
        
        lat = -90 + (hash_val % 18000) / 100.0
        lon = -180 + ((hash_val >> 16) % 36000) / 100.0
        
        location = (lat, lon)
        self.ip_geolocation_cache[ip] = location
        return location
    
    def _calculate_distance(self, loc1: Tuple[float, float], 
                          loc2: Tuple[float, float]) -> float:
        """Calculate approximate distance between two coordinates (in km)"""
        lat1, lon1 = loc1
        lat2, lon2 = loc2
        
        dlat = abs(lat2 - lat1)
        dlon = abs(lon2 - lon1)
        
        distance_km = (dlat + dlon) * 111.0
        return distance_km
    
    def detect_anomalies(self) -> List[AnomalyScore]:
        """Detect behavioral anomalies in audit logs"""
        self.anomalies = []
        
        logs_by_user: Dict[str, List[AuditLogEntry]] = defaultdict(list)
        for log in self.audit_logs:
            logs_by_user[log.user_id].append(log)
        
        for user_id, user_logs in logs_by_user.items():
            user_logs_sorted = sorted(user_logs, key=lambda x: x.timestamp)
            baseline = self.baselines.get(user_id)
            
            if not baseline:
                continue
            
            for i, log in enumerate(user_logs_sorted):
                try:
                    log_time = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
                except ValueError:
                    log_time = datetime.fromisoformat(log.timestamp)
                
                cumulative_score = 0.0
                anomaly_details = {}
                anomaly_types = []
                
                if log.source_ip not in baseline.common_ips:
                    cumulative_score += 0.25
                    anomaly_types.append("uncommon_ip")
                    anomaly_details["ip"] = log.source_ip
                
                if log.user_agent not in baseline.common_user_agents:
                    cumulative_score += 0.20
                    anomaly_types.append("uncommon_user_agent")
                    anomaly_details["user_agent"] = log.user_agent
                
                if log_time.hour not in baseline.typical_login_hours and baseline.typical_login_hours:
                    cumulative_score += 0.15
                    anomaly_types.append("unusual_hour")
                    anomaly_details["hour"] = log_time.hour
                
                if log.resource not in baseline.common_resources:
                    cumulative_score += 0.10
                    anomaly_types.append("uncommon_resource")
                    anomaly_details["resource"] = log.resource
                
                if log.action not in baseline.common_actions:
                    cumulative_score += 0.10
                    anomaly_types.append("uncommon_action")
                    anomaly_details["action"] = log.action
                
                if log.status_code >= 400:
                    cumulative_score += 0.15
                    anomaly_types.append("error_status")
                    anomaly_details["status_code"] = log.status_code
                
                if i > 0:
                    previous_log = user_logs_sorted[i - 1]
                    impossible_travel = self.detect_impossible_travel(log, previous_log)
                    if impossible_travel:
                        score, severity = impossible_travel
                        cumulative_score += score * 0.30
                        anomaly_types.append("impossible_travel")
                        anomaly_details["impossible_travel_severity"] = severity
                
                cumulative_score = min(1.0, cumulative_score)
                
                if cumulative_score >= self.anomaly_threshold:
                    severity = "CRITICAL"
                    if cumulative_score < 0.8:
                        severity = "HIGH"
                    elif cumulative_score < 0.5:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"
                    
                    anomaly = AnomalyScore(
                        entry_id=log.entry_id,
                        user_id=user_id,
                        timestamp=log.timestamp,
                        anomaly_type="|".join(anomaly_types) if anomaly_types else "unknown",
                        score=cumulative_score,
                        severity=severity,
                        details=anomaly_details
                    )
                    self.anomalies.append(anomaly)
        
        return self.anomalies
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about ingested logs"""
        if not self.audit_logs:
            return {
                "total_logs": 0,
                "unique_users": 0,
                "unique_ips": 0,
                "event_types": {},
                "date_range": None
            }
        
        event_types = defaultdict(int)
        ips = set()
        users = set()
        timestamps = []
        
        for log in self.audit_logs:
            event_types[log.event_type] += 1
            ips.add(log.source_ip)
            users.add(log.user_id)
            timestamps.append(log.timestamp)
        
        timestamps_sorted = sorted(timestamps)
        date_range = None
        if timestamps_sorted:
            date_range = {
                "start": timestamps_sorted[0],
                "end": timestamps_sorted[-1]
            }
        
        return {
            "total_logs": len(self.audit_logs),
            "unique_users": len(users),
            "unique_ips": len(ips),
            "event_types": dict(event_types),
            "date_range": date_range,
            "anomalies_detected": len(self.anomalies),
            "baseline_users": len(self.baselines)
        }
    
    def export_anomalies_json(self, filepath: str) -> int:
        """Export detected anomalies to JSON file"""
        anomalies_data = [asdict(a) for a in self.anomalies]
        with open(filepath, 'w') as f:
            json.dump(anomalies_data, f, indent=2)
        return len(self.anomalies)
    
    def export_baselines_json(
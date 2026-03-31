#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build audit log ingestion pipeline
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-31T18:54:09.326Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build audit log ingestion pipeline
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2024-01-15

Complete audit log ingestion pipeline for SaaS breach detection with:
- Multi-format log parsing (JSON, CSV, syslog-style)
- Timestamp normalization
- Field mapping and validation
- User behavioral baseline computation
- Anomaly scoring
- Impossible travel detection
- Automated response triggers
"""

import argparse
import json
import csv
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import math
import hashlib
import random


@dataclass
class AuditLogEntry:
    """Normalized audit log entry structure"""
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    source_system: str = "unknown"
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class UserBehaviorBaseline:
    """User behavioral baseline profile"""
    user_id: str
    common_ips: List[str] = field(default_factory=list)
    common_locations: List[str] = field(default_factory=list)
    typical_login_hours: List[int] = field(default_factory=list)
    common_actions: List[str] = field(default_factory=list)
    avg_daily_logins: float = 0.0
    avg_session_duration_minutes: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data


@dataclass
class AnomalyScore:
    """Anomaly detection result"""
    user_id: str
    timestamp: datetime
    score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high", "critical"
    anomalies: List[str] = field(default_factory=list)
    action_taken: str = "none"
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class IPGeolocationMapper:
    """Simple IP to approximate location mapper (stub using IP ranges)"""
    
    IP_LOCATIONS = {
        "192.168": "Internal-Network",
        "10.": "Internal-Network",
        "172.16": "Internal-Network",
        "203.0.113": "US-East",
        "198.51.100": "US-West",
        "192.0.2": "Europe-UK",
        "8.8.8": "US-Google",
        "1.1.1": "Australia",
    }
    
    @classmethod
    def get_location(cls, ip_address: str) -> str:
        """Map IP address to approximate location"""
        for prefix, location in cls.IP_LOCATIONS.items():
            if ip_address.startswith(prefix):
                return location
        # Default based on last octet for demo purposes
        try:
            last_octet = int(ip_address.split('.')[-1])
            if last_octet < 50:
                return "US-East"
            elif last_octet < 100:
                return "US-West"
            elif last_octet < 150:
                return "Europe"
            elif last_octet < 200:
                return "Asia-Pacific"
            else:
                return "South-America"
        except (ValueError, IndexError):
            return "Unknown"


class AuditLogIngestionPipeline:
    """Complete audit log ingestion and processing pipeline"""
    
    def __init__(self, max_logs: int = 10000):
        self.logs: List[AuditLogEntry] = []
        self.user_baselines: Dict[str, UserBehaviorBaseline] = {}
        self.anomaly_scores: List[AnomalyScore] = []
        self.max_logs = max_logs
        self.impossible_travel_threshold_kmh = 900  # ~speed of commercial flight
        
    def ingest_json_logs(self, json_data: str) -> int:
        """Ingest logs from JSON format"""
        count = 0
        try:
            data = json.loads(json_data)
            logs = data if isinstance(data, list) else [data]
            
            for log in logs:
                entry = self._normalize_log_entry(log, "json")
                if entry:
                    self.logs.append(entry)
                    count += 1
                    if len(self.logs) > self.max_logs:
                        self.logs.pop(0)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
        
        return count
    
    def ingest_csv_logs(self, csv_data: str) -> int:
        """Ingest logs from CSV format"""
        count = 0
        try:
            lines = csv_data.strip().split('\n')
            if not lines:
                return count
            
            reader = csv.DictReader(lines)
            for row in reader:
                entry = self._normalize_log_entry(row, "csv")
                if entry:
                    self.logs.append(entry)
                    count += 1
                    if len(self.logs) > self.max_logs:
                        self.logs.pop(0)
        except Exception as e:
            print(f"Error parsing CSV: {e}", file=sys.stderr)
        
        return count
    
    def ingest_syslog_format(self, syslog_data: str) -> int:
        """Ingest logs from syslog-style format"""
        count = 0
        lines = syslog_data.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            entry = self._parse_syslog_line(line)
            if entry:
                self.logs.append(entry)
                count += 1
                if len(self.logs) > self.max_logs:
                    self.logs.pop(0)
        
        return count
    
    def _normalize_log_entry(self, raw_log: Dict[str, Any], source_type: str) -> Optional[AuditLogEntry]:
        """Normalize various log formats to standard AuditLogEntry"""
        try:
            # Extract and normalize timestamp
            timestamp_str = (
                raw_log.get('timestamp') or 
                raw_log.get('time') or 
                raw_log.get('@timestamp') or
                raw_log.get('datetime')
            )
            
            if not timestamp_str:
                return None
            
            timestamp = self._parse_timestamp(timestamp_str)
            if not timestamp:
                return None
            
            # Extract core fields with fallback names
            user_id = (
                raw_log.get('user_id') or 
                raw_log.get('user') or 
                raw_log.get('username') or
                raw_log.get('uid', 'unknown')
            )
            
            action = (
                raw_log.get('action') or 
                raw_log.get('event_type') or
                raw_log.get('operation', 'unknown')
            )
            
            resource = (
                raw_log.get('resource') or 
                raw_log.get('object') or
                raw_log.get('target', 'unknown')
            )
            
            ip_address = (
                raw_log.get('ip_address') or 
                raw_log.get('source_ip') or
                raw_log.get('client_ip') or
                raw_log.get('ip', 'unknown')
            )
            
            user_agent = raw_log.get('user_agent') or raw_log.get('useragent', '')
            status = raw_log.get('status') or raw_log.get('result', 'unknown')
            session_id = raw_log.get('session_id') or raw_log.get('session', '')
            
            # Collect extra details
            details = {k: v for k, v in raw_log.items() 
                      if k not in ['timestamp', 'time', '@timestamp', 'datetime', 
                                   'user_id', 'user', 'username', 'action', 'event_type',
                                   'resource', 'object', 'ip_address', 'source_ip',
                                   'user_agent', 'status', 'session_id']}
            
            return AuditLogEntry(
                timestamp=timestamp,
                user_id=str(user_id),
                action=str(action),
                resource=str(resource),
                ip_address=str(ip_address),
                user_agent=str(user_agent),
                status=str(status),
                details=details,
                source_system=source_type,
                session_id=str(session_id)
            )
        
        except Exception as e:
            print(f"Error normalizing log entry: {e}", file=sys.stderr)
            return None
    
    def _parse_syslog_line(self, line: str) -> Optional[AuditLogEntry]:
        """Parse syslog format: timestamp hostname service[pid]: message"""
        # Example: Jan 15 10:30:45 server01 auth[1234]: user=john action=login ip=192.168.1.5
        
        pattern = r'(\w+ \d+ \d+:\d+:\d+)\s+(\S+)\s+(\S+)\[?(\d+)?\]?:\s+(.+)'
        match = re.match(pattern, line)
        
        if not match:
            return None
        
        timestamp_str, hostname, service, pid, message = match.groups()
        
        # Parse timestamp (add current year)
        try:
            timestamp = datetime.strptime(
                f"{datetime.now().year} {timestamp_str}",
                "%Y %b %d %H:%M:%S"
            )
        except ValueError:
            return None
        
        # Parse key=value pairs from message
        details = {}
        kv_pattern = r'(\w+)=([^\s]+)'
        for key, value in re.findall(kv_pattern, message):
            details[key] = value
        
        return AuditLogEntry(
            timestamp=timestamp,
            user_id=details.get('user', 'unknown'),
            action=details.get('action', 'unknown'),
            resource=details.get('resource', 'unknown'),
            ip_address=details.get('ip', 'unknown'),
            user_agent=details.get('user_agent', ''),
            status=details.get('status', 'unknown'),
            details=details,
            source_system='syslog',
            session_id=details.get('session_id', '')
        )
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats"""
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def compute_user_baselines(self) -> Dict[str, UserBehaviorBaseline]:
        """Compute behavioral baselines for all users"""
        user_data = defaultdict(lambda: {
            'ips': defaultdict(int),
            'locations': defaultdict(int),
            'login_hours': [],
            'actions': defaultdict(int),
            'login_count': 0,
            'session_times': []
        })
        
        for log in self.logs:
            user_key = log.user_id
            user_data[user_key]['ips'][log.ip_address] += 1
            
            location = IPGeolocationMapper.get_location(log.ip_address)
            user_data[user_key]['locations'][location] += 1
            user_data[user_key]['login_hours'].append(log.timestamp.hour)
            user_data[user_key]['actions'][log.action] += 1
            
            if log.action.lower() in ['login', 'authenticate', 'signin']:
                user_data[user_key]['login_count'] += 1
        
        # Build baselines
        self.user_baselines = {}
        for user_id, data in user_data.items():
            # Most common IPs (top 5)
            common_ips = sorted(
                data['ips'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Most common locations
            common_locations = sorted(
                data['locations'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            # Typical login hours
            typical_hours = list(set(data['login_hours']))
            
            # Most common actions
            common_actions = sorted(
                data['actions'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            baseline = UserBehaviorBaseline(
                user_id=user_id,
                common_ips=[ip for ip, count in common_ips],
                common_locations=[loc for loc, count in common_locations],
                typical_login_hours=sorted(typical_hours),
                common_actions=[action for action, count in common_actions],
                avg_daily_logins=data['login_count'] / max(1, len(set(log.timestamp.date() for log in self.logs if log.user_id == user_id))),
                last_updated=datetime.utcnow()
            )
            
            self.user_baselines[user_id] = baseline
        
        return self.user_baselines
    
    def compute_anomaly_scores(self) -> List[AnomalyScore]:
        """Compute anomaly scores for all logs"""
        if not self.user_baselines:
            self.compute_user_baselines()
        
        self.anomaly_scores = []
        user_sessions = defaultdict(list)
        
        # Group logs by user and time for session analysis
        for log in self.logs:
            user_sessions[log.user_id].append(log)
        
        for log in self.logs:
            baseline = self.user_baselines.get(log.user_id)
            if not baseline:
                baseline = UserBehaviorBaseline(user_id=log.user_id)
            
            score = 0.0
            anomalies = []
            
            # Check 1: Impossible travel detection
            travel_anomaly = self._detect_impossible_travel(log.user_id, log)
            if travel_anomaly:
                score += 0.4
                anomalies.append(f"Impossible travel: {travel_anomaly}")
            
            # Check 2: Uncommon IP address
            if log.ip_address not in baseline.common_ips and baseline.common_ips:
                score += 0.2
                anomalies.append(f"New IP address: {log.ip_address}")
            
            # Check 3: Off-hours login
            if baseline.typical_login_hours and log.timestamp.hour not in baseline.typical_login_hours:
                if log.action.lower() in ['login', 'authenticate', 'signin']:
                    score += 0.15
                    anomalies.append(f"Off-hours login at {log.timestamp.hour}:00")
            
            # Check 4: Unusual action
            if log.action not in baseline.common_actions and baseline.common_actions:
                score += 0.1
                anomalies.append(f"Unusual action: {log.action}")
            
            # Check 5: Resource access anomaly (high risk resources)
            high_risk_resources = ['admin', 'config', 'secret', 'password', 'credentials']
            if any(res in log.resource.lower() for res in high_risk_resources):
                if log.action.lower() in ['read', 'access', 'download', 'export']:
                    score += 0.15
                    anomalies.append(f"High-risk resource access: {log.resource}")
            
            # Check 6: Failed authentication attempts
            if log.status.lower() in ['failed', 'denied', 'unauthorized', 'error']:
                if log.action.lower() in ['login', 'authenticate']:
                    score += 0.1
                    anomalies.append("Failed authentication attempt")
            
            # Clamp score to 0.0-1.0
            score = min(1.0, max(0.0, score))
            
            # Determine risk level
            if score >= 0.7:
                risk_level = "critical"
                action_taken = "block_and_alert"
            elif score >= 0.5:
                risk_level = "high"
                action_taken = "alert_and_monitor"
            elif score >= 0.3:
                risk_level = "medium"
                action_taken = "monitor"
            else:
                risk_level = "low"
                action_taken = "none"
            
            anomaly_score = AnomalyScore(
                user_id=log.user_id,
                timestamp=log.timestamp,
                score=round(score, 3),
                risk_level=risk_level,
                anomalies=anomalies,
                action_taken=action_taken,
                details={
                    'ip_address': log.ip_address,
                    'action': log.action,
                    'resource': log.resource,
                    'status': log.status
                }
            )
            
            self.anomaly_scores.append(anomaly_score)
        
        return self.anomaly_scores
    
    def _detect_impossible_travel(self, user_id: str, current_log: AuditLogEntry) -> Optional[str]:
        """Detect impossible travel between two locations"""
        # Find previous login for this user within last hour
        user_logs = [log for log in self.logs 
                    if log.user_id == user_id 
                    and log.timestamp < current_log.timestamp]
        
        if not user_logs:
            return None
        
        previous_log = max(user_logs, key=lambda x: x.timestamp)
        time_diff = (current_log.timestamp - previous_log.timestamp).total_seconds() / 3600
        
        if time_diff < 0.1:  # Less than 6 minutes
            return None
        
        if previous_log.ip_address == current_log.ip_address:
            return None
        
        prev_location = IPGeolocationMapper.get_location(previous_log.ip_address)
        curr_location = IPGeolocationMapper.get_location(current_log.ip_address)
        
        if prev_location == curr_location:
            return None
        
        # Estimate distance (simplified)
        distance = self._estimate_distance(prev_location, curr_location)
        required_speed = distance / time_diff if time_diff > 0 else float('inf')
        
        if required_speed > self.impossible_travel_threshold_kmh:
            return f"From {prev_location} to {curr_location} in {time_diff:.2f} hours (requires {required_speed:.0f} km/h)"
        
        return None
    
    def _estimate_distance(self, location1: str, location2: str) -> float:
        """Estimate distance between locations in kilometers"""
        location_coords = {
            'Internal-Network': (0, 0),
            'US-East': (40.7128, -74.0060),  # NYC
            'US-West': (37.7749, -122.4194),  # SF
            'Europe-UK': (51.5074, -0.1278),  # London
            'Europe': (48.8566, 2.3522),  # Paris
            'Asia-Pacific': (35.6762, 139.6503),  # Tokyo
            'Australia': (-33.8688, 151.2093),  # Sydney
            'South-America': (-23.5505, -46.6333),  # São Paulo
            'US-Google': (37.4419, -122.1430),  # Google HQ
        }
        
        if location1 not in location_coords or location2 not in location_coords:
            return random.uniform(500, 5000)
        
        lat1, lon1 = location_coords[location1]
        lat2, lon2 = location_coords[location2]
        
        # Haversine formula (simplified)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        radius_km = 6371
        
        return radius_km * c
    
    def get_summary(self) -> Dict[str, Any]:
        """Get ingestion and analysis summary"""
        return {
            'total_logs_ingested': len(self.logs),
            'unique_users': len(set(log.user_id for log in self.logs)),
            'unique_ips': len(set(log.ip_address for log in self.logs)),
            'logs_by_source': {
                'json': len([log for log in self.logs if log.source_system == 'json']),
                'csv': len([log for log in self.logs if log.source_system == 'csv']),
                'syslog': len([log for log in self.logs if log.source_system == 'syslog']),
            },
            'baseline_users': len(self.user_baselines),
            'anomaly_scores_computed': len(self.anomaly_scores),
            'high_risk_events': len([a for a in self.anomaly_scores if a.risk_level in ['high', 'critical']]),
            'time_range': {
                'earliest': min([log.timestamp for log in self.logs]).isoformat() if self.logs else None,
                'latest': max([log.timestamp for log in self.logs]).isoformat() if self.logs else None,
            }
        }
    
    def export_logs_json(self) -> str:
        """Export normalized logs as JSON"""
        return json.dumps([log.to_dict() for log in self.logs], indent=2)
    
    def export_baselines_json(self) -> str:
        """Export user baselines as JSON"""
        return json.dumps([baseline.to_dict() for baseline in self.user_baselines.values()], indent=2)
    
    def export_anomalies_json(self) -> str:
        """Export anomaly scores as JSON"""
        return json.dumps([score.to_dict() for score in self.anomaly_scores], indent=2)


def generate_sample_audit_logs() -> Tuple[str, str, str]:
    """Generate sample audit logs in multiple formats"""
    base_time = datetime.utcnow()
    
    # JSON format logs
    json_logs = []
    users = ['alice', 'bob', 'charlie', 'david']
    ips = [
        '192.168.1.10', '192.168.1.20', '192.168.1.30',
        '203.0.113.45', '203.0.113.100', '198.51.100.15'
    ]
    actions = ['login', 'logout', 'read', 'write', 'delete', 'admin_access']
    resources = ['config.db', 'user_data.csv', 'admin_panel', 'api_key', 'document_123']
    
    for i in range(15):
        json_logs.append({
            'timestamp': (base_time - timedelta(minutes=15-i)).isoformat() + 'Z',
            'user_id': users[i % len(users)],
            'action': actions[i % len(actions)],
            'resource': resources[i % len(resources)],
            'ip_address': ips[i % len(ips)],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'status': 'success' if i % 5 != 0 else 'failed',
            'session_id': f'sess_{hashlib.md5(f"{users[i % len(users)]}{i}".encode()).hexdigest()[:16]}'
        })
    
    json_str = json.dumps(json_logs)
    
    # CSV format logs
    csv_lines = [
        'timestamp,user,action,resource,ip_address,user_agent,status'
    ]
    for i in range(10):
        csv_lines.append(
            f'{(base_time - timedelta(minutes=10-i)).isoformat()},'
            f'{users[i % len(users)]},'
            f'{actions[i % len(actions)]},'
            f'{resources[i % len(resources)]},'
            f'{ips[(i+1) % len(ips)]},'
            f'Mozilla/5.0,'
            f'{"success" if i % 4 != 0 else "failed"}'
        )
    
    csv_str = '\n'.join(csv_lines)
    
    # Syslog format logs
    syslog_lines = []
    for i in range(10):
        ts = (base_time - timedelta(minutes=5-i))
        syslog_lines.append(
            f'{ts.strftime("%b %d %H:%M:%S")} server01 auth[1234]: '
            f'user={users[i % len(users)]} action={actions[i % len(actions)]} '
            f'resource={resources[i % len(resources)]} ip={ips[(i+2) % len(ips)]} '
            f'status={"success" if i % 3 != 0 else "failed"}'
        )
    
    syslog_str = '\n'.join(syslog_lines)
    
    # Add one impossible travel scenario
    alice_logs = [log for log in json_logs if log['user_id'] == 'alice']
    if alice_logs:
        alice_logs[-1]['ip_address'] = '1.1.1.100'  # Australia
        if len(alice_logs) > 1:
            alice_logs[-2]['ip_address'] = '203.0.113.45'  # US-East
            # Make time difference small for impossible travel
            base = datetime.fromisoformat(alice_logs[-2]['timestamp'].replace('Z', '+00:00'))
            alice_logs[-1]['timestamp'] = (base + timedelta(minutes=15)).isoformat() + 'Z'
    
    json_str = json.dumps(json_logs)
    
    return json_str, csv_str, syslog_str


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='SaaS Audit Log Ingestion and Breach Detection Pipeline'
    )
    
    parser.add_argument(
        '--input-format',
        choices=['json', 'csv', 'syslog', 'auto', 'demo'],
        default='demo',
        help='Input log format (demo generates sample data)'
    )
    
    parser.add_argument(
        '--input-file',
        type=str,
        help='Path to input log file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./breach_detection_output',
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--max-logs',
        type=int,
        default=10000,
        help='Maximum logs to process'
    )
    
    parser.add_argument(
        '--compute-baselines',
        action='store_true',
        help='Compute user behavioral baselines'
    )
    
    parser.add_argument(
        '--compute-anomalies',
        action='store_true',
        help='Compute anomaly scores for all logs'
    )
    
    parser.add_argument(
        '--export-logs',
        action='store_true',
        help='Export normalized logs to JSON'
    )
    
    parser.add_argument(
        '--export-baselines',
        action='store_true',
        help='Export user baselines to JSON'
    )
    
    parser.add_argument(
        '--export-anomalies',
        action='store_true',
        help='Export anomaly scores to JSON'
    )
    
    parser.add_argument(
        '--show-summary',
        action='store_true',
        default=True,
        help='Show processing summary'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = AuditLogIngestionPipeline(max_logs=args.max_logs)
    
    # Ingest logs
    print("[*] Starting audit log ingestion pipeline...", file=sys.stderr)
    
    if args.input_format == 'demo':
        print("[*] Generating demo audit logs...", file=sys.stderr)
        json_data, csv_data, syslog_data = generate_sample_audit_logs()
        
        print(f"[+] Ingesting JSON logs...", file=sys.stderr)
        json_count = pipeline.ingest_json_logs(json_data)
        print(f"    Ingested {json_count} JSON logs", file=sys.stderr)
        
        print(f"[+] Ingesting CSV logs...", file=sys.stderr)
        csv_count = pipeline.ingest_csv_logs(csv_data)
        print(f"    Ingested {csv_count} CSV logs", file=sys.stderr)
        
        print(f"[+] Ingesting syslog format logs...", file=sys.stderr)
        syslog_count = pipeline.ingest_syslog_logs(syslog_data)
        print(f"    Ingested {syslog_count} syslog logs", file=sys.stderr)
    
    elif args.input_file:
        print(f"[*] Reading input from {args.input_file}...", file=sys.stderr)
        try:
            with open(args.input_file, 'r') as f:
                data = f.read()
            
            if args.input_format == 'json':
                count = pipeline.ingest_json_logs(data)
                print(f"[+] Ingested {count} JSON logs", file=sys.stderr)
            elif args.input_format == 'csv':
                count = pipeline.ingest_csv_logs(data)
                print(f"[+] Ingested {count} CSV logs", file=sys.stderr)
            elif args.input_format == 'syslog':
                count = pipeline.ingest_syslog_logs(data)
                print(f"[+] Ingested {count} syslog logs", file=sys.stderr
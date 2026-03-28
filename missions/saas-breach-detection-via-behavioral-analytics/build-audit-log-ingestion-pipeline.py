#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build audit log ingestion pipeline
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-28T22:05:52.894Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build audit log ingestion pipeline
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @echo
DATE: 2025-01-20

Complete implementation of an audit log ingestion pipeline for breach detection.
Includes log parsing, validation, user baseline establishment, anomaly detection,
impossible travel detection, and automated response mechanisms.
"""

import json
import argparse
import sys
import csv
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import hashlib
import re
import gzip
import io
from pathlib import Path


@dataclass
class AuditLog:
    """Structured audit log entry."""
    timestamp: str
    user_id: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    status: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLogValidator:
    """Validates and normalizes audit log entries."""
    
    REQUIRED_FIELDS = ['timestamp', 'user_id', 'action', 'resource', 'ip_address', 'user_agent', 'status']
    VALID_ACTIONS = ['login', 'logout', 'create', 'read', 'update', 'delete', 'export', 'admin_action', 'api_call']
    VALID_STATUSES = ['success', 'failure', 'pending']
    IP_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    
    @staticmethod
    def validate(entry: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate audit log entry."""
        for field in AuditLogValidator.REQUIRED_FIELDS:
            if field not in entry:
                return False, f"Missing required field: {field}"
        
        if entry.get('action') not in AuditLogValidator.VALID_ACTIONS:
            return False, f"Invalid action: {entry.get('action')}"
        
        if entry.get('status') not in AuditLogValidator.VALID_STATUSES:
            return False, f"Invalid status: {entry.get('status')}"
        
        if not AuditLogValidator.IP_PATTERN.match(entry.get('ip_address', '')):
            return False, f"Invalid IP address format: {entry.get('ip_address')}"
        
        try:
            datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return False, f"Invalid timestamp format: {entry.get('timestamp')}"
        
        if not isinstance(entry.get('user_id'), str) or len(entry['user_id']) == 0:
            return False, "Invalid user_id"
        
        return True, None
    
    @staticmethod
    def normalize(entry: Dict[str, Any]) -> AuditLog:
        """Convert validated entry to AuditLog."""
        return AuditLog(
            timestamp=entry['timestamp'],
            user_id=entry['user_id'].lower(),
            action=entry['action'].lower(),
            resource=entry['resource'],
            ip_address=entry['ip_address'],
            user_agent=entry['user_agent'],
            status=entry['status'].lower(),
            details=entry.get('details', {})
        )


class AuditLogParser:
    """Parse audit logs from various formats."""
    
    @staticmethod
    def parse_json_logs(content: str) -> List[Dict[str, Any]]:
        """Parse JSON format logs (one per line or array)."""
        logs = []
        content = content.strip()
        
        if content.startswith('['):
            logs = json.loads(content)
        else:
            for line in content.split('\n'):
                if line.strip():
                    logs.append(json.loads(line))
        
        return logs
    
    @staticmethod
    def parse_csv_logs(content: str) -> List[Dict[str, Any]]:
        """Parse CSV format logs."""
        logs = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            if row:
                logs.append(row)
        return logs
    
    @staticmethod
    def parse_logs(content: str, format_type: str = 'json') -> List[Dict[str, Any]]:
        """Parse audit logs based on format."""
        if format_type == 'json':
            return AuditLogParser.parse_json_logs(content)
        elif format_type == 'csv':
            return AuditLogParser.parse_csv_logs(content)
        else:
            raise ValueError(f"Unsupported format: {format_type}")


class UserBehaviorBaseline:
    """Establishes and manages user behavior baselines."""
    
    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'typical_ips': set(),
            'typical_locations': set(),
            'typical_user_agents': set(),
            'typical_actions': defaultdict(int),
            'typical_times': [],
            'login_count': 0,
            'first_seen': None,
            'last_seen': None,
            'access_frequency': defaultdict(int)
        })
    
    def update(self, log: AuditLog) -> None:
        """Update baseline with new log entry."""
        baseline = self.baselines[log.user_id]
        
        if baseline['first_seen'] is None:
            baseline['first_seen'] = log.timestamp
        baseline['last_seen'] = log.timestamp
        
        baseline['typical_ips'].add(log.ip_address)
        baseline['typical_user_agents'].add(log.user_agent)
        baseline['typical_actions'][log.action] += 1
        
        try:
            dt = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            baseline['typical_times'].append(dt.hour)
        except ValueError:
            pass
        
        if log.action == 'login':
            baseline['login_count'] += 1
        
        day_of_week = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00')).strftime('%A')
        baseline['access_frequency'][day_of_week] += 1
    
    def get_baseline(self, user_id: str) -> Dict[str, Any]:
        """Get baseline for user."""
        baseline = self.baselines[user_id]
        return {
            'user_id': user_id,
            'typical_ips': list(baseline['typical_ips']),
            'typical_user_agents': list(baseline['typical_user_agents']),
            'typical_actions': dict(baseline['typical_actions']),
            'typical_times': baseline['typical_times'],
            'login_count': baseline['login_count'],
            'access_frequency': dict(baseline['access_frequency']),
            'first_seen': baseline['first_seen'],
            'last_seen': baseline['last_seen']
        }


class AnomalyDetector:
    """Detects anomalies in user behavior."""
    
    def __init__(self, baseline: UserBehaviorBaseline):
        self.baseline = baseline
    
    def detect_impossible_travel(self, logs: List[AuditLog]) -> List[Dict[str, Any]]:
        """Detect impossible travel patterns (same user in distant locations quickly)."""
        anomalies = []
        user_logs = defaultdict(list)
        
        for log in logs:
            user_logs[log.user_id].append(log)
        
        for user_id, user_events in user_logs.items():
            sorted_events
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build audit log ingestion pipeline
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-31T19:13:44.562Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build audit log ingestion pipeline
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @echo
Date: 2025-01-14

Audit log ingestion pipeline for SaaS platforms with validation,
normalization, storage, and anomaly-ready formatting.
"""

import argparse
import json
import sys
import sqlite3
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import random
import string


class AuditEventType(Enum):
    """Standard audit event types for SaaS platforms."""
    LOGIN = "login"
    LOGOUT = "logout"
    DATA_ACCESS = "data_access"
    DATA_MODIFY = "data_modify"
    DATA_DELETE = "data_delete"
    PERMISSION_CHANGE = "permission_change"
    ADMIN_ACTION = "admin_action"
    API_CALL = "api_call"
    FAILED_AUTH = "failed_auth"
    SESSION_CREATED = "session_created"
    SESSION_TERMINATED = "session_terminated"
    MFA_ENROLLED = "mfa_enrolled"
    PASSWORD_CHANGED = "password_changed"
    UNKNOWN = "unknown"


class AuditEventSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Normalized audit event with validation and enrichment."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: AuditEventType = AuditEventType.UNKNOWN
    user_id: str = ""
    username: str = ""
    source_ip: str = ""
    resource_type: str = ""
    resource_id: str = ""
    action: str = ""
    result: str = "success"
    error_code: str = ""
    severity: AuditEventSeverity = AuditEventSeverity.LOW
    session_id: str = ""
    user_agent: str = ""
    organization_id: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    ingestion_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    content_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA256 hash of core event fields for integrity."""
        core_data = f"{self.event_id}{self.timestamp}{self.user_id}{self.action}{self.resource_id}"
        return hashlib.sha256(core_data.encode()).hexdigest()

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate audit event integrity and completeness."""
        errors = []
        
        if not self.user_id or not self.user_id.strip():
            errors.append("user_id is required")
        
        if not self.timestamp:
            errors.append("timestamp is required")
        else:
            try:
                datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"invalid timestamp format: {self.timestamp}")
        
        if not self.source_ip or not self._validate_ip(self.source_ip):
            errors.append(f"invalid source_ip: {self.source_ip}")
        
        if self.event_type == AuditEventType.UNKNOWN:
            errors.append("event_type cannot be unknown after normalization")
        
        if not self.action or not self.action.strip():
            errors.append("action is required")
        
        return len(errors) == 0, errors

    @staticmethod
    def _validate_ip(ip: str) -> bool:
        """Validate IPv4 or IPv6 address format."""
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
        
        if re.match(ipv4_pattern, ip):
            parts = ip.split('.')
            return all(0 <= int(p) <= 255 for p in parts)
        
        return bool(re.match(ipv6_pattern, ip))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data


class AuditLogNormalizer:
    """Normalize various audit log formats to standard schema."""

    @staticmethod
    def normalize_json_log(raw_log: Dict[str, Any]) -> AuditEvent:
        """Normalize generic JSON audit log."""
        event = AuditEvent()
        
        event.event_id = raw_log.get('event_id') or str(uuid.uuid4())
        event.timestamp = raw_log.get('timestamp', datetime.utcnow().isoformat())
        event.user_id = raw_log.get('user_id', '')
        event.username = raw_log.get('username', '')
        event.source_ip = raw_log.get('source_ip', '0.0.0.0')
        event.resource_type = raw_log.get('resource_type', '')
        event.resource_id = raw_log.get('resource_id', '')
        event.action = raw_log.get('action', '')
        event.result = raw_log.get('result', 'success')
        event.error_code = raw_log.get('error_code', '')
        event.session_id = raw_log.get('session_id', '')
        event.user_agent = raw_log.get('user_agent', '')
        event.organization_id = raw_log.get('organization_id', '')
        event.raw_data = raw_log
        
        event.event_type = AuditLogNormalizer._classify_event_type(raw_log)
        event.severity = AuditLogNormalizer._classify_severity(event)
        event.content_hash = event.compute_hash()
        
        return event

    @staticmethod
    def normalize_aws_cloudtrail(raw_log: Dict[str, Any]) -> AuditEvent:
        """Normalize AWS CloudTrail format."""
        event = AuditEvent()
        
        event.event_id = raw_log.get('eventID', str(uuid.uuid4()))
        event.timestamp = raw_log.get('eventTime', datetime.utcnow().isoformat())
        event.user_id = raw_log.get('userIdentity', {}).get('principalId', '')
        event.username = raw_log.get('userIdentity', {}).get('userName', '')
        event.source_ip = raw_log.get('sourceIPAddress', '0.0.0.0')
        event.action = raw_log.get('eventName', '')
        event.resource_type = raw_log.get('eventSource', '')
        event.result = 'success' if raw_log.get('errorCode') is None else 'failure'
        event.error_code = raw_log.get('errorCode', '')
        event.user_agent = raw_log.get('userAgent', '')
        event.raw_data = raw_log
        
        event.event_type = AuditLogNormalizer._classify_event_type_aws(raw_log)
        event.severity = AuditLogNormalizer._classify_severity(event)
        event.content_hash = event.compute_hash()
        
        return event

    @staticmethod
    def normalize_okta_log(raw_log: Dict[str, Any]) -> AuditEvent:
        """Normalize Okta audit log format."""
        event = AuditEvent()
        
        event.event_id = raw_log.get('uuid', str(uuid.uuid4()))
        event.timestamp = raw_log.get('published', datetime.utcnow().isoformat())
        
        actor = raw_log.get('actor', {})
        event.user_id = actor.get('id', '')
        event.username = actor.get('login', '')
        
        client = raw_log.get('client', {})
        event.source_ip = client.get('ipAddress', '0.0.0.0')
        event.user_agent = client.get('userAgent', {}).get('rawUserAgent', '')
        
        event.action = raw_log.get('eventType', '')
        event.result = 'success' if raw_log.get('outcome', {}).get('result') == 'SUCCESS' else 'failure'
        event.organization_id = raw_log.get('orgId', '')
        event.raw_data = raw_log
        
        event.event_type = AuditLogNormalizer._classify_event_type_okta(raw_log)
        event.severity = AuditLogNormalizer._classify_severity(event)
        event.content_hash = event.compute_hash()
        
        return event

    @staticmethod
    def _classify_event_type(log: Dict[str, Any]) -> AuditEventType:
        """Classify event type from generic log."""
        action = log.get('action', '').lower()
        event_type = log.get('event_type', '').lower()
        
        if 'login' in action or 'login' in event_type or 'signin' in action:
            return AuditEventType.LOGIN
        elif 'logout' in action or 'logoff' in action or 'signout' in action:
            return AuditEventType.LOGOUT
        elif 'read' in action or 'get' in action or 'access' in action:
            return AuditEventType.DATA_ACCESS
        elif 'create' in action or 'update' in action or 'put' in action or 'post' in action:
            return AuditEventType.DATA_MODIFY
        elif 'delete' in action or 'remove' in action:
            return AuditEventType.DATA_DELETE
        elif 'permission' in action or 'role' in action:
            return AuditEventType.PERMISSION_CHANGE
        elif 'failed' in action or 'failure' in action or 'error' in action:
            return AuditEventType.FAILED_AUTH
        else:
            return AuditEventType.UNKNOWN

    @staticmethod
    def _classify_event_type_aws(log: Dict[str, Any]) -> AuditEventType:
        """Classify AWS CloudTrail event type."""
        event_name = log.get('eventName', '').lower()
        
        if 'login' in event_name or 'signin' in event_name:
            return AuditEventType.LOGIN
        elif 'logout' in event_name or 'signout' in event_name:
            return AuditEventType.LOGOUT
        elif 'get' in event_name or 'describe' in event_name or 'list' in event_name:
            return AuditEventType.DATA_ACCESS
        elif 'put' in event_name or 'create' in event_name or 'update' in event_name:
            return AuditEventType.DATA_MODIFY
        elif 'delete' in event_name:
            return AuditEventType.DATA_DELETE
        elif 'assumeRole' in event_name or 'attachUserPolicy' in event_name:
            return AuditEventType.PERMISSION_CHANGE
        else:
            return AuditEventType.API_CALL

    @staticmethod
    def _classify_event_type_okta(log: Dict[str, Any]) -> AuditEventType:
        """Classify Okta event type."""
        event_type = log.get('eventType', '').lower()
        
        if 'user.session.start' in event_type:
            return AuditEventType.LOGIN
        elif 'user.session.end' in event_type:
            return AuditEventType.LOGOUT
        elif 'user.authentication.auth_via_mfa' in event_type:
            return AuditEventType.MFA_ENROLLED
        elif 'user.account.update_password' in event_type:
            return AuditEventType.PASSWORD_CHANGED
        elif 'user.account.privilege.grant' in event_type or 'user.account.privilege.revoke' in event_type:
            return AuditEventType.PERMISSION_CHANGE
        else:
            return AuditEventType.UNKNOWN

    @staticmethod
    def _classify_severity(event: AuditEvent) -> AuditEventSeverity:
        """Classify event severity."""
        critical_actions = ['delete', 'remove', 'terminate', 'disable', 'admin']
        high_actions = ['modify', 'update', 'create', 'permission', 'role', 'permission_change']
        
        action_lower = event.action.lower()
        
        if event.result == 'failure' and 'auth' in event.event_type.value:
            return AuditEventSeverity.MEDIUM
        
        if any(crit in action_lower for crit in critical_actions):
            return AuditEventSeverity.CRITICAL
        elif any(high in action_lower for high in high_actions):
            return AuditEventSeverity.HIGH
        elif event.result == 'failure':
            return AuditEventSeverity.MEDIUM
        else:
            return AuditEventSeverity.LOW


class AuditLogIngestionPipeline:
    """Complete audit log ingestion pipeline with storage and analytics."""

    def __init__(self, db_path: str, buffer_size: int = 100):
        """Initialize ingestion pipeline."""
        self.db_path = db_path
        self.buffer_size = buffer_size
        self.event_buffer: List[AuditEvent] = []
        self.ingestion_stats = {
            'total_ingested': 0,
            'valid_events': 0,
            'invalid_events': 0,
            'events_by_type': {},
            'events_by_severity': {},
            'failed_ip_validations': 0,
        }
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT,
                source_ip TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT NOT NULL,
                result TEXT,
                error_code TEXT,
                severity TEXT,
                session_id TEXT,
                user_agent TEXT,
                organization_id TEXT,
                content_hash TEXT,
                ingestion_timestamp TEXT,
                raw_data TEXT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_user_id (user_id),
                INDEX idx_event_type (event_type),
                INDEX idx_source_ip (source_ip),
                INDEX idx_severity (severity),
                INDEX idx_organization (organization_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingestion_stats (
                stat_id INTEGER PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                total_ingested INTEGER,
                valid_events INTEGER,
                invalid_events INTEGER,
                events_by_type TEXT,
                events_by_severity TEXT,
                failed_ip_validations INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()

    def ingest_logs(self, logs: List[Dict[str, Any]], source_format: str = 'json') -> Dict[str, Any]:
        """Ingest and normalize logs from various sources."""
        results = {
            'total': len(logs),
            'ingested': 0,
            'failed': 0,
            'events': [],
            'errors': [],
        }
        
        normalizer_map = {
            'json': AuditLogNormalizer.normalize_json_log,
            'cloudtrail': AuditLogNormalizer.normalize_aws_cloudtrail,
            'okta': AuditLogNormalizer.normalize_okta_log,
        }
        
        normalizer = normalizer_map.get(source_format, AuditLogNormalizer.normalize_json_log)
        
        for log in logs:
            try:
                event = normalizer(log)
                is_valid, validation_errors = event.validate()
                
                if is_valid:
                    self.event_buffer.append(event)
                    self.ingestion_stats['valid_events'] += 1
                    results['ingested'] += 1
                    results['events'].append(event.to_dict())
                    
                    event_type_key = event.event_type.value
                    self.ingestion_stats['events_by_type'][event_type_key] = \
                        self.ingestion_stats['events_by_type'].get(event_type_key, 0) + 1
                    
                    severity_key = event.severity.value
                    self.ingestion_stats['events_by_severity'][severity_key] = \
                        self.ingestion_stats['events_by_severity'].get(severity_key, 0) + 1
                else:
                    self.ingestion_stats['invalid_events'] += 1
                    results['failed'] += 1
                    results['errors'].append({
                        'source_log': log,
                        'validation_errors': validation_errors,
                    })
                
                self.ingestion_stats['total_ingested'] += 1
                
                if len(self.event_buffer) >= self.buffer_size:
                    self.flush()
            
            except Exception as e:
                self.ingestion_stats['invalid_events'] += 1
                results['failed'] += 1
                results['errors'].append({
                    'source_log': log,
                    'exception': str(e),
                })
        
        return results

    def flush(self) -> int:
        """Flush buffered events to database."""
        if not self.event_buffer:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        inserted = 0
        for event in self.event_buffer:
            try:
                cursor.execute('''
                    INSERT INTO audit_events (
                        event_id, timestamp, event_type, user_id, username,
                        source_ip, resource_type, resource_id, action, result,
                        error_code, severity, session_id, user_agent,
                        organization_id, content_hash, ingestion_timestamp, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id, event.timestamp, event.event_type.value,
                    event.user_id, event.username, event.source_ip,
                    event.resource_type, event.resource_id, event.action,
                    event.result, event.error_code, event.severity.value,
                    event.session_id, event.user_agent, event.organization_id,
                    event.content_hash, event.ingestion_timestamp,
                    json.dumps(event.raw_data)
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
        
        self.event_buffer.clear()
        return inserted

    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion pipeline statistics."""
        self.flush()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM audit_events')
        total_stored = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM audit_events
            GROUP BY event_type
        ''')
        event_type_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT severity, COUNT(*) as count
            FROM audit_events
            GROUP BY severity
        ''')
        severity_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM audit_events
        ''')
        unique_users = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(DISTINCT source_ip) FROM audit_events
        ''')
        unique_ips = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'ingestion_phase': self.ingestion_stats,
            'storage': {
                'total_events_stored': total_stored,
                'event_type_breakdown': event_type_breakdown,
                'severity_breakdown': severity_breakdown,
                'unique_users': unique_users,
                'unique_source_ips': unique_ips,
            },
            'timestamp': datetime.utcnow().isoformat(),
        }

    def query_events(self, user_id: str = None, event_type: str = None,
                     severity: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query stored events with optional filters."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM audit_events WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        events = []
        for row in rows:
            event_dict = dict(row)
            if event_dict.get('raw_data'):
                event_dict['raw_data'] = json.loads(event_dict['raw_data'])
            events.append(event_dict)
        
        return events

    def export_events(self, output_path: str, format_type: str = 'jsonl') -> str:
        """Export stored events to file."""
        self.flush()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM audit_events ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == 'jsonl':
            with open(output_file, 'w') as f:
                for row in rows:
                    event_dict = dict(row)
                    if event_dict.get('raw_data'):
                        event_dict['raw_data'] = json.loads(event_dict['raw_data'])
                    f.write(json.dumps(event_dict) + '\n')
        
        elif format_type == 'json':
            events = []
            for row in rows:
                event_dict = dict(row)
                if event_dict.get('raw_data'):
                    event_dict['raw_data'] = json.loads(event_dict['raw_data'])
                events.append(event_dict)
            
            with open(output_file, 'w') as f:
                json.dump(events, f, indent=2)
        
        return str(output_file)


def generate_sample_logs(count: int = 50) -> List[Dict[str, Any]]:
    """Generate realistic sample audit logs for testing."""
    users = [f'user_{i}@example.com' for i in range(10)]
    ips = [f'192.168.{random.randint(0,255)}.{random.randint(0,255)}' for _ in range(5)]
    resources = ['file_123', 'database_456', 'api_key_789', 'report_101', 'dashboard_202']
    actions = [
        'login', 'logout', 'read_file', 'modify_config', 'delete_record',
        'create_user', 'assign_role', 'api_call', 'data_export', 'password_change'
    ]
    
    logs = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        timestamp = base_time - timedelta(minutes=random.randint(0, 1440))
        
        logs.append({
            'event_id': str(uuid.uuid4()),
            'timestamp': timestamp.isoformat(),
            'user_id': f"uid_{random.choice(users).split('@')[0]}",
            'username': random.choice(users),
            'source_ip': random.choice(ips),
            'resource_type': 'data' if random.random() > 0.3 else 'config',
            'resource_id': random.choice(resources),
            'action': random.choice(actions),
            'result': 'success' if random.random() > 0.1 else 'failure',
            'error_code': '' if random.random() > 0.1 else f'ERR_{random.randint(400, 500)}',
            'session_id': f"sess_{random.randint(1000, 9999)}",
            'user_agent': f"Mozilla/5.0 (Platform {random.randint(1,5)})",
            'organization_id': 'org_001',
        })
    
    return logs


def main():
    """Main CLI interface for audit log ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description='Audit Log Ingestion Pipeline for SaaS Breach Detection'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='/tmp/audit_logs.db',
        help='Path to SQLite database (default: /tmp/audit_logs.db)'
    )
    
    parser.add_argument(
        '--input-file',
        type=str,
        help='Path to input log file (JSON or JSONL format)'
    )
    
    parser.add_argument(
        '--input-format',
        type=str,
        choices=['json', 'jsonl', 'cloudtrail', 'okta'],
        default='json',
        help='Input log format (default: json)'
    )
    
    parser.add_argument(
        '--generate-sample',
        type=int,
        metavar='COUNT',
        help='Generate and ingest sample logs (specify count)'
    )
    
    parser.add_argument(
        '--buffer-size',
        type=int,
        default=100,
        help='Event buffer size before flush (default: 100)'
    )
    
    parser.add_argument(
        '--query-user',
        type=str,
        help='Query events for specific user ID'
    )
    
    parser.add_argument(
        '--query-type',
        type=str,
        help='Query events of specific type'
    )
    
    parser.add_argument(
        '--query-severity',
        type=str,
        choices=['low', 'medium', 'high', 'critical'],
        help='Query events of specific severity'
    )
    
    parser.add_argument(
        '--query-limit',
        type=int,
        default=50,
        help='Limit for query results (default: 50)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Display ingestion statistics'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        metavar='OUTPUT_PATH',
        help='Export events to file'
    )
    
    parser.add_argument(
        '--export-format',
        type=str,
        choices=['jsonl', 'json'],
        default='jsonl',
        help='Export format (default: jsonl)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    pipeline = AuditLogIngestionPipeline(args.db_path, args.buffer_size)
    
    if args.generate_sample:
        if args.verbose:
            print(f"Generating {args.generate_sample} sample logs...")
        
        sample_logs = generate_sample_logs(args.generate_sample)
        result = pipeline.ingest_logs(sample_logs, source_format=args.input_format)
        
        print(json.dumps({
            'action': 'generate_and_ingest',
            'ingestion_result': {
                'total': result['total'],
                'ingested': result['ingested'],
                'failed': result['failed'],
            }
        }, indent=2))
    
    elif args.input_file:
        if args.verbose:
            print(f"Reading logs from {args.input_file}...")
        
        with open(args.input_file, 'r') as f:
            if args.input_format == 'jsonl':
                logs = [json.loads(line) for line in f if line.strip()]
            else:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = [logs]
        
        result = pipeline.ingest_logs(logs, source_format=args.input_format)
        
        print(json.dumps({
            'action': 'ingest_from_file',
            'file': args.input_file,
            'ingestion_result': {
                'total': result['total'],
                'ingested': result['ingested'],
                'failed': result['failed'],
            }
        }, indent=2))
    
    if args.query_user or args.query_type or args.query_severity:
        results = pipeline.query_events(
            user_id=args.query_user,
            event_type=args.query_type,
            severity=args.query_severity,
            limit=args.query_limit
        )
        
        print(json.dumps({
            'action': 'query_events',
            'filters': {
                'user_id': args.query_user,
                'event_type': args.query_type,
                'severity': args.query_severity,
            },
            'result_count': len(results),
            'events': results[:10],
        }, indent=2))
    
    if args.stats:
        stats = pipeline.get_stats()
        print(json.dumps(stats, indent=2))
    
    if args.export:
        export_path = pipeline.export_events(args.export, args.export_format)
        print(json.dumps({
            'action': 'export_events',
            'output_path': export_path,
            'format': args.export_format,
        }, indent=2))


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    User session anomaly scanner
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-31T19:14:12.213Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: User session anomaly scanner
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @sue
DATE: 2026
CATEGORY: Engineering

Detect compromised sessions by analyzing login timestamps, IP geolocation,
and user-agent patterns. Flag impossible travel and concurrent sessions.
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2
import hashlib
import random
import string


class SessionAnomalyScanner:
    """Detects anomalous user sessions via behavioral analytics."""

    def __init__(self, max_concurrent_sessions=2, impossible_travel_threshold_kmh=900):
        """
        Initialize the scanner.
        
        Args:
            max_concurrent_sessions: Maximum allowed concurrent sessions per user
            impossible_travel_threshold_kmh: Speed threshold for impossible travel detection
        """
        self.max_concurrent_sessions = max_concurrent_sessions
        self.impossible_travel_threshold_kmh = impossible_travel_threshold_kmh
        self.user_sessions = defaultdict(list)
        self.user_baselines = defaultdict(dict)
        self.alerts = []

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two geographic coordinates in km."""
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def ingest_session(self, session_record):
        """
        Process a session log entry.
        
        Args:
            session_record: Dict with keys: username, timestamp, ip, latitude, longitude,
                          user_agent, action (login/logout/activity)
        """
        username = session_record.get('username')
        timestamp = datetime.fromisoformat(session_record.get('timestamp', datetime.now().isoformat()))
        ip = session_record.get('ip', '')
        latitude = float(session_record.get('latitude', 0))
        longitude = float(session_record.get('longitude', 0))
        user_agent = session_record.get('user_agent', '')
        action = session_record.get('action', 'activity')
        session_id = hashlib.md5(f"{username}{ip}{timestamp.isoformat()}".encode()).hexdigest()[:12]

        if action == 'login':
            self._handle_login(username, timestamp, ip, latitude, longitude, user_agent, session_id)
        elif action == 'logout':
            self._handle_logout(username, session_id)
        elif action == 'activity':
            self._validate_activity(username, timestamp, ip, latitude, longitude, user_agent, session_id)

    def _handle_login(self, username, timestamp, ip, latitude, longitude, user_agent, session_id):
        """Process login event and check for anomalies."""
        session = {
            'session_id': session_id,
            'login_time': timestamp,
            'ip': ip,
            'latitude': latitude,
            'longitude': longitude,
            'user_agent': user_agent,
            'last_activity': timestamp,
            'logout_time': None
        }

        active_sessions = [s for s in self.user_sessions[username] if s['logout_time'] is None]
        
        if len(active_sessions) >= self.max_concurrent_sessions:
            self._alert('concurrent_sessions_exceeded', {
                'username': username,
                'timestamp': timestamp.isoformat(),
                'active_count': len(active_sessions),
                'max_allowed': self.max_concurrent_sessions,
                'new_ip': ip,
                'existing_ips': [s['ip'] for s in active_sessions]
            })

        if active_sessions:
            last_session = active_sessions[-1]
            self._check_impossible_travel(username, timestamp, last_session, latitude, longitude, ip)

        if username in self.user_baselines:
            baseline = self.user_baselines[username]
            self._check_anomalous_user_agent(username, timestamp, user_agent, baseline)
            self._check_anomalous_location(username, timestamp, ip, latitude, longitude, baseline)

        self.user_sessions[username].append(session)
        self._update_baseline(username, ip, latitude, longitude, user_agent)

    def _handle_logout(self, username, session_id):
        """Process logout event."""
        for session in self.user_sessions[username]:
            if session['session_id'] == session_id:
                session['logout_time'] = datetime.now()
                break

    def _validate_activity(self, username, timestamp, ip, latitude, longitude, user_agent, session_id):
        """Validate that ongoing activity is consistent with established session."""
        active_sessions = [s for s in self.user_sessions[username] if s['logout_time'] is None]
        
        if not active_sessions:
            self._alert('activity_without_session', {
                'username': username,
                'timestamp': timestamp.isoformat(),
                'ip': ip
            })
            return

        matching_session = None
        for session in active_sessions:
            if session['ip'] == ip:
                matching_session = session
                break

        if matching_session:
            matching_session['last_activity'] = timestamp
        else:
            self._alert('activity_from_unregistered_ip', {
                'username': username,
                'timestamp': timestamp.isoformat(),
                'activity_ip': ip,
                'session_ips': [s['ip'] for s in active_sessions]
            })

    def _check_impossible_travel(self, username, new_login_time, last_session, new_lat, new_lon, new_ip):
        """Detect impossible travel between sessions."""
        last_activity = last_session['last_activity']
        time_diff_hours = (new_login_time - last_activity).total_seconds() / 3600.0
        
        if time_diff_hours < 0.1:
            time_diff_hours = 0.1

        distance_km = self.haversine_distance(
            last_session['latitude'], last_session['longitude'],
            new_lat, new_lon
        )

        required_speed_kmh = distance_km / time_diff_hours

        if required_speed_kmh > self.impossible_travel_threshold_kmh:
            self._alert('impossible_travel', {
                'username': username,
                'previous_location': {
                    'ip': last_session['ip'],
                    'latitude': last_session['latitude'],
                    'longitude': last_session['longitude'],
                    'timestamp': last_session['last_activity'].isoformat()
                },
                'new_location': {
                    'ip': new_ip,
                    'latitude': new_lat,
                    'longitude': new_lon,
                    'timestamp': new_login_time.isoformat()
                },
                'distance_km': round(distance_km, 2),
                'time_hours': round(time_diff_hours, 2),
                'required_speed_kmh': round(required_speed_kmh, 2),
                'threshold_kmh': self.impossible_travel_threshold_kmh
            })

    def _check_anomalous_user_agent(self, username, timestamp, user_agent, baseline):
        """Detect unusual user agent patterns."""
        baseline_agents = baseline.get('user_agents', set())
        
        if user_agent and user_agent not in baseline_agents:
            self._alert('anomalous_user_agent', {
                'username': username,
                'timestamp': timestamp.isoformat(),
                'new_user_agent': user_agent,
                'baseline_agents': list(baseline_agents)[:5]
            })

    def _check_anomalous_location(self, username, timestamp, ip, latitude, longitude, baseline):
        """Detect unusual geographic locations."""
        baseline_ips = baseline.get('ips', set())
        
        if ip and ip not in baseline_ips:
            baseline_locs = baseline.get('locations', [])
            
            is_nearby = False
            if baseline_locs:
                for baseline_lat, baseline_lon in baseline_locs:
                    dist = self.haversine_distance(latitude, longitude, baseline_lat, baseline_lon)
                    if dist < 50:
                        is_nearby = True
                        break
            
            if not is_nearby and baseline_locs:
                self._alert('anomalous_location', {
                    'username': username,
                    'timestamp': timestamp.isoformat(),
                    'new_ip': ip,
                    'new_location': [latitude, longitude],
                    'baseline_locations': baseline_locs[:3],
                    'distance_from_baseline_km': round(
                        min(self.haversine_distance(latitude, longitude, lat, lon) 
                            for lat, lon in baseline_locs), 2
                    ) if baseline_locs else None
                })

    def _update_baseline(self, username, ip, latitude, longitude, user_agent):
        """Update user baseline behavior profile."""
        if username not in self.user_baselines:
            self.user_baselines[username] = {
                'ips': set(),
                'locations': [],
                'user_agents': set(),
                'first_seen': datetime.now().isoformat()
            }

        baseline = self.user_baselines[username]
        baseline['ips'].add(ip)
        baseline['user_agents'].add(user_agent)
        
        if [latitude, longitude] not in baseline['locations'] and latitude != 0 and longitude != 0:
            baseline['locations'].append([latitude, longitude])
            baseline['locations'] = baseline['locations'][-10]
        
        baseline['last_seen'] = datetime.now().isoformat()

    def _alert(self, alert_type, details):
        """Record a security alert."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': self._get_severity(alert_type),
            'details': details
        }
        self.alerts.append(alert)

    def _get_severity(self, alert_type):
        """Determine severity level based on alert type."""
        severity_map = {
            'impossible_travel': 'high',
            'concurrent_sessions_exceeded': 'high',
            'activity_from_unregistered_ip': 'medium',
            'anomalous_user_agent': 'low',
            'anomalous_location': 'medium',
            'activity_without_session': 'medium'
        }
        return severity_map.get(alert_type, 'low')

    def get_alerts(self, severity_filter=None, alert_type_filter=None):
        """Retrieve alerts with optional filtering."""
        filtered = self.alerts
        
        if severity_filter:
            filtered = [a for a in filtered if a['severity'] == severity_filter]
        
        if alert_type_filter:
            filtered = [a for a in filtered if a['alert_type'] == alert_type_filter]
        
        return filtered

    def get_user_sessions(self, username):
        """Get all sessions for a user."""
        sessions = []
        for session in self.user_sessions.get(username, []):
            session_copy = session.copy()
            session_copy['login_time'] = session_copy['login_time'].isoformat()
            session_copy['last_activity'] = session_copy['last_activity'].isoformat()
            if session_copy['logout_time']:
                session_copy['logout_time'] = session_copy['logout_time'].isoformat()
            sessions.append(session_copy)
        return sessions

    def get_summary(self):
        """Get overall security summary."""
        alerts_by_type = defaultdict(int)
        alerts_by_severity = defaultdict(int)
        
        for alert in self.alerts:
            alerts_by_type[alert['alert_type']] += 1
            alerts_by_severity[alert['severity']] += 1
        
        return {
            'total_alerts': len(self.alerts),
            'alerts_by_type': dict(alerts_by_type),
            'alerts_by_severity': dict(alerts_by_severity),
            'users_monitored': len(self.user_baselines),
            'scan_timestamp': datetime.now().isoformat()
        }


def generate_test_data(num_records=50):
    """Generate realistic test session data."""
    users = ['alice@company.com', 'bob@company.com', 'charlie@company.com', 'diana@company.com']
    locations = [
        (40.7128, -74.0060, '203.0.113.1'),
        (51.5074, -0.1278, '203.0.113.2'),
        (35.6762, 139.6503, '203.0.113.3'),
        (-33.8688, 151.2093, '203.0.113.4'),
        (48.8566, 2.3522, '203.0.113.5'),
    ]
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15',
    ]
    
    base_time = datetime.now() - timedelta(days=7)
    records = []
    
    for i in range(num_records):
        user = random.choice(users)
        lat, lon, ip = random.choice(locations)
        user_agent = random.choice(user_agents)
        timestamp = base_time + timedelta(minutes=random.randint(0, 10080))
        
        action = random.choice(['login', 'activity', 'activity', 'activity', 'logout'])
        
        record = {
            'username': user,
            'timestamp': timestamp.isoformat(),
            'ip': ip,
            'latitude': lat,
            'longitude': lon,
            'user_agent': user_agent,
            'action': action
        }
        records.append(record)
    
    records.sort(key=lambda x: x['timestamp'])
    return records


def add_anomalies(records):
    """Add realistic anomalies to test data."""
    anomalous_records = []
    
    alice_sessions = [r for r in records if r['username'] == 'alice@company.com']
    if len(alice_sessions) > 1:
        time1 = datetime.fromisoformat(alice_sessions[0]['timestamp'])
        time2 = time1 + timedelta(minutes=5)
        anomalous_records.append({
            'username': 'alice@company.com',
            'timestamp': time2.isoformat(),
            'ip': '203.0.113.10',
            'latitude': -33.8688,
            'longitude': 151.2093,
            'user_agent': alice_sessions[0]['user_agent'],
            'action': 'login'
        })
        anomalous_records.append({
            'username': 'alice@company.com',
            'timestamp': time2.isoformat(),
            'ip': '203.0.113.11',
            'latitude': -33.8688,
            'longitude': 151.2093,
            'user_agent': alice_sessions[0]['user_agent'],
            'action': 'login'
        })
    
    bob_sessions = [r for r in records if r['username'] == 'bob@company.com']
    if bob_sessions:
        time = datetime.fromisoformat(bob_sessions[0]['timestamp']) + timedelta(hours=2)
        anomalous_records.append({
            'username': 'bob@company.com',
            'timestamp': time.isoformat(),
            'ip': '203.0.113.20',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'user_agent': 'MaliciousBot/1.0',
            'action': 'login'
        })
    
    return records + anomalous_records


def main():
    parser = argparse.ArgumentParser(
        description='User Session Anomaly Scanner - Detect compromised sessions via behavioral analytics'
    )
    parser.add_argument(
        '--max-concurrent-sessions',
        type=int,
        default=2,
        help='Maximum allowed concurrent sessions per user (default: 2)'
    )
    parser.add_argument(
        '--impossible-travel-threshold',
        type=int,
        default=900,
        help='Impossible travel speed threshold in km/h (default: 900)'
    )
    parser.add_argument(
        '--severity-filter',
        choices=['low', 'medium', 'high'],
        help='Filter alerts by severity level'
    )
    parser.add_argument(
        '--alert-type-filter',
        choices=['impossible_travel', 'concurrent_sessions_exceeded', 'activity_from_unregistered_ip',
                'anomalous_user_agent', 'anomalous_location', 'activity_without_session'],
        help='Filter alerts by type'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'text'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--user-filter',
        help='Analyze sessions for specific user'
    )
    
    args = parser.parse_args()
    
    scanner = SessionAnomalyScanner(
        max_concurrent_sessions=args.max_concurrent_sessions,
        impossible_travel_threshold_kmh=args.impossible_travel_threshold
    )
    
    test_records = generate_test_data(50)
    test_records = add_anomalies(test_records)
    
    for record in test_records:
        scanner.ingest_session(record)
    
    alerts = scanner.get_alerts(
        severity_filter=args.severity_filter,
        alert_type_filter=args.alert_type_filter
    )
    
    if args.output_format == 'json':
        output = {
            'summary': scanner.get_summary(),
            'alerts': alerts
        }
        
        if args.user_filter:
            output['user_sessions'] = scanner.get_user_sessions(args.user_filter)
        
        print(json.dumps(output, indent=2))
    else:
        summary = scanner.get_summary()
        print(f"Session Anomaly Scan Results")
        print(f"=" * 50)
        print(f"Total Alerts: {summary['total_alerts']}")
        print(f"Users Monitored: {summary['users_monitored']}")
        print(f"\nAlerts by Severity:")
        for severity, count in summary['alerts_by_severity'].items():
            print(f"  {severity}: {count}")
        print(f"\nAlerts by Type:")
        for alert_type, count in summary['alerts_by_type'].items():
            print(f"  {alert_type}: {count}")
        
        print(f"\nTop Alerts:")
        for alert in alerts[:10]:
            print(f"\n  [{alert['severity'].upper()}] {alert['alert_type']}")
            print(f"    Time: {alert['timestamp']}")
            if 'username' in alert['details']:
                print(f"    User: {alert['details']['username']}")


if __name__ == '__main__':
    main()
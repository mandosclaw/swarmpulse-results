#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Behavioral baseline engine
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-29T13:08:08.765Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Behavioral baseline engine for SaaS breach detection
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @sue
DATE: 2025-01-24

Per-user activity model: access patterns, data volumes, geo. 30-day rolling window.
Detects: credential stuffing, impossible travel, mass download, privilege creep.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
import math
import hashlib
import random


class BehavioralBaselineEngine:
    def __init__(self, rolling_window_days=30, anomaly_threshold_sigma=3.0):
        self.rolling_window_days = rolling_window_days
        self.anomaly_threshold_sigma = anomaly_threshold_sigma
        self.user_profiles = defaultdict(lambda: {
            'access_times': [],
            'locations': [],
            'data_volumes': [],
            'privilege_changes': [],
            'resource_types': defaultdict(int),
            'last_activity_time': None,
            'last_location': None,
            'ip_addresses': set()
        })
        self.baseline_stats = defaultdict(lambda: {
            'access_frequency': None,
            'avg_data_volume': None,
            'stdev_data_volume': None,
            'common_locations': [],
            'common_times': [],
            'resource_distribution': {}
        })
        self.anomalies = []

    def ingest_log(self, log_entry):
        """Parse and ingest a single audit log entry."""
        timestamp = log_entry.get('timestamp')
        user_id = log_entry.get('user_id')
        action = log_entry.get('action')
        location = log_entry.get('location', 'unknown')
        ip_address = log_entry.get('ip_address', 'unknown')
        data_volume = log_entry.get('data_volume', 0)
        resource_type = log_entry.get('resource_type', 'unknown')
        privilege_level = log_entry.get('privilege_level')

        if not user_id or not timestamp:
            return

        profile = self.user_profiles[user_id]
        profile['access_times'].append(timestamp)
        profile['locations'].append(location)
        profile['data_volumes'].append(data_volume)
        profile['resource_types'][resource_type] += 1
        profile['ip_addresses'].add(ip_address)
        profile['last_activity_time'] = timestamp
        profile['last_location'] = location

        if privilege_level:
            profile['privilege_changes'].append({
                'timestamp': timestamp,
                'level': privilege_level
            })

    def compute_baseline(self):
        """Compute baseline statistics for each user over rolling window."""
        cutoff_time = datetime.now() - timedelta(days=self.rolling_window_days)

        for user_id, profile in self.user_profiles.items():
            access_times = [t for t in profile['access_times'] if t >= cutoff_time]
            data_volumes = [v for v in profile['data_volumes'] if v > 0]

            baseline = self.baseline_stats[user_id]
            baseline['access_frequency'] = len(access_times) / self.rolling_window_days if access_times else 0

            if data_volumes:
                baseline['avg_data_volume'] = mean(data_volumes)
                baseline['stdev_data_volume'] = stdev(data_volumes) if len(data_volumes) > 1 else 0
            else:
                baseline['avg_data_volume'] = 0
                baseline['stdev_data_volume'] = 0

            location_counts = defaultdict(int)
            for loc in profile['locations']:
                if loc:
                    location_counts[loc] += 1
            baseline['common_locations'] = sorted(
                location_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            total_resources = sum(profile['resource_types'].values())
            if total_resources > 0:
                baseline['resource_distribution'] = {
                    res: count / total_resources
                    for res, count in profile['resource_types'].items()
                }

    def detect_anomalies(self, new_log_entry):
        """Detect anomalies in a new log entry against baseline."""
        anomaly_flags = []
        user_id = new_log_entry.get('user_id')
        timestamp = new_log_entry.get('timestamp')
        location = new_log_entry.get('location', 'unknown')
        ip_address = new_log_entry.get('ip_address', 'unknown')
        data_volume = new_log_entry.get('data_volume', 0)
        action = new_log_entry.get('action', 'unknown')

        if user_id not in self.baseline_stats:
            return []

        baseline = self.baseline_stats[user_id]
        profile = self.user_profiles[user_id]

        # Credential stuffing: multiple failed login attempts
        if action == 'login_failed':
            recent_failed = sum(1 for t in profile['access_times']
                              if t >= datetime.now() - timedelta(minutes=5))
            if recent_failed > 5:
                anomaly_flags.append({
                    'type': 'credential_stuffing',
                    'severity': 'high',
                    'description': f'Multiple failed login attempts ({recent_failed} in 5 min)',
                    'value': recent_failed
                })

        # Impossible travel: same user in different locations within short time
        if profile['last_location'] and profile['last_activity_time']:
            time_diff = (timestamp - profile['last_activity_time']).total_seconds() / 3600
            if time_diff < 1 and location != profile['last_location']:
                anomaly_flags.append({
                    'type': 'impossible_travel',
                    'severity': 'critical',
                    'description': f'Same user in {profile["last_location"]} then {location} within {time_diff:.2f} hours',
                    'locations': [profile['last_location'], location],
                    'hours_apart': time_diff
                })

        # Mass download: unusual data volume spike
        if data_volume > 0 and baseline['avg_data_volume'] > 0:
            z_score = (data_volume - baseline['avg_data_volume']) / (baseline['stdev_data_volume'] + 1e-6)
            if z_score > self.anomaly_threshold_sigma:
                anomaly_flags.append({
                    'type': 'mass_download',
                    'severity': 'high',
                    'description': f'Data volume {data_volume}MB exceeds baseline by {z_score:.2f} standard deviations',
                    'data_volume_mb': data_volume,
                    'baseline_avg_mb': baseline['avg_data_volume'],
                    'z_score': z_score
                })

        # Privilege creep: unexpected privilege elevation
        if new_log_entry.get('privilege_level'):
            if len(profile['privilege_changes']) > 0:
                last_privilege = profile['privilege_changes'][-1]['level']
                new_privilege = new_log_entry.get('privilege_level')
                if self._is_privilege_escalation(last_privilege, new_privilege):
                    anomaly_flags.append({
                        'type': 'privilege_creep',
                        'severity': 'high',
                        'description': f'Privilege escalation from {last_privilege} to {new_privilege}',
                        'from_level': last_privilege,
                        'to_level': new_privilege
                    })

        # Geolocation anomaly: access from unusual location
        baseline_locs = [loc for loc, _ in baseline['common_locations']]
        if location not in baseline_locs and location != 'unknown' and len(baseline_locs) > 0:
            anomaly_flags.append({
                'type': 'unusual_location',
                'severity': 'medium',
                'description': f'Access from new location: {location}',
                'location': location,
                'baseline_locations': baseline_locs
            })

        # IP address anomaly: new IP address
        if ip_address != 'unknown' and ip_address not in profile['ip_addresses'] and len(profile['ip_addresses']) > 0:
            anomaly_flags.append({
                'type': 'new_ip_address',
                'severity': 'low',
                'description': f'Access from new IP: {ip_address}',
                'ip_address': ip_address,
                'known_ips': list(profile['ip_addresses'])[:5]
            })

        # Store anomalies
        for flag in anomaly_flags:
            anomaly = {
                'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                'user_id': user_id,
                'action': action,
                **flag
            }
            self.anomalies.append(anomaly)

        return anomaly_flags

    def _is_privilege_escalation(self, from_level, to_level):
        """Determine if privilege change is an escalation."""
        privilege_hierarchy = {'viewer': 0, 'editor': 1, 'admin': 2, 'super_admin': 3}
        from_rank = privilege_hierarchy.get(from_level, -1)
        to_rank = privilege_hierarchy.get(to_level, -1)
        return to_rank > from_rank

    def get_report(self):
        """Generate comprehensive behavioral baseline report."""
        return {
            'report_time': datetime.now().isoformat(),
            'rolling_window_days': self.rolling_window_days,
            'total_users': len(self.user_profiles),
            'total_anomalies': len(self.anomalies),
            'anomalies_by_type': self._count_anomalies_by_type(),
            'high_risk_users': self._get_high_risk_users(),
            'detailed_anomalies': self.anomalies[-100:]  # Last 100
        }

    def _count_anomalies_by_type(self):
        """Count anomalies by type."""
        counts = defaultdict(int)
        for anomaly in self.anomalies:
            counts[anomaly.get('type', 'unknown')] += 1
        return dict(counts)

    def _get_high_risk_users(self):
        """Identify users with multiple anomalies."""
        user_anomaly_counts = defaultdict(int)
        for anomaly in self.anomalies:
            user_anomaly_counts[anomaly['user_id']] += 1

        high_risk = sorted(
            user_anomaly_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return [
            {
                'user_id': user_id,
                'anomaly_count': count,
                'risk_score': min(count * 10, 100)
            }
            for user_id, count in high_risk
        ]

    def export_baseline(self):
        """Export baseline profiles as JSON-serializable dict."""
        export = {}
        for user_id, baseline in self.baseline_stats.items():
            export[user_id] = {
                'access_frequency_per_day': round(baseline['access_frequency'], 2),
                'avg_data_volume_mb': round(baseline['avg_data_volume'], 2),
                'stdev_data_volume_mb': round(baseline['stdev_data_volume'], 2),
                'common_locations': [loc for loc, _ in baseline['common_locations']],
                'resource_distribution': {k: round(v, 3) for k, v in baseline['resource_distribution'].items()}
            }
        return export


def generate_sample_logs(num_logs=500, num_users=20):
    """Generate realistic sample audit logs for testing."""
    logs = []
    base_time = datetime.now() - timedelta(days=30)
    locations = ['USA-NYC', 'USA-SF', 'USA-LA', 'UK-LON', 'IN-BLR', 'CN-SH', 'DE-BER']
    actions = ['login', 'login_failed', 'file_download', 'file_upload', 'privilege_change', 'api_call']
    resource_types = ['spreadsheet', 'document', 'email', 'code_repo', 'database', 'api']
    privilege_levels = ['viewer', 'editor', 'admin']

    for i in range(num_logs):
        user_id = f'user_{random.randint(1, num_users)}'
        timestamp = base_time + timedelta(
            hours=random.randint(0, 30 * 24),
            minutes=random.randint(0, 60)
        )
        action = random.choice(actions)
        location = random.choice(locations)
        ip_address = f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}'
        data_volume = random.randint(0, 5000) if action in ['file_download', 'file_upload'] else 0
        resource_type = random.choice(resource_types)
        privilege_level = random.choice(privilege_levels) if action == 'privilege_change' else None

        logs.append({
            'timestamp': timestamp,
            'user_id': user_id,
            'action': action,
            'location': location,
            'ip_address': ip_address,
            'data_volume': data_volume,
            'resource_type': resource_type,
            'privilege_level': privilege_level
        })

    return sorted(logs, key=lambda x: x['timestamp'])


def generate_anomalous_logs(num_anomalies=10):
    """Generate logs with deliberate anomalies."""
    anomalies = []
    base_time = datetime.now()

    # Credential stuffing
    for _ in range(3):
        user_id = f'user_5'
        for i in range(7):
            anomalies.append({
                'timestamp': base_time - timedelta(minutes=4 - i),
                'user_id': user_id,
                'action': 'login_failed',
                'location': 'USA-NYC',
                'ip_address': '192.168.1.100',
                'data_volume': 0,
                'resource_type': 'api',
                'privilege_level': None
            })

    # Impossible travel
    anomalies.append({
        'timestamp': base_time - timedelta(minutes=30),
        'user_id': 'user_12',
        'action': 'file_download',
        'location': 'UK-LON',
        'ip_address': '10.0.0.1',
        'data_volume': 100,
        'resource_type': 'spreadsheet',
        'privilege_level': None
    })
    anomalies.append({
        'timestamp': base_time - timedelta(minutes=20),
        'user_id': 'user_12',
        'action': 'file_upload',
        'location': 'CN-SH',
        'ip_address': '10.0.0.2',
        'data_volume': 50,
        'resource_type': 'spreadsheet',
        'privilege_level': None
    })

    # Mass download
    anomalies.append({
        'timestamp': base_time - timedelta(hours=2),
        'user_id': 'user_8',
        'action': 'file_download',
        'location': 'USA-SF',
        'ip_address': '172.16.0.1',
        'data_volume': 50000,
        'resource_type': 'database',
        'privilege_level': None
    })

    # Privilege creep
    anomalies.append({
        'timestamp': base_time - timedelta(hours=1),
        'user_id': '
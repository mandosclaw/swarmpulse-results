#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build behavioral baseline engine
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-31T19:14:47.460Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build behavioral baseline engine
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @echo
DATE: 2024

Implements ML-powered behavioral baseline creation for SaaS security:
- User activity profiling
- Baseline statistical models per user
- Anomaly scoring mechanisms
- Impossible travel detection
- Automated alerting on deviations
"""

import argparse
import json
import sys
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import hashlib
import random
import string


class BehavioralBaseline:
    """Statistical behavioral baseline engine for user activity analysis."""
    
    def __init__(self, min_samples: int = 10):
        self.min_samples = min_samples
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.activity_logs: List[Dict[str, Any]] = []
        self.baseline_trained = False
        
    def ingest_log(self, log_entry: Dict[str, Any]) -> None:
        """Ingest a single audit log entry."""
        required_fields = ['user_id', 'timestamp', 'action', 'ip_address', 'latitude', 'longitude']
        
        for field in required_fields:
            if field not in log_entry:
                raise ValueError(f"Missing required field: {field}")
        
        log_entry['timestamp'] = datetime.fromisoformat(log_entry['timestamp'])
        self.activity_logs.append(log_entry)
    
    def train_baseline(self) -> Dict[str, Any]:
        """Train behavioral baseline from ingested logs."""
        if len(self.activity_logs) < self.min_samples:
            raise ValueError(f"Insufficient logs for training. Need {self.min_samples}, have {len(self.activity_logs)}")
        
        user_activities = defaultdict(list)
        
        for log in self.activity_logs:
            user_id = log['user_id']
            user_activities[user_id].append(log)
        
        training_stats = {
            'total_users': len(user_activities),
            'total_logs': len(self.activity_logs),
            'trained_at': datetime.utcnow().isoformat(),
            'profiles': {}
        }
        
        for user_id, activities in user_activities.items():
            if len(activities) < self.min_samples:
                continue
            
            profile = self._build_user_profile(user_id, activities)
            self.user_profiles[user_id] = profile
            training_stats['profiles'][user_id] = {
                'activity_count': len(activities),
                'baseline_actions': list(profile['action_distribution'].keys()),
                'common_ips': list(profile['ip_distribution'].keys())[:5],
                'location_cluster_count': len(profile['location_clusters'])
            }
        
        self.baseline_trained = True
        return training_stats
    
    def _build_user_profile(self, user_id: str, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build comprehensive behavioral profile for a user."""
        actions = []
        ips = []
        locations = []
        hours_active = []
        days_active = set()
        
        for activity in activities:
            actions.append(activity['action'])
            ips.append(activity['ip_address'])
            locations.append((activity['latitude'], activity['longitude']))
            
            ts = activity['timestamp']
            hours_active.append(ts.hour)
            days_active.add(ts.weekday())
        
        action_counts = defaultdict(int)
        for action in actions:
            action_counts[action] += 1
        
        action_distribution = {
            action: count / len(actions) 
            for action, count in action_counts.items()
        }
        
        ip_counts = defaultdict(int)
        for ip in ips:
            ip_counts[ip] += 1
        
        ip_distribution = {
            ip: count / len(ips)
            for ip, count in ip_counts.items()
        }
        
        location_clusters = self._cluster_locations(locations)
        
        hour_mean = statistics.mean(hours_active) if hours_active else 12
        hour_stdev = statistics.stdev(hours_active) if len(hours_active) > 1 else 2
        
        profile = {
            'user_id': user_id,
            'action_distribution': action_distribution,
            'ip_distribution': ip_distribution,
            'location_clusters': location_clusters,
            'preferred_hours': {
                'mean': hour_mean,
                'stdev': hour_stdev
            },
            'active_days': list(days_active),
            'activity_count': len(activities),
            'geographic_spread_km': self._calc_geographic_spread(locations)
        }
        
        return profile
    
    def _cluster_locations(self, locations: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Simple location clustering using k-means-like approach."""
        if not locations or len(locations) < 2:
            return [{'center': locations[0] if locations else (0, 0), 'count': len(locations)}]
        
        clusters = []
        clustered = [False] * len(locations)
        
        for i, (lat, lon) in enumerate(locations):
            if clustered[i]:
                continue
            
            cluster = [(lat, lon)]
            clustered[i] = True
            
            for j, (lat2, lon2) in enumerate(locations[i+1:], i+1):
                if clustered[j]:
                    continue
                
                dist = self._haversine_distance(lat, lon, lat2, lon2)
                if dist < 100:
                    cluster.append((lat2, lon2))
                    clustered[j] = True
            
            center_lat = statistics.mean([c[0] for c in cluster])
            center_lon = statistics.mean([c[1] for c in cluster])
            
            clusters.append({
                'center': (center_lat, center_lon),
                'count': len(cluster)
            })
        
        return clusters
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km."""
        R = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calc_geographic_spread(self, locations: List[Tuple[float, float]]) -> float:
        """Calculate max distance between any two locations."""
        if len(locations) < 2:
            return 0.0
        
        max_dist = 0.0
        for i, (lat1, lon1) in enumerate(locations):
            for lat2, lon2 in locations[i+1:]:
                dist = self._haversine_distance(lat1, lon1, lat2, lon2)
                max_dist = max(max_dist, dist)
        
        return max_dist
    
    def score_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Score an activity for anomalies against baseline."""
        if not self.baseline_trained:
            raise RuntimeError("Baseline not trained. Call train_baseline() first.")
        
        user_id = activity['user_id']
        
        if user_id not in self.user_profiles:
            return {
                'user_id': user_id,
                'anomaly_score': 0.5,
                'anomalies': ['unknown_user'],
                'risk_level': 'MEDIUM',
                'details': 'User not in baseline'
            }
        
        profile = self.user_profiles[user_id]
        anomalies = []
        scores = []
        
        action_score = self._score_action(activity['action'], profile)
        scores.append(action_score)
        if action_score > 0.7:
            anomalies.append(f"unusual_action:{activity['action']}")
        
        ip_score = self._score_ip(activity['ip_address'], profile)
        scores.append(ip_score)
        if ip_score > 0.7:
            anomalies.append(f"new_ip:{activity['ip_address']}")
        
        location_score = self._score_location(
            (activity['latitude'], activity['longitude']),
            profile
        )
        scores.append(location_score)
        if location_score > 0.7:
            anomalies.append("new_location")
        
        time_score = self._score_time(activity['timestamp'], profile)
        scores.append(time_score)
        if time_score > 0.7:
            anomalies.append("unusual_time")
        
        impossible_travel = self._check_impossible_travel(activity, profile)
        if impossible_travel:
            anomalies.append(f"impossible_travel:{impossible_travel}")
            scores.append(0.95)
        
        anomaly_score = statistics.mean(scores) if scores else 0.0
        
        if anomaly_score > 0.8:
            risk_level = 'CRITICAL'
        elif anomaly_score > 0.6:
            risk_level = 'HIGH'
        elif anomaly_score > 0.4:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'user_id': user_id,
            'anomaly_score': round(anomaly_score, 3),
            'anomalies': anomalies,
            'risk_level': risk_level,
            'component_scores': {
                'action': round(action_score, 3),
                'ip': round(ip_score, 3),
                'location': round(location_score, 3),
                'time': round(time_score, 3)
            },
            'timestamp': activity['timestamp'].isoformat()
        }
    
    def _score_action(self, action: str, profile: Dict[str, Any]) -> float:
        """Score how anomalous an action is."""
        if action in profile['action_distribution']:
            probability = profile['action_distribution'][action]
            return 1.0 - probability
        else:
            return 0.9
    
    def _score_ip(self, ip: str, profile: Dict[str, Any]) -> float:
        """Score how anomalous an IP is."""
        if ip in profile['ip_distribution']:
            probability = profile['ip_distribution'][ip]
            return 1.0 - probability
        else:
            return 0.85
    
    def _score_location(self, location: Tuple[float, float], profile: Dict[str, Any]) -> float:
        """Score how anomalous a location is."""
        for cluster in profile['location_clusters']:
            center = cluster['center']
            dist = self._haversine_distance(location[0], location[1], center[0], center[1])
            if dist < 50:
                return 0.1
        
        return 0.8
    
    def _score_time(self, timestamp: datetime, profile: Dict[str, Any]) -> float:
        """Score how anomalous a timestamp is."""
        hour = timestamp.hour
        day = timestamp.weekday()
        
        if day not in profile['active_days']:
            return 0.7
        
        mean_hour = profile['preferred_hours']['mean']
        stdev_hour = profile['preferred_hours']['stdev']
        
        if stdev_hour == 0:
            return 0.0 if hour == mean_hour else 0.5
        
        z_score = abs((hour - mean_hour) / stdev_hour)
        
        if z_score > 3:
            return 0.9
        elif z_score > 2:
            return 0.7
        elif z_score > 1:
            return 0.4
        else:
            return 0.1
    
    def _check_impossible_travel(self, activity: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """Detect impossible travel based on geographic and temporal constraints."""
        recent_activities = [
            a for a in self.activity_logs
            if a['user_id'] == activity['user_id']
            and a['timestamp'] < activity['timestamp']
        ]
        
        if not recent_activities:
            return ""
        
        last_activity = max(recent_activities, key=lambda x: x['timestamp'])
        time_diff_minutes = (activity['timestamp'] - last_activity['timestamp']).total_seconds() / 60
        
        distance_km = self._haversine_distance(
            last_activity['latitude'],
            last_activity['longitude'],
            activity['latitude'],
            activity['longitude']
        )
        
        max_possible_speed_kmh = 900
        max_distance_km = (time_diff_minutes / 60) * max_possible_speed_kmh
        
        if distance_km > max_distance_km:
            return f"traveled_{distance_km:.0f}km_in_{time_diff_minutes:.0f}min"
        
        return ""
    
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Retrieve baseline profile for a user."""
        if user_id not in self.user_profiles:
            return {'error': f'No profile for user {user_id}'}
        
        profile = self.user_profiles[user_id].copy()
        profile['action_distribution'] = {
            k: round(v, 3) for k, v in profile['action_distribution'].items()
        }
        profile['ip_distribution'] = {
            k: round(v, 3) for k, v in profile['ip_distribution'].items()
        }
        
        return profile
    
    def export_baselines(self) -> Dict[str, Any]:
        """Export all trained baselines."""
        return {
            'trained': self.baseline_trained,
            'trained_at': datetime.utcnow().isoformat(),
            'user_count': len(self.user_profiles),
            'profiles': {
                user_id: self.get_profile(user_id)
                for user_id in self.user_profiles
            }
        }


def generate_sample_logs(user_count: int = 3, logs_per_user: int = 50) -> List[Dict[str, Any]]:
    """Generate realistic sample audit logs for testing."""
    logs = []
    actions = ['login', 'logout', 'api_call', 'file_download', 'file_upload', 'password_change', 'settings_update']
    
    base_locations = [
        (40.7128, -74.0060),
        (34.0522, -118.2437),
        (41.8781, -87.6298),
        (37.7749, -122.4194),
        (51.5074, -0.1278)
    ]
    
    base_ips = [
        '203.0.113.42',
        '198.51.100.89',
        '192.0.2.15',
        '203.0.113.200',
        '198.51.100.1'
    ]
    
    start_time = datetime.utcnow() - timedelta(days=30)
    
    for user_idx in range(user_count):
        user_id = f"user_{user_idx:03d}"
        user_location = base_locations[user_idx % len(base_locations)]
        user_ip = base_ips[user_idx % len(base_ips)]
        
        for log_idx in range(logs_per_user):
            timestamp = start_time + timedelta(
                hours=random.randint(0, 720),
                minutes=random.randint(0, 59)
            )
            
            lat_noise = random.uniform(-0.5, 0.5)
            lon_noise = random.uniform(-0.5, 0.5)
            
            log_entry = {
                'user_id': user_id,
                'timestamp': timestamp.isoformat(),
                'action': random.choice(actions),
                'ip_address': user_ip if random.random() > 0.2 else base_ips[random.randint(0, len(base_ips)-1)],
                'latitude': user_location[0] + lat_noise,
                'longitude': user_location[1] + lon_noise,
                'resource': f"/api/resource_{random.randint(1, 100)}"
            }
            logs.append(log_entry)
    
    return logs


def generate_anomalous_activity(baseline_engine: BehavioralBaseline, user_id: str) -> Dict[str, Any]:
    """Generate an anomalous activity for testing detection."""
    if user_id not in baseline_engine.user_profiles:
        user_id = list(baseline_engine.user_profiles.keys())[0]
    
    profile = baseline_engine.user_profiles[user_id]
    
    return {
        'user_id': user_id,
        'timestamp': (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        'action': 'sensitive_export',
        'ip_address': '203.0.113.99',
        'latitude': 51.5074,
        'longitude': -0.1278,
        'resource': '/api/data_export'
    }


def main():
    parser = argparse.ArgumentParser(
        description='SaaS Behavioral Baseline Engine - Breach Detection'
    )
    parser.add_argument(
        '--mode',
        choices=['train', 'score', 'profile', 'export', 'demo'],
        default='demo',
        help='Operation mode'
    )
    parser.add_argument(
        '--input-file',
        type=str,
        help='Input log file (JSON lines format)'
    )
    parser.add_argument(
        '--activity-file',
        type=str,
        help='Activity to score (JSON format)'
    )
    parser.add_argument(
        '--user-id',
        type=str,
        help='User ID for profile retrieval'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file for results (JSON format)'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=10,
        help='Minimum samples per user for baseline training'
    )
    parser.add_argument(
        '--demo-users',
        type=int,
        default=3,
        help='Number of users for demo mode'
    )
    parser.add_argument(
        '--demo-logs-per-user',
        type=int,
        default=50,
        help='Logs per user for demo mode'
    )
    
    args = parser.parse_args()
    
    engine = BehavioralBaseline(min_samples=args.min_samples)
    
    if args.mode == 'demo':
        print("=== SaaS Behavioral Baseline Engine - DEMO ===\n")
        
        print(f"Generating sample logs ({args.demo_users} users, {args.demo_logs_per_user} logs/user)...")
        logs = generate_sample_logs(args.demo_users, args.demo_logs_per_user)
        
        for log in logs:
            engine.ingest_log(log)
        
        print(f"Ingested {len(logs)} log entries\n")
        
        print("Training baseline...")
        training_stats = engine.train_baseline()
        print(f"Trained on {training_stats['total_users']} users")
        print(f"Profiles created: {len(training_stats['profiles'])}\n")
        
        user_ids = list(engine.user_profiles.keys())
        if user_ids:
            print(f"Sample profile for {user_ids[0]}:")
            profile = engine.get_profile(user_ids[0])
            print(json.dumps({k: v for k, v in profile.items() if k != 'location_clusters'}, indent=2))
            print()
        
        print("Scoring normal activity...")
        normal_activity = {
            'user_id': user_ids[0],
            'timestamp': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            'action': 'login',
            'ip_address': list(engine.user_profiles[user_ids[0]]['ip_distribution'].keys())[0],
            'latitude': engine.user_profiles[user_ids[0]]['location_clusters'][0]['center'][0],
            'longitude': engine.user_profiles[user_ids[0]]['location_clusters'][0]['center'][1]
        }
        
        score = engine.score_activity(normal_activity)
        print(f"Normal activity score: {json.dumps(score, indent=2)}\n")
        
        print("Scoring anomalous activity...")
        anomalous = generate_anomalous_activity(engine, user_ids[0])
        anomaly_score = engine.score_activity(anomalous)
        print(f"Anomalous activity score: {json.dumps(anomaly_score, indent=2)}\n")
        
        if args.output_file:
            output = {
                'training_stats': training_stats,
                'normal_activity_score': score,
                'anomalous_activity_score': anomaly_score
            }
            with open(args.output_file, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"Results written to {args.output_file}")
    
    elif args.mode == 'train':
        if not args.input_file:
            print("Error: --input-file required for train mode", file=sys.stderr)
            sys.exit(1)
        
        with open(args.input_file, 'r') as f:
            for line in f:
                log = json.loads(line.strip())
                engine.ingest_log(log)
        
        stats = engine.train_baseline()
        
        output = stats
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))
    
    elif args.mode == 'score':
        if not args.input_file or not args.activity_file:
            print("Error: --input-file and --activity-file required for score mode", file=sys.stderr)
            sys.exit(1)
        
        with open(args.input_file, 'r') as f:
            for line in f:
                log = json.loads(line.strip())
                engine.ingest_log(log)
        
        engine.train_baseline()
        
        with open(args.activity_file, 'r') as f:
            activity = json.load(f)
        
        score = engine.score_activity(activity)
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(score, f, indent=2)
        else:
            print(json.dumps(score, indent=2))
    
    elif args.mode == 'profile':
        if not args.input_file or not args.user_id:
            print("Error: --input-file and --user-id required for profile mode", file=sys.stderr)
            sys.exit(1)
        
        with open(args.input_file, 'r') as f:
            for line in f:
                log = json.loads(line.strip())
                engine.ingest_log(log)
        
        engine.train_baseline()
        
        profile = engine.get_profile(args.user_id)
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(profile, f, indent=2)
        else:
            print(json.dumps(profile, indent=2))
    
    elif args.mode == 'export':
        if not args.input_file:
            print("Error: --input-file required for export mode", file=sys.stderr)
            sys.exit(1)
        
        with open(args.input_file, 'r') as f:
            for line in f:
                log = json.loads(line.strip())
                engine.ingest_log(log)
        
        engine.train_baseline()
        
        export = engine.export_baselines()
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(export, f, indent=2)
        else:
            print(json.dumps(export, indent=2))


if __name__ == '__main__':
    main()
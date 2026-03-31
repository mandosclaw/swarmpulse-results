#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build registry stream monitor
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-31T18:52:45.619Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build registry stream monitor
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024-01-15

Monitors open-source package registries for supply chain attacks including
typosquatting detection, behavioral diffing, SBOM generation, and maintainer
change alerts.
"""

import argparse
import json
import hashlib
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import urllib.request
import urllib.error


@dataclass
class PackageMetadata:
    name: str
    version: str
    timestamp: str
    maintainer: str
    size: int
    hash_sha256: str
    dependencies: List[str]
    files: List[str]


@dataclass
class RegistryEvent:
    event_type: str
    package_name: str
    version: str
    timestamp: str
    severity: str
    details: Dict[str, Any]


class TyposquattingDetector:
    """Detects potential typosquatting attacks on package names."""
    
    def __init__(self, levenshtein_threshold: int = 2):
        self.threshold = levenshtein_threshold
        self.known_packages = set()
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _has_suspicious_patterns(self, package_name: str) -> bool:
        """Check for suspicious patterns in package names."""
        suspicious_patterns = [
            r'_+',
            r'-{2,}',
            r'\.{2,}',
            r'\d{5,}',
            r'(npm|pypi|pip|ruby|gem|crate)',
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, package_name, re.IGNORECASE):
                return True
        return False
    
    def check_typosquatting(self, package_name: str) -> Tuple[bool, List[str]]:
        """Check if package_name is a potential typosquat of known packages."""
        if not self.known_packages:
            return False, []
        
        if self._has_suspicious_patterns(package_name):
            return True, []
        
        suspects = []
        for known_pkg in self.known_packages:
            distance = self._levenshtein_distance(package_name.lower(), known_pkg.lower())
            if 0 < distance <= self.threshold:
                suspects.append(known_pkg)
        
        return len(suspects) > 0, suspects
    
    def register_package(self, package_name: str):
        """Register a known legitimate package."""
        self.known_packages.add(package_name.lower())


class BehavioralDiffer:
    """Detects anomalous behavior changes in packages."""
    
    def __init__(self):
        self.package_history = defaultdict(list)
        self.baseline_metrics = {}
    
    def _calculate_metrics(self, metadata: PackageMetadata) -> Dict[str, Any]:
        """Calculate behavioral metrics from package metadata."""
        return {
            'size': metadata.size,
            'file_count': len(metadata.files),
            'dependency_count': len(metadata.dependencies),
            'maintainer': metadata.maintainer,
            'hash': metadata.hash_sha256,
        }
    
    def _detect_file_changes(self, old_files: List[str], new_files: List[str]) -> Dict[str, Any]:
        """Detect file additions, removals, and modifications."""
        old_set = set(old_files)
        new_set = set(new_files)
        
        return {
            'added_files': list(new_set - old_set),
            'removed_files': list(old_set - new_set),
            'count_delta': len(new_files) - len(old_files),
        }
    
    def record_version(self, metadata: PackageMetadata):
        """Record package version for future comparison."""
        metrics = self._calculate_metrics(metadata)
        self.package_history[metadata.name].append({
            'version': metadata.version,
            'timestamp': metadata.timestamp,
            'metrics': metrics,
            'files': metadata.files,
        })
    
    def detect_anomalies(self, metadata: PackageMetadata) -> List[Dict[str, Any]]:
        """Detect behavioral anomalies compared to historical baseline."""
        package_name = metadata.name
        current_metrics = self._calculate_metrics(metadata)
        anomalies = []
        
        if package_name not in self.package_history or len(self.package_history[package_name]) == 0:
            self.record_version(metadata)
            return anomalies
        
        history = self.package_history[package_name]
        if len(history) > 0:
            last_version = history[-1]
            last_metrics = last_version['metrics']
            
            size_increase_ratio = (current_metrics['size'] / max(last_metrics['size'], 1)) - 1
            if abs(size_increase_ratio) > 0.5:
                anomalies.append({
                    'type': 'size_change',
                    'severity': 'medium',
                    'details': {
                        'old_size': last_metrics['size'],
                        'new_size': current_metrics['size'],
                        'ratio': size_increase_ratio,
                    }
                })
            
            dep_change = current_metrics['dependency_count'] - last_metrics['dependency_count']
            if abs(dep_change) > 5:
                anomalies.append({
                    'type': 'dependency_change',
                    'severity': 'medium' if dep_change > 0 else 'low',
                    'details': {
                        'old_count': last_metrics['dependency_count'],
                        'new_count': current_metrics['dependency_count'],
                        'delta': dep_change,
                    }
                })
            
            if current_metrics['maintainer'] != last_metrics['maintainer']:
                anomalies.append({
                    'type': 'maintainer_change',
                    'severity': 'high',
                    'details': {
                        'old_maintainer': last_metrics['maintainer'],
                        'new_maintainer': current_metrics['maintainer'],
                    }
                })
            
            file_changes = self._detect_file_changes(last_version['files'], metadata.files)
            suspicious_additions = [f for f in file_changes['added_files'] 
                                   if any(x in f.lower() for x in ['.exe', '.dll', '.so', '.dylib', '.bin'])]
            if suspicious_additions:
                anomalies.append({
                    'type': 'suspicious_binaries',
                    'severity': 'critical',
                    'details': {
                        'files': suspicious_additions,
                    }
                })
        
        self.record_version(metadata)
        return anomalies


class SBOMGenerator:
    """Generates Software Bill of Materials for packages."""
    
    @staticmethod
    def generate_sbom(metadata: PackageMetadata) -> Dict[str, Any]:
        """Generate SBOM in simplified format."""
        return {
            'sbom_version': '1.3',
            'name': metadata.name,
            'version': metadata.version,
            'generated_at': datetime.utcnow().isoformat(),
            'package': {
                'name': metadata.name,
                'version': metadata.version,
                'maintainer': metadata.maintainer,
                'hash': metadata.hash_sha256,
            },
            'components': [
                {
                    'type': 'library',
                    'name': dep,
                    'version': 'unknown',
                } for dep in metadata.dependencies
            ],
            'files': metadata.files,
        }


class RegistryStreamMonitor:
    """Main registry stream monitoring engine."""
    
    def __init__(self, registry_url: str = "https://registry.npmjs.org", check_interval: int = 5):
        self.registry_url = registry_url
        self.check_interval = check_interval
        self.typosquat_detector = TyposquattingDetector()
        self.behavior_differ = BehavioralDiffer()
        self.sbom_generator = SBOMGenerator()
        self.events = []
        self.package_cache = {}
        self.baseline_packages = set()
    
    def _fetch_package_metadata(self, package_name: str) -> PackageMetadata | None:
        """Fetch package metadata from registry."""
        try:
            url = f"{self.registry_url}/{package_name}"
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'OSS-Supply-Chain-Monitor/1.0'}
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if 'dist-tags' not in data or 'latest' not in data['dist-tags']:
                return None
            
            latest_version = data['dist-tags']['latest']
            version_data = data['versions'].get(latest_version, {})
            
            dependencies = list(version_data.get('dependencies', {}).keys())
            
            size = version_data.get('dist', {}).get('uncompressed', 0)
            hash_val = version_data.get('dist', {}).get('shasum', '')
            
            maintainers = data.get('maintainers', [])
            maintainer = maintainers[0].get('name', 'unknown') if maintainers else 'unknown'
            
            return PackageMetadata(
                name=package_name,
                version=latest_version,
                timestamp=datetime.utcnow().isoformat(),
                maintainer=maintainer,
                size=size,
                hash_sha256=hash_val,
                dependencies=dependencies,
                files=[f"{package_name}@{latest_version}/{i}" for i in range(min(5, len(dependencies) + 1))],
            )
        except Exception as e:
            return None
    
    def _generate_event(self, event_type: str, package_name: str, version: str, 
                       severity: str, details: Dict[str, Any]) -> RegistryEvent:
        """Create a registry event."""
        return RegistryEvent(
            event_type=event_type,
            package_name=package_name,
            version=version,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity,
            details=details,
        )
    
    def register_baseline_package(self, package_name: str):
        """Register a package as part of baseline."""
        self.baseline_packages.add(package_name.lower())
        self.typosquat_detector.register_package(package_name)
    
    def monitor_package(self, package_name: str) -> List[RegistryEvent]:
        """Monitor a single package for anomalies."""
        events = []
        
        metadata = self._fetch_package_metadata(package_name)
        if not metadata:
            return events
        
        is_typosquat, suspects = self.typosquat_detector.check_typosquatting(package_name)
        if is_typosquat:
            events.append(self._generate_event(
                'typosquatting_detected',
                package_name,
                metadata.version,
                'high',
                {'suspected_targets': suspects}
            ))
        
        behavioral_anomalies = self.behavior_differ.detect_anomalies(metadata)
        for anomaly in behavioral_anomalies:
            severity_map = {
                'size_change': 'medium',
                'dependency_change': 'medium',
                'maintainer_change': 'high',
                'suspicious_binaries': 'critical',
            }
            events.append(self._generate_event(
                f'behavioral_{anomaly["type"]}',
                package_name,
                metadata.version,
                anomaly['severity'],
                anomaly['details']
            ))
        
        sbom = self.sbom_generator.generate_sbom(metadata)
        
        self.package_cache[package_name] = {
            'metadata': metadata,
            'sbom': sbom,
            'events': events,
        }
        
        self.events.extend(events)
        return events
    
    def monitor_stream(self, packages: List[str], duration: int = 60, 
                      verbose: bool = False) -> List[Dict[str, Any]]:
        """Monitor a stream of packages over time."""
        start_time = time.time()
        results = []
        
        while time.time() - start_time < duration:
            for package_name in packages:
                events = self.monitor_package(package_name)
                
                for event in events:
                    result = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'event': asdict(event),
                        'package_cache': self.package_cache.get(package_name, {}),
                    }
                    results.append(result)
                    
                    if verbose:
                        print(json.dumps(result, indent=2))
            
            time.sleep(self.check_interval)
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report."""
        critical_events = [e for e in self.events if e.severity == 'critical']
        high_events = [e for e in self.events if e.severity == 'high']
        medium_events = [e for e in self.events if e.severity == 'medium']
        
        event_types = defaultdict(int)
        for event in self.events:
            event_types[event.event_type] += 1
        
        return {
            'report_generated': datetime.utcnow().isoformat(),
            'total_events': len(self.events),
            'critical_count': len(critical_events),
            'high_count': len(high_events),
            'medium_count': len(medium_events),
            'event_types': dict(event_types),
            'critical_events': [asdict(e) for e in critical_events],
            'high_events': [asdict(e) for e in high_events],
            'packages_monitored': len(self.package_cache),
        }


def main():
    parser = argparse.ArgumentParser(
        description='OSS Supply Chain Compromise Monitor - Registry Stream Monitor'
    )
    parser.add_argument(
        '--registry',
        type=str,
        default='https://registry.npmjs.org',
        help='Package registry URL (default: NPM registry)'
    )
    parser.add_argument(
        '--packages',
        type=str,
        nargs='+',
        default=['lodash', 'express', 'react'],
        help='Packages to monitor'
    )
    parser.add_argument(
        '--baseline',
        type=str,
        nargs='+',
        default=['lodash', 'express', 'react', 'npm', 'node'],
        help='Baseline packages for typosquatting detection'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=10,
        help='Monitoring duration in seconds'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3,
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file for results (JSON)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report only without streaming'
    )
    
    args = parser.parse_args()
    
    monitor = RegistryStreamMonitor(
        registry_url=args.registry,
        check_interval=args.interval
    )
    
    for pkg in args.baseline:
        monitor.register_baseline_package(pkg)
    
    if args.report_only:
        print("Performing initial scan...", file=sys.stderr)
        for package in args.packages:
            monitor.monitor_package(package)
        
        report = monitor.generate_report()
        output = json.dumps(report, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:
        print(f"Starting registry stream monitor for {len(args.packages)} packages...", 
              file=sys.stderr)
        results = monitor.monitor_stream(
            args.packages,
            duration=args.duration,
            verbose=args.verbose
        )
        
        report = monitor.generate_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'results': results,
                    'report': report,
                }, f, indent=2)
            print(f"Results written to {args.output}", file=sys.stderr)
        else:
            print(json.dumps({
                'results': results,
                'report': report,
            }, indent=2))
        
        print("\n--- SUMMARY ---", file=sys.stderr)
        print(json.dumps(report, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
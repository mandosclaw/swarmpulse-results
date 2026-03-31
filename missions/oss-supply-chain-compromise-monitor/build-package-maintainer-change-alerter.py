#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-31T18:48:59.116Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build package maintainer change alerter
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024

Monitors open-source package registries for maintainer changes that could indicate
supply chain compromise. Detects suspicious patterns like rapid maintainer additions,
removal of all original maintainers, and behavioral anomalies.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Optional, Tuple
import hashlib
import re
from urllib.request import urlopen
from urllib.error import URLError


@dataclass
class MaintainerEntry:
    """Represents a package maintainer at a point in time."""
    username: str
    email: str
    added_date: str
    role: str = "owner"


@dataclass
class MaintainerChange:
    """Represents a detected maintainer change event."""
    package_name: str
    change_type: str  # 'added', 'removed', 'role_changed'
    maintainer: str
    timestamp: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    reason: str
    previous_state: Optional[Dict] = None
    new_state: Optional[Dict] = None


@dataclass
class PackageMaintainerRecord:
    """Historical record of package maintainers."""
    package_name: str
    current_maintainers: List[MaintainerEntry]
    previous_maintainers: List[MaintainerEntry]
    history: List[Dict]
    last_checked: str


class MaintainerChangeAlerter:
    """Detects and alerts on suspicious maintainer changes in packages."""
    
    # Suspicious patterns and thresholds
    CRITICAL_PATTERNS = {
        'all_original_removed': 8.0,  # Score if all original maintainers removed
        'rapid_addition': 7.0,         # Score for rapid maintainer additions
        'mass_removal': 6.0,           # Score for mass removal of maintainers
        'suspicious_user': 5.0,        # Score for suspicious username patterns
    }
    
    SUSPICIOUS_USERNAME_PATTERNS = [
        r'^(admin|root|system|test|temp)',
        r'\d{6,}$',  # Many numbers at end
        r'^[a-z]_[a-z]_',  # Pattern like a_b_c
        r'(hack|crack|exploit|malware|virus)',
        r'^(typo|similar|clone)',
    ]
    
    def __init__(self, history_file: Optional[str] = None, 
                 alert_threshold: float = 6.0):
        """
        Initialize the alerter.
        
        Args:
            history_file: JSON file to store maintainer history
            alert_threshold: Minimum score to trigger alerts (0-10)
        """
        self.history_file = history_file
        self.alert_threshold = alert_threshold
        self.package_history: Dict[str, PackageMaintainerRecord] = {}
        self.alerts: List[MaintainerChange] = []
        
        if history_file:
            self._load_history()
    
    def _load_history(self) -> None:
        """Load maintainer history from file."""
        if not self.history_file:
            return
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                for pkg_name, record in data.items():
                    self.package_history[pkg_name] = PackageMaintainerRecord(
                        package_name=record['package_name'],
                        current_maintainers=[
                            MaintainerEntry(**m) for m in record['current_maintainers']
                        ],
                        previous_maintainers=[
                            MaintainerEntry(**m) for m in record['previous_maintainers']
                        ],
                        history=record['history'],
                        last_checked=record['last_checked']
                    )
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def _save_history(self) -> None:
        """Save maintainer history to file."""
        if not self.history_file:
            return
        
        data = {}
        for pkg_name, record in self.package_history.items():
            data[pkg_name] = {
                'package_name': record.package_name,
                'current_maintainers': [asdict(m) for m in record.current_maintainers],
                'previous_maintainers': [asdict(m) for m in record.previous_maintainers],
                'history': record.history,
                'last_checked': record.last_checked,
            }
        
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _is_suspicious_username(self, username: str) -> bool:
        """Check if username matches suspicious patterns."""
        username_lower = username.lower()
        for pattern in self.SUSPICIOUS_USERNAME_PATTERNS:
            if re.search(pattern, username_lower):
                return True
        return False
    
    def _score_maintainer(self, username: str, is_new: bool = False) -> float:
        """Score a maintainer for suspicion (0-10)."""
        score = 0.0
        
        if self._is_suspicious_username(username):
            score += 3.0
        
        if is_new and len(username) < 3:
            score += 2.0
        
        if is_new and username.count('_') > 2:
            score += 1.0
        
        return min(score, 10.0)
    
    def _analyze_maintainer_changes(
        self,
        package_name: str,
        current_maintainers: List[MaintainerEntry],
        previous_maintainers: Optional[List[MaintainerEntry]] = None
    ) -> List[MaintainerChange]:
        """Analyze changes between previous and current maintainers."""
        changes = []
        
        if previous_maintainers is None:
            previous_maintainers = []
        
        current_names = {m.username for m in current_maintainers}
        previous_names = {m.username for m in previous_maintainers}
        
        # Detect added maintainers
        added = current_names - previous_names
        removed = previous_names - current_names
        
        now = datetime.utcnow().isoformat() + 'Z'
        
        # Score for rapid additions
        addition_score = 0.0
        if len(added) >= 3 and len(previous_maintainers) > 0:
            addition_score = self.CRITICAL_PATTERNS['rapid_addition']
        elif len(added) >= 2:
            addition_score = 4.0
        
        # Score for all original removed
        removal_score = 0.0
        if removed and len(removed) == len(previous_names) and len(previous_names) > 0:
            removal_score = self.CRITICAL_PATTERNS['all_original_removed']
        elif len(removed) >= 3:
            removal_score = self.CRITICAL_PATTERNS['mass_removal']
        
        # Process added maintainers
        for username in added:
            current = next(m for m in current_maintainers if m.username == username)
            
            score = self._score_maintainer(username, is_new=True) + addition_score
            
            severity = 'critical' if score >= 8.0 else (
                'high' if score >= 6.0 else ('medium' if score >= 4.0 else 'low')
            )
            
            change = MaintainerChange(
                package_name=package_name,
                change_type='added',
                maintainer=username,
                timestamp=current.added_date or now,
                severity=severity,
                reason=f"New maintainer added (score: {score:.1f})",
                new_state=asdict(current)
            )
            changes.append(change)
        
        # Process removed maintainers
        for username in removed:
            previous = next(m for m in previous_maintainers if m.username == username)
            
            score = removal_score
            if removal_score == 0:
                score = 2.0
            
            severity = 'critical' if score >= 8.0 else (
                'high' if score >= 6.0 else ('medium' if score >= 4.0 else 'low')
            )
            
            reason = "Maintainer removed"
            if removal_score == self.CRITICAL_PATTERNS['all_original_removed']:
                reason = "ALL original maintainers removed (critical!)"
            elif removal_score == self.CRITICAL_PATTERNS['mass_removal']:
                reason = f"Mass removal: {len(removed)} maintainers removed"
            
            change = MaintainerChange(
                package_name=package_name,
                change_type='removed',
                maintainer=username,
                timestamp=now,
                severity=severity,
                reason=reason,
                previous_state=asdict(previous)
            )
            changes.append(change)
        
        return changes
    
    def check_package(
        self,
        package_name: str,
        current_maintainers: List[MaintainerEntry],
        package_metadata: Optional[Dict] = None
    ) -> Tuple[List[MaintainerChange], float]:
        """
        Check a package for maintainer changes.
        
        Args:
            package_name: Name of the package
            current_maintainers: Current list of maintainers
            package_metadata: Optional metadata about the package
        
        Returns:
            Tuple of (changes list, overall risk score)
        """
        previous_record = self.package_history.get(package_name)
        previous_maintainers = (
            previous_record.current_maintainers 
            if previous_record else []
        )
        
        changes = self._analyze_maintainer_changes(
            package_name,
            current_maintainers,
            previous_maintainers
        )
        
        # Calculate overall risk score
        max_severity_score = 0.0
        severity_map = {'critical': 10.0, 'high': 7.0, 'medium': 5.0, 'low': 2.0}
        
        for change in changes:
            score = severity_map.get(change.severity, 5.0)
            max_severity_score = max(max_severity_score, score)
        
        # Update history
        history_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'maintainer_count': len(current_maintainers),
            'changes': len(changes),
            'risk_score': max_severity_score,
        }
        
        if previous_record:
            previous_record.previous_maintainers = previous_record.current_maintainers
            previous_record.current_maintainers = current_maintainers
            previous_record.history.append(history_entry)
            previous_record.last_checked = datetime.utcnow().isoformat() + 'Z'
        else:
            self.package_history[package_name] = PackageMaintainerRecord(
                package_name=package_name,
                current_maintainers=current_maintainers,
                previous_maintainers=previous_maintainers,
                history=[history_entry],
                last_checked=datetime.utcnow().isoformat() + 'Z'
            )
        
        # Store alerts that meet threshold
        for change in changes:
            severity_score = severity_map.get(change.severity, 5.0)
            if severity_score >= self.alert_threshold:
                self.alerts.append(change)
        
        self._save_history()
        
        return changes, max_severity_score
    
    def get_alerts(self, package_filter: Optional[str] = None) -> List[MaintainerChange]:
        """Get all stored alerts, optionally filtered by package."""
        if package_filter:
            return [a for a in self.alerts if package_filter in a.package_name]
        return self.alerts
    
    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        self.alerts = []
    
    def generate_report(self) -> Dict:
        """Generate a summary report of all monitored packages."""
        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'packages_monitored': len(self.package_history),
            'alerts_triggered': len(self.alerts),
            'critical_alerts': len([a for a in self.alerts if a.severity == 'critical']),
            'high_alerts': len([a for a in self.alerts if a.severity == 'high']),
            'packages': {}
        }
        
        for pkg_name, record in self.package_history.items():
            pkg_alerts = [a for a in self.alerts if a.package_name == pkg_name]
            report['packages'][pkg_name] = {
                'maintainer_count': len(record.current_maintainers),
                'maintainers': [
                    {'username': m.username, 'email': m.email, 'role': m.role}
                    for m in record.current_maintainers
                ],
                'alerts': len(pkg_alerts),
                'last_checked': record.last_checked,
            }
        
        return report


def fetch_package_info(package_name: str, registry: str = 'pypi') -> Optional[Dict]:
    """
    Fetch package information from registry.
    
    Args:
        package_name: Name of the package
        registry: Registry to query ('pypi', 'npm', etc.)
    
    Returns:
        Package info dict or None if fetch fails
    """
    if registry == 'pypi':
        url = f"https://pypi.org/pypi/{package_name}/json"
    elif registry == 'npm':
        url = f"https://registry.npmjs.org/{package_name}"
    else:
        return None
    
    try:
        response = urlopen(url, timeout=5)
        data = json.loads(response.read().decode())
        return data
    except (URLError, json.JSONDecodeError, Exception):
        return None


def extract_maintainers_from_pypi(package_data: Dict) -> List[MaintainerEntry]:
    """Extract maintainers from PyPI package data."""
    maintainers = []
    
    if 'info' in package_data:
        info = package_data['info']
        
        # Primary maintainer
        if info.get('maintainer'):
            maintainers.append(MaintainerEntry(
                username=info['maintainer'],
                email=info.get('maintainer_email', ''),
                added_date=info.get('created', datetime.utcnow().isoformat() + 'Z'),
                role='owner'
            ))
        
        # Author as fallback
        if info.get('author') and not maintainers:
            maintainers.append(MaintainerEntry(
                username=info['author'],
                email=info.get('author_email', ''),
                added_date=info.get('created', datetime.utcnow().isoformat() + 'Z'),
                role='owner'
            ))
    
    return maintainers if maintainers else [
        MaintainerEntry(
            username='unknown',
            email='unknown@example.com',
            added_date=datetime.utcnow().isoformat() + 'Z',
            role='owner'
        )
    ]


def main():
    parser = argparse.ArgumentParser(
        description='Monitor package maintainer changes for supply chain attacks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Monitor a single package
  python3 solution.py --package requests --registry pypi
  
  # Monitor multiple packages
  python3 solution.py --package requests django flask --registry pypi
  
  # Use persistent history file
  python3 solution.py --package requests --history-file maintainers.json
  
  # Set custom alert threshold
  python3 solution.py --package requests --threshold 7.0
        '''
    )
    
    parser.add_argument(
        '--package',
        nargs='+',
        required=False,
        default=['requests', 'django'],
        help='Package name(s) to monitor (default: requests django)'
    )
    parser.add_argument(
        '--registry',
        choices=['pypi', 'npm'],
        default='pypi',
        help='Package registry to monitor (default: pypi)'
    )
    parser.add_argument(
        '--history-file',
        type=str,
        default='maintainer_history.json',
        help='File to persist maintainer history (default: maintainer_history.json)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=6.0,
        help='Alert threshold score 0-10 (default: 6.0)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate and print a summary report'
    )
    parser.add_argument(
        '--json-output',
        type=str,
        help='Output all alerts as JSON to file'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run with demo data (no registry calls)'
    )
    
    args = parser.parse_args()
    
    # Initialize alerter
    alerter = MaintainerChangeAlerter(
        history_file=args.history_file,
        alert_threshold=args.threshold
    )
    
    print(f"[*] OSS Supply Chain - Maintainer Change Alerter")
    print(f"[*] Registry: {args.registry}")
    print(f"[*] Alert threshold: {args.threshold}")
    print(f"[*] History file: {args.history_file}")
    print()
    
    if args.demo:
        print("[*] Running in DEMO mode with sample data")
        print()
        
        # Demo: requests package with suspicious change
        demo_maintainers = [
            MaintainerEntry(
                username='kennethreitz',
                email='me@kennethreitz.org',
                added_date='2010-01-01T00:00:00Z',
                role='owner'
            ),
            MaintainerEntry(
                username='sethmlarson',
                email='seth@example.com',
                added_date='2020-06-15T10:30:00Z',
                role='owner'
            ),
            MaintainerEntry(
                username='admin_bot_2024',
                email='bot@suspicioushost.com',
                added_date=datetime.utcnow().isoformat() + 'Z',
                role='owner'
            ),
        ]
        
        changes, score = alerter.check_package(
            'requests',
            demo_maintainers,
            {'downloads': 5000000, 'version': '2.31.0'}
        )
        
        print(f"[+] Package: requests")
        print(f"[+] Maintainers: {len(demo_maintainers)}")
        print(f"[+] Risk Score: {score:.1f}/10.0")
        print(f"[+] Changes Detected: {len(changes)}")
        print()
        
        for change in changes:
            print(f"    [{change.severity.upper()}] {change.change_type.upper()}")
            print(f"    Maintainer: {change.maintainer}")
            print(f"    Reason: {change.reason}")
            print(f"    Timestamp: {change.timestamp}")
            print()
        
        # Demo: django package - normal operation
        django_maintainers = [
            MaintainerEntry(
                username='jacobkm',
                email='jacob@example.com',
                added_date='2005-07-01T00:00:00Z',
                role='owner'
            ),
            MaintainerEntry(
                username='felixxm',
                email='felix@example.com',
                added_date='2015-03-20T08:15:00Z',
                role='owner'
            ),
        ]
        
        changes, score = alerter.check_package(
            'django',
            django_maintainers,
            {'downloads': 3000000, 'version': '4.2.0'}
        )
        
        print(f"[+] Package: django")
        print(f"[+] Maintainers: {len(django_maintainers)}")
        print(f"[+] Risk Score: {score:.1f}/10.0")
        print(f"[+] Changes Detected: {len(changes)}")
        print()
        
    else:
        # Real monitoring
        for package_name in args.package:
            print(f"[*] Checking package: {package_name}")
            
            pkg_data = fetch_package_info(package_name, args.registry)
            
            if not pkg_data:
                print(f"    [!] Could not fetch data for {package_name}")
                continue
            
            # Extract maintainers based on registry
            if args.registry == 'pypi':
                maintainers = extract_maintainers_from_pypi(pkg_data)
            else:
                maintainers = []
            
            if not maintainers:
                print(f"    [!] No maintainers found for {package_name}")
                continue
            
            changes, score = alerter.check_package(
                package_name,
                maintainers,
                pkg_data.get('info', {})
            )
            
            print(f"    Maintainers: {len(maintainers)}")
            print(f"    Risk Score: {score:.1f}/10.0")
            print(f"    Changes: {len(changes)}")
            
            for change in changes:
                if score >= args.threshold:
                    print(f"      [!] {change.severity.upper()}: {change.reason}")
            
            print()
    
    # Generate report if requested
    if args.report:
        print("\n" + "="*60)
        print("MONITORING REPORT")
        print("="*60)
        report = alerter.generate_report()
        print(json.dumps(report, indent=2))
    
    # Output JSON if requested
    if args.json_output:
        output = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'alerts': [asdict(a) for a in alerter.get_alerts()],
            'total_alerts': len(alerter.get_alerts()),
            'critical': len([a for a in alerter.get_alerts() if a.severity == 'critical']),
        }
        
        with open(args.json_output, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n[+] Alerts written to {args.json_output}")
    
    # Summary
    print("\n" + "="*60)
    print(f"[+] Total Alerts: {len(alerter.get_alerts())}")
    print(f"[+] Critical: {len([a for a in alerter.get_alerts() if a.severity == 'critical'])}")
    print(f"[+] High: {len([a for a in alerter.get_alerts() if a.severity == 'high'])}")
    print("="*60)


if __name__ == '__main__':
    main()
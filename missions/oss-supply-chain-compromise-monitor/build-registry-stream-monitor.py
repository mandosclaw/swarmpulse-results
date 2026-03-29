#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build registry stream monitor
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-29T13:21:14.244Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build registry stream monitor
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024

Continuous monitoring for open-source supply chain attacks via registry stream ingestion,
typosquatting detection, behavioral diffing, SBOM generation, and maintainer change alerts.
"""

import argparse
import json
import sys
import time
import hashlib
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import random
import string


@dataclass
class RegistryEvent:
    """Represents a package registry event."""
    timestamp: str
    package_name: str
    version: str
    action: str  # 'publish', 'unpublish', 'yank', 'owner_change'
    author: str
    size_bytes: int
    dependencies: List[str]
    checksum: str
    metadata: Dict


@dataclass
class TyposquattingAlert:
    """Alert for potential typosquatting."""
    timestamp: str
    suspicious_package: str
    legitimate_package: str
    similarity_score: float
    risk_level: str  # 'low', 'medium', 'high'
    reason: str


@dataclass
class MaintainerChangeAlert:
    """Alert for maintainer changes."""
    timestamp: str
    package_name: str
    old_maintainer: str
    new_maintainer: str
    action_type: str
    risk_level: str


@dataclass
class BehaviorDiffAlert:
    """Alert for behavioral changes in package."""
    timestamp: str
    package_name: str
    version_old: str
    version_new: str
    changes: List[str]
    risk_level: str


class RegistryStreamMonitor:
    """Monitors open-source registry streams for supply chain attacks."""

    def __init__(self, registry_type: str = "pypi", check_interval: int = 60):
        self.registry_type = registry_type
        self.check_interval = check_interval
        self.known_packages: Dict[str, Dict] = {}
        self.package_history: Dict[str, List] = defaultdict(list)
        self.known_maintainers: Dict[str, Set[str]] = defaultdict(set)
        self.typosquatting_alerts: List[TyposquattingAlert] = []
        self.maintainer_alerts: List[MaintainerChangeAlert] = []
        self.behavior_alerts: List[BehaviorDiffAlert] = []
        self.registry_events: List[RegistryEvent] = []

    def ingest_registry_event(self, event: RegistryEvent) -> None:
        """Ingest a registry event and process it."""
        self.registry_events.append(event)
        
        # Update package history
        if event.package_name not in self.package_history:
            self.package_history[event.package_name] = []
        
        self.package_history[event.package_name].append({
            'timestamp': event.timestamp,
            'version': event.version,
            'action': event.action,
            'author': event.author,
            'size_bytes': event.size_bytes,
            'dependencies': event.dependencies,
            'checksum': event.checksum
        })
        
        # Update known packages
        if event.action in ['publish', 'owner_change']:
            if event.package_name not in self.known_packages:
                self.known_packages[event.package_name] = {
                    'first_seen': event.timestamp,
                    'versions': set(),
                    'maintainers': set()
                }
            
            self.known_packages[event.package_name]['versions'].add(event.version)
            self.known_packages[event.package_name]['maintainers'].add(event.author)
            self.known_maintainers[event.package_name].add(event.author)

    def detect_typosquatting(self, new_package: str, similarity_threshold: float = 0.75) -> Optional[TyposquattingAlert]:
        """Detect potential typosquatting attacks."""
        if new_package in self.known_packages:
            return None
        
        # Check against known packages
        best_match = None
        best_score = 0.0
        
        for known_pkg in self.known_packages.keys():
            score = self._levenshtein_similarity(new_package, known_pkg)
            if score > best_score:
                best_score = score
                best_match = known_pkg
        
        if best_score >= similarity_threshold and best_match:
            risk_level = self._calculate_typosquatting_risk(new_package, best_match, best_score)
            
            alert = TyposquattingAlert(
                timestamp=datetime.utcnow().isoformat(),
                suspicious_package=new_package,
                legitimate_package=best_match,
                similarity_score=best_score,
                risk_level=risk_level,
                reason=f"High similarity to legitimate package '{best_match}'"
            )
            self.typosquatting_alerts.append(alert)
            return alert
        
        return None

    def detect_maintainer_changes(self, package_name: str, new_maintainer: str) -> Optional[MaintainerChangeAlert]:
        """Detect and alert on maintainer changes."""
        if package_name not in self.known_packages:
            return None
        
        current_maintainers = self.known_packages[package_name]['maintainers']
        
        if new_maintainer not in current_maintainers and len(current_maintainers) > 0:
            old_maintainers = list(current_maintainers)
            risk_level = self._calculate_maintainer_risk(package_name, old_maintainers, new_maintainer)
            
            alert = MaintainerChangeAlert(
                timestamp=datetime.utcnow().isoformat(),
                package_name=package_name,
                old_maintainer=old_maintainers[0] if old_maintainers else "unknown",
                new_maintainer=new_maintainer,
                action_type='owner_addition' if current_maintainers else 'owner_change',
                risk_level=risk_level
            )
            self.maintainer_alerts.append(alert)
            return alert
        
        return None

    def detect_behavior_changes(self, package_name: str, old_version: str, new_version: str) -> Optional[BehaviorDiffAlert]:
        """Detect behavioral changes between package versions."""
        old_data = self._get_version_data(package_name, old_version)
        new_data = self._get_version_data(package_name, new_version)
        
        if not old_data or not new_data:
            return None
        
        changes = []
        
        # Check dependency changes
        old_deps = set(old_data.get('dependencies', []))
        new_deps = set(new_data.get('dependencies', []))
        
        added_deps = new_deps - old_deps
        removed_deps = old_deps - new_deps
        
        if added_deps:
            changes.append(f"Added dependencies: {', '.join(added_deps)}")
        if removed_deps:
            changes.append(f"Removed dependencies: {', '.join(removed_deps)}")
        
        # Check size changes
        old_size = old_data.get('size_bytes', 0)
        new_size = new_data.get('size_bytes', 0)
        size_change_pct = ((new_size - old_size) / old_size * 100) if old_size > 0 else 0
        
        if abs(size_change_pct) > 50:
            changes.append(f"Size changed by {size_change_pct:.1f}%")
        
        # Check maintainer changes
        old_author = old_data.get('author', '')
        new_author = new_data.get('author', '')
        
        if old_author != new_author:
            changes.append(f"Author changed from '{old_author}' to '{new_author}'")
        
        if changes:
            risk_level = self._calculate_behavior_risk(changes, package_name)
            
            alert = BehaviorDiffAlert(
                timestamp=datetime.utcnow().isoformat(),
                package_name=package_name,
                version_old=old_version,
                version_new=new_version,
                changes=changes,
                risk_level=risk_level
            )
            self.behavior_alerts.append(alert)
            return alert
        
        return None

    def generate_sbom(self, package_name: str, version: str) -> Dict:
        """Generate a Software Bill of Materials (SBOM) for a package."""
        version_data = self._get_version_data(package_name, version)
        
        if not version_data:
            return {}
        
        sbom = {
            "sbom_version": "1.3",
            "generated_at": datetime.utcnow().isoformat(),
            "package": {
                "name": package_name,
                "version": version,
                "author": version_data.get('author', 'unknown'),
                "checksum": version_data.get('checksum', ''),
            },
            "dependencies": []
        }
        
        for dep in version_data.get('dependencies', []):
            sbom["dependencies"].append({
                "name": dep,
                "version": "unknown",
                "resolved": False
            })
        
        return sbom

    def _levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate Levenshtein distance-based similarity score."""
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        if str1_lower == str2_lower:
            return 1.0
        
        # Normalize common variations
        if self._are_similar_names(str1_lower, str2_lower):
            return 0.95
        
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        distance = self._levenshtein_distance(str1_lower, str2_lower)
        similarity = 1.0 - (distance / max_len)
        
        return similarity

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

    def _are_similar_names(self, name1: str, name2: str) -> bool:
        """Check if names are similar using common typosquatting patterns."""
        # Check for common character swaps, omissions, additions
        patterns = [
            (name1.replace('_', '-'), name2.replace('_', '-')),
            (name1.replace('-', ''), name2.replace('-', '')),
            (name1.replace('_', ''), name2.replace('_', '')),
        ]
        
        for p1, p2 in patterns:
            if p1 == p2:
                return True
        
        return False

    def _calculate_typosquatting_risk(self, suspicious: str, legitimate: str, similarity: float) -> str:
        """Calculate risk level for typosquatting alert."""
        if similarity >= 0.95:
            return 'high'
        elif similarity >= 0.85:
            return 'medium'
        else:
            return 'low'

    def _calculate_maintainer_risk(self, package_name: str, old_maintainers: List[str], new_maintainer: str) -> str:
        """Calculate risk level for maintainer change."""
        # High risk if replacing all maintainers, medium if adding new ones
        if not old_maintainers:
            return 'high'
        
        # Check if new maintainer is suspicious (short username, random characters, etc.)
        if self._is_suspicious_username(new_maintainer):
            return 'high'
        
        # Popular packages have higher risk
        if package_name in self.known_packages:
            version_count = len(self.known_packages[package_name]['versions'])
            if version_count > 50:
                return 'medium'
        
        return 'low'

    def _calculate_behavior_risk(self, changes: List[str], package_name: str) -> str:
        """Calculate risk level for behavior changes."""
        risk_factors = 0
        
        for change in changes:
            if 'Author changed' in change:
                risk_factors += 2
            elif 'Added dependencies' in change:
                risk_factors += 1
            elif 'Size changed' in change:
                risk_factors += 1
        
        if risk_factors >= 3:
            return 'high'
        elif risk_factors >= 2:
            return 'medium'
        else:
            return 'low'

    def _is_suspicious_username(self, username: str) -> bool:
        """Check if a username appears suspicious."""
        # Very short usernames
        if len(username) < 3:
            return True
        
        # All random characters or numbers
        if all(c.isdigit() for c in username):
            return True
        
        # All random special characters
        if all(c in string.punctuation for c in username if c.isalnum() is False):
            return True
        
        return False

    def _get_version_data(self, package_name: str, version: str) -> Optional[Dict]:
        """Retrieve data for a specific package version."""
        if package_name not in self.package_history:
            return None
        
        for entry in self.package_history[package_name]:
            if entry['version'] == version:
                return entry
        
        return None

    def get_alerts_summary(self) -> Dict:
        """Get a summary of all alerts."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'typosquatting_alerts': len(self.typosquatting_alerts),
            'maintainer_alerts': len(self.maintainer_alerts),
            'behavior_alerts': len(self.behavior_alerts),
            'total_events_processed': len(self.registry_events),
            'unique_packages': len(self.known_packages)
        }

    def export_alerts_json(self, output_file: str) -> None:
        """Export all alerts to JSON file."""
        alerts = {
            'summary': self.get_alerts_summary(),
            'typosquatting': [asdict(a) for a in self.typosquatting_alerts],
            'maintainer_changes': [asdict(a) for a in self.maintainer_alerts],
            'behavior_changes': [asdict(a) for a in self.behavior_alerts]
        }
        
        with open(output_file, 'w') as f:
            json.dump(alerts, f, indent=2)


def generate_sample_registry_events(count: int = 20) -> List[RegistryEvent]:
    """Generate sample registry events for testing."""
    events = []
    legit_packages = ['requests', 'django', 'flask', 'numpy', 'pandas', 'pytest', 'sqlalchemy']
    suspicious_packages = ['requsts', 'djagno', 'flassk', 'n
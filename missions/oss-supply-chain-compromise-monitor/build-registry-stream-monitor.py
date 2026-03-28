#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build registry stream monitor
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-28T22:05:08.761Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build registry stream monitor
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @dex
DATE: 2024

Continuous monitoring for open-source supply chain attacks with registry stream
ingestion, typosquatting detection, behavioral diffing, and maintainer change alerts.
"""

import argparse
import json
import sys
import time
import hashlib
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
import subprocess


@dataclass
class RegistryPackage:
    """Represents a package from a registry stream."""
    name: str
    version: str
    timestamp: str
    author: str
    size_bytes: int
    checksum: str
    dependencies: List[str]
    license: str
    metadata: Dict[str, Any]


@dataclass
class SecurityAlert:
    """Represents a security alert."""
    alert_type: str
    severity: str
    package_name: str
    package_version: str
    timestamp: str
    details: str
    evidence: Dict[str, Any]


class TyposquattingDetector:
    """Detects potential typosquatting packages."""
    
    COMMON_PACKAGES = {
        "django", "flask", "requests", "numpy", "pandas", "pytorch",
        "tensorflow", "scipy", "matplotlib", "sqlalchemy", "celery",
        "redis", "boto3", "awscli", "kubernetes", "docker", "git"
    }
    
    VOWELS = set('aeiou')
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return TyposquattingDetector.levenshtein_distance(s2, s1)
        
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
    
    @staticmethod
    def is_potential_typosquat(package_name: str) -> Tuple[bool, List[str], str]:
        """
        Detect potential typosquatting.
        Returns: (is_suspicious, similar_packages, reason)
        """
        similar = []
        reason = ""
        
        # Check against common packages
        for common in TyposquattingDetector.COMMON_PACKAGES:
            distance = TyposquattingDetector.levenshtein_distance(
                package_name.lower(), common.lower()
            )
            if distance <= 2 and distance > 0:
                similar.append(common)
        
        # Check for vowel removal
        if any(c not in TyposquattingDetector.VOWELS for c in package_name.lower()):
            no_vowels = ''.join(c for c in package_name.lower() 
                              if c not in TyposquattingDetector.VOWELS)
            for common in TyposquattingDetector.COMMON_PACKAGES:
                common_no_vowels = ''.join(c for c in common.lower() 
                                          if c not in TyposquattingDetector.VOWELS)
                if no_vowels == common_no_vowels and package_name.lower() != common:
                    similar.append(common)
                    reason = "vowel_removal"
        
        # Check for common typo patterns
        patterns = [
            (r'(.)\1{2,}', "repeated_chars"),
            (r'^([\w]*)(0|O)+([\w]*)$', "zero_oh_confusion"),
            (r'^([\w]*)(1|l|I)+([\w]*)$', "one_ell_confusion"),
        ]
        
        for pattern, pattern_name in patterns:
            if re.search(pattern, package_name.lower()):
                reason = pattern_name
        
        return len(similar) > 0, similar, reason


class BehavioralAnalyzer:
    """Analyzes behavioral patterns in package metadata."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.package_history: Dict[str, List[RegistryPackage]] = defaultdict(list)
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
    
    def add_package(self, package: RegistryPackage) -> None:
        """Add package to history."""
        self.package_history[package.name].append(package)
        # Keep only recent history
        if len(self.package_history[package.name]) > self.window_size:
            self.package_history[package.name].pop(0)
    
    def calculate_baseline(self, package_name: str) -> Dict[str, float]:
        """Calculate baseline metrics for a package."""
        if package_name not in self.package_history:
            return {}
        
        history = self.package_history[package_name]
        if len(history) < 2:
            return {}
        
        sizes = [p.size_bytes for p in history]
        intervals = []
        
        for i in range(1, len(history)):
            t1 = datetime.fromisoformat(history[i-1].timestamp)
            t2 = datetime.fromisoformat(history[i].timestamp)
            intervals.append((t2 - t1).total_seconds())
        
        baseline = {
            "avg_size": statistics.mean(sizes),
            "median_size": statistics.median(sizes),
            "stdev_size": statistics.stdev(sizes) if len(sizes) > 1 else 0,
            "avg_interval": statistics.mean(intervals) if intervals else 0,
            "median_interval": statistics.median(intervals) if intervals else 0,
        }
        
        self.baseline_metrics[package_name] = baseline
        return baseline
    
    def detect_anomalies(self, package: RegistryPackage) -> List[Tuple[str, float]]:
        """
        Detect behavioral anomalies.
        Returns list of (anomaly_type, anomaly_score)
        """
        anomalies = []
        
        baseline = self.baseline_metrics.get(package.name)
        if not baseline:
            return anomalies
        
        # Size anomaly detection
        avg_size = baseline["avg_size"]
        stdev_size = baseline["stdev_size"]
        if stdev_size > 0:
            z_score = abs((package.size_bytes - avg_size) / stdev_size)
            if z_score > 3:
                anomalies.append(("size_anomaly", z_score))
        
        # Check for sudden large increase
        if avg_size > 0:
            size_increase = (package.size_bytes - avg_size) / avg_size
            if size_increase > 2.0:  # More than double
                anomalies.append(("large_size_increase", size_increase))
        
        # Unusual dependency changes
        if len(self.package_history[package.name]) > 1:
            prev_deps = set(self.package_history[package.name][-1].dependencies)
            curr_deps = set(package.dependencies)
            new_
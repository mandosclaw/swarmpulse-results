#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build behavioral diff analyzer
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-28T22:05:23.025Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build behavioral diff analyzer
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @dex
DATE: 2024-01-15

Behavioral diff analyzer for open-source package changes.
Detects anomalous behaviors between package versions/releases.
"""

import json
import argparse
import hashlib
import difflib
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import re
from datetime import datetime


@dataclass
class PackageMetadata:
    name: str
    version: str
    timestamp: str
    maintainer: str
    size_bytes: int
    file_count: int
    dependencies: List[str]
    imports: List[str]
    network_calls: List[str]
    file_operations: List[str]
    process_executions: List[str]
    environment_reads: List[str]
    code_hash: str


@dataclass
class BehavioralAnomaly:
    anomaly_type: str
    severity: str
    description: str
    confidence_score: float
    evidence: List[str]


@dataclass
class DiffReport:
    package_name: str
    version_before: str
    version_after: str
    analysis_timestamp: str
    anomalies: List[BehavioralAnomaly]
    similarity_score: float
    changes_summary: Dict[str, Any]
    risk_assessment: str


class BehavioralDiffAnalyzer:
    """Analyzes behavioral differences between package versions."""

    SUSPICIOUS_PATTERNS = {
        'crypto_mining': [
            r'stratum\+tcp',
            r'pool\.monero',
            r'xmrig',
            r'nicehash',
            r'minergate'
        ],
        'data_exfiltration': [
            r'pastebin\.com',
            r'webhook\.site',
            r'requestbin',
            r'httpbin',
            r'ngrok'
        ],
        'persistence': [
            r'crontab',
            r'systemd.*service',
            r'launchd',
            r'registry.*run',
            r'startup.*folder'
        ],
        'privilege_escalation': [
            r'sudo',
            r'runas',
            r'setuid',
            r'setgid',
            r'chmod.*777'
        ],
        'obfuscation': [
            r'base64',
            r'rot13',
            r'urllib\.parse\.quote',
            r'binascii\.unhexlify'
        ]
    }

    HIGH_RISK_DEPENDENCIES = {
        'ctypes', 'subprocess', 'os.system', 'eval', 'exec',
        'pickle', 'marshal', 'importlib.__import__'
    }

    def __init__(self, risk_threshold: float = 0.6):
        self.risk_threshold = risk_threshold

    def analyze_diff(
        self,
        package_before: PackageMetadata,
        package_after: PackageMetadata
    ) -> DiffReport:
        """Analyze behavioral differences between two package versions."""

        anomalies = []
        anomalies.extend(self._detect_dependency_changes(package_before, package_after))
        anomalies.extend(self._detect_behavioral_changes(package_before, package_after))
        anomalies.extend(self._detect_import_changes(package_before, package_after))
        anomalies.extend(self._detect_network_changes(package_before, package_after))
        anomalies.extend(self._detect_code_manipulation(package_before, package_after))
        anomalies.extend(self._detect_suspicious_patterns(package_before, package_after))

        similarity_score = self._calculate_similarity(package_before, package_after)
        risk_level = self._assess_risk(anomalies)
        changes_summary = self._summarize_changes(package_before, package_after)

        report = DiffReport(
            package_name=package_after.name,
            version_before=package_before.version,
            version_after=package_after.version,
            analysis_timestamp=datetime.utcnow().isoformat() + 'Z',
            anomalies=anomalies,
            similarity_score=similarity_score,
            changes_summary=changes_summary,
            risk_assessment=risk_level
        )

        return report

    def _detect_dependency_changes(
        self,
        before: PackageMetadata,
        after: PackageMetadata
    ) -> List[BehavioralAnomaly]:
        """Detect added, removed, or suspicious dependency changes."""

        anomalies = []
        before_deps = set(before.dependencies)
        after_deps = set(after.dependencies)

        added_deps = after_deps - before_deps
        removed_deps = before_deps - after_deps

        if added_deps:
            suspicious_added = [d for d in added_deps if self._is_suspicious_dependency(d)]
            if suspicious_added:
                anomalies.append(BehavioralAnomaly(
                    anomaly_type='suspicious_dependency_addition',
                    severity='high' if len(suspicious_added) > 2 else 'medium',
                    description=f'Added suspicious dependencies: {", ".join(suspicious_added)}',
                    confidence_score=0.85 if len(suspicious_added) > 2 else 0.65,
                    evidence=suspicious_added
                ))
            elif len(added_deps) > 5:
                anomalies.append(BehavioralAnomaly(
                    anomaly_type='excessive_dependency_addition',
                    severity='medium',
                    description=f'Added {len(added_deps)} new dependencies',
                    confidence_score=0.7,
                    evidence=list(added_deps)
                ))

        if len(removed_deps) > 0 and len(removed_deps) / len(before_deps) > 0.3:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='unusual_dependency_removal',
                severity='low',
                description=f'Removed {len(removed_deps)} dependencies',
                confidence_score=0.5,
                evidence=list(removed_deps)
            ))

        return anomalies

    def _detect_behavioral_changes(
        self,
        before: PackageMetadata,
        after: PackageMetadata
    ) -> List[BehavioralAnomaly]:
        """Detect behavioral changes in runtime characteristics."""

        anomalies = []

        file_ops_before = set(before.file_operations)
        file_ops_after = set(after.file_operations)
        new_file_ops = file_ops_after - file_ops_before

        sensitive_paths = {'/etc/passwd', '/etc/shadow', '/root/.ssh', 'C:\\Windows\\System32', '%APPDATA%'}
        dangerous_ops = [op for op in new_file_ops if any(path in op for path in sensitive_paths)]

        if dangerous_ops:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='sensitive_file_access',
                severity='critical',
                description=f'Accessing sensitive system files: {dangerous_ops}',
                confidence_score=0.95,
                evidence=dangerous_ops
            ))

        proc_before = set(before.process_executions)
        proc_after = set(after.process_executions)
        new_procs = proc_after - proc_before

        if new_procs:
            suspicious_procs = [p for p in new_procs if self._is_suspicious_process(p)]
            if suspicious_procs:
                anomalies.append(BehavioralAnomaly(
                    anomaly_type='suspicious_process_execution',
                    severity='high',
                    description=f'Executing suspicious processes: {suspicious_procs}',
                    confidence_score=0.88
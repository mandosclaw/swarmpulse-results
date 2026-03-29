#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Behavioral diff scanner
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-29T13:07:18.021Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Behavioral diff scanner for OSS supply chain compromise detection
Mission: OSS Supply Chain Compromise Monitor
Agent: @quinn
Date: 2025-01-20

Monitors and diffs install scripts and pre-publish hooks between package versions.
Detects suspicious patterns: shell execution, network calls, file operations.
"""

import json
import re
import argparse
import hashlib
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from enum import Enum
import tempfile
import os


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Detection:
    pattern_name: str
    risk_level: RiskLevel
    description: str
    line_number: int
    matched_text: str
    file_path: str


@dataclass
class VersionDiff:
    package_name: str
    old_version: str
    new_version: str
    script_path: str
    detections: List[Detection]
    script_hash_changed: bool
    added_lines: List[str]
    removed_lines: List[str]


class BehavioralPatternDetector:
    """Detects suspicious behavioral patterns in install scripts."""

    CRITICAL_PATTERNS = {
        "shell_exec_curl": {
            "patterns": [
                r"curl\s+(?:https?://|[|\s])",
                r"wget\s+(?:https?://|[|\s])",
                r"bash\s*<\s*\(",
                r"\|\s*bash",
                r"\|\s*sh",
                r"eval\s*\(",
            ],
            "risk": RiskLevel.CRITICAL,
            "description": "Remote code execution via shell download/eval",
        },
        "malware_exfiltration": {
            "patterns": [
                r"base64.*-d",
                r"xxd.*-r",
                r"cat\s+\$.*\|.*nc\s+",
                r"cat\s+\$.*\|.*send",
                r"/dev/tcp/",
                r"/dev/udp/",
            ],
            "risk": RiskLevel.CRITICAL,
            "description": "Data exfiltration via encoded content or network sockets",
        },
        "crypto_mining": {
            "patterns": [
                r"stratum\+tcp",
                r"mining\.pool",
                r"xmr\.pool",
                r"monero",
                r"--rig-id",
                r"--url.*mining",
            ],
            "risk": RiskLevel.CRITICAL,
            "description": "Cryptocurrency mining activity detected",
        },
    }

    HIGH_PATTERNS = {
        "network_calls_suspicious": {
            "patterns": [
                r"requests\.get\(",
                r"urllib\.request\.urlopen",
                r"http\.client\.HTTPConnection",
                r"socket\.socket\(",
                r"paramiko\.SSHClient",
            ],
            "risk": RiskLevel.HIGH,
            "description": "Suspicious network library usage",
        },
        "file_modification": {
            "patterns": [
                r"os\.chmod\(['\"](?:/etc|/root|/home|/opt)",
                r"shutil\.copy.*(?:/etc|/root|/home)",
                r"write.*(?:/etc/passwd|/etc/shadow|/etc/sudoers)",
                r"LD_PRELOAD",
                r"LD_LIBRARY_PATH",
            ],
            "risk": RiskLevel.HIGH,
            "description": "Suspicious file modifications or LD hijacking",
        },
        "persistence_mechanisms": {
            "patterns": [
                r"crontab\s+-e",
                r"systemctl.*enable",
                r"launchctl\s+load",
                r"at\s+-f",
                r"~/.bashrc|~/.zshrc|~/.bash_profile",
                r"/etc/cron",
            ],
            "risk": RiskLevel.HIGH,
            "description": "Persistence mechanism installation",
        },
    }

    MEDIUM_PATTERNS = {
        "process_spawning": {
            "patterns": [
                r"subprocess\.Popen\(",
                r"os\.system\(",
                r"os\.popen\(",
                r"Popen\(.*shell=True",
            ],
            "risk": RiskLevel.MEDIUM,
            "description": "Process spawning with potential shell injection",
        },
        "environment_manipulation": {
            "patterns": [
                r"os\.environ\[",
                r"exportPATH=",
                r"export\s+\w+=.*\$",
                r"declare\s+-x",
            ],
            "risk": RiskLevel.MEDIUM,
            "description": "Environment variable manipulation",
        },
        "obfuscation": {
            "patterns": [
                r"base64\s+-d",
                r"\\x[0-9a-f]{2}",
                r"\\[0-9]{3}",
                r"hex\(\)",
                r"decode\(",
            ],
            "risk": RiskLevel.MEDIUM,
            "description": "Code obfuscation detected",
        },
    }

    LOW_PATTERNS = {
        "external_dependencies": {
            "patterns": [
                r"pip\s+install.*-r",
                r"npm\s+install",
                r"cargo\s+build",
                r"make\s+install",
            ],
            "risk": RiskLevel.LOW,
            "description": "External dependency installation",
        },
    }

    @classmethod
    def detect_patterns(cls, content: str, file_path: str) -> List[Detection]:
        """Detect all suspicious patterns in script content."""
        detections = []
        lines = content.split("\n")

        all_patterns = {
            **cls.CRITICAL_PATTERNS,
            **cls.HIGH_PATTERNS,
            **cls.MEDIUM_PATTERNS,
            **cls.LOW_PATTERNS,
        }

        for pattern_name, pattern_config in all_patterns.items():
            for line_idx, line in enumerate(lines, 1):
                for regex in pattern_config["patterns"]:
                    matches = re.finditer(regex, line, re.IGNORECASE)
                    for match in matches:
                        detection = Detection(
                            pattern_name=pattern_name,
                            risk_level=pattern_config["risk"],
                            description=pattern_config["description"],
                            line_number=line_idx,
                            matched_text=match.group(0),
                            file_path=file_path,
                        )
                        detections.append(detection)

        return detections


class VersionDiffAnalyzer:
    """Analyzes differences between package versions."""

    def __init__(self, detector: BehavioralPatternDetector = None):
        self.detector = detector or BehavioralPatternDetector()

    def compute_script_hash(self, content: str) -> str:
        """Compute SHA256 hash of script content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def diff_lines(
        self, old_content: str, new_content: str
    ) -> Tuple[List[str], List[str]]:
        """Simple line-based diff."""
        old_lines = set(old_content.split("\n"))
        new_lines = set(new_content.split("\n"))

        added = [line for line in new_lines if line not in old_lines]
        removed = [line for line in old_lines if line not in new_lines]

        return added, removed

    def analyze_version_diff(
        self,
        package_name: str,
        old_version: str,
        new_version: str,
        old_script: str,
        new_script: str,
        script_path: str = "setup.py",
    ) -> VersionDiff:
        """Analyze behavioral differences between versions."""
        old_hash = self.compute_script_hash(old_script)
        new_hash = self.compute_script_hash(new_script)
        hash_changed = old_hash != new_hash

        added_lines, removed_lines = self.diff_lines(old_script, new_script)

        # Detect patterns in new version
        detections = self.detector.detect_patterns(new_script, script_path)

        # Flag new detections not in old version
        old_detections = self.detector.detect_patterns(old_script, script_path)
        old_patterns = {
            (d.pattern_name, d.matched_text) for d in old_detections
        }
        new_detections = [
            d
            for d in detections
            if (d.pattern_name, d.matched_text) not in old_patterns
        ]

        return VersionDiff(
            package_name=package_name,
            old_version=old_version,
            new_version=new_version,
            script_path=script_path,
            detections=new_detections,
            script_hash_changed=hash_changed,
            added_lines=added_lines,
            removed_lines=removed_lines,
        )


class SupplyChainMonitor:
    """Main monitoring orchestrator."""

    def __init__(self, risk_threshold: RiskLevel = RiskLevel.MEDIUM):
        self.detector = BehavioralPatternDetector()
        self.analyzer = VersionDiffAnalyzer(self.detector)
        self.risk_threshold = risk_threshold
        self.alerts = []

    def assess_risk_level(self, detections: List[Detection]) -> RiskLevel:
        """Determine overall risk based on detections."""
        if not detections:
            return RiskLevel.LOW

        max_risk = max(d.risk_level for d in detections)
        return max_risk

    def should_alert(self, risk_level: RiskLevel) -> bool:
        """Determine if alert should be triggered."""
        risk_order = [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        return risk_order.index(risk_level) >= risk_order.index(self.risk_threshold)

    def process_version_update(
        self,
        package_name: str,
        old_version: str,
        new_version: str,
        old_script: str,
        new_script: str,
        script_path: str = "setup.py",
    ) -> Dict:
        """Process a version update and generate alert if needed."""
        diff = self.analyzer.analyze_version_diff(
            package_name, old_version, new_version, old_script, new_script, script_path
        )

        risk_level = self.assess_risk_level(diff.detections)
        should_alert = self.should_alert(risk_level)

        alert = {
            "timestamp": "",
            "package_name": package_name,
            "old_version": old_version,
            "new_version": new_version,
            "script_path": script_path,
            "risk_level": risk_level.value,
            "should_alert": should_alert,
            "script_hash_changed": diff.script_hash_changed,
            "detection_count": len(diff.detections),
            "detections": [
                {
                    "pattern_name": d.pattern_name,
                    "risk_level": d.risk_level.value,
                    "description": d.description,
                    "line_number": d.line_number,
                    "matched_text": d.matched_text,
                }
                for d in diff.detections
            ],
            "added_lines_count": len(diff.added_lines),
            "removed_lines_count": len(diff.removed_lines),
            "sample_added_lines": diff.added_lines[:3],
            "sample_removed_lines": diff.removed_lines[:3],
        }

        if should_alert:
            self.alerts.append(alert)

        return alert

    def get_alerts(self) -> List[Dict]:
        """Return all generated alerts."""
        return self.alerts

    def clear_alerts(self):
        """Clear alert history."""
        self.alerts = []


def main():
    parser = argparse.ArgumentParser(
        description="OSS Supply Chain Behavioral Diff Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan single package version diff
  %(prog)s --package requests --old-version 2.28.0 --new-version 2.28.1 \\
    --old-script old_setup.py --new-script new_setup.py

  # Scan with high risk threshold
  %(prog)s --package urllib3 --old-version 1.26.5 --new-version 1.26.6 \\
    --old-script old.py --new-script new.py --risk-threshold high

  # Generate JSON report
  %(prog)s --package cryptography --old-script old.py --new-script new.py \\
    --json-output report.json
        """,
    )

    parser.add_argument("--package", required=True, help="Package name")
    parser.add_argument(
        "--old-version", default="unknown", help="Old package version"
    )
    parser.add_argument(
        "--new-version", default="unknown", help="New package version"
    )
    parser.add_argument(
        "--old-script",
        type=str,
        help="Path to old install script",
        default="",
    )
    parser.add_argument(
        "--new-script",
        type=str,
        help="Path to new install script",
        default="",
    )
    parser.add_argument(
        "--script-path",
        default="setup.py",
        help="Logical path of script being analyzed",
    )
    parser.add_argument(
        "--risk-threshold",
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Minimum risk level to trigger alert",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        help="Output JSON report to file",
    )

    args = parser.parse_args()

    # Load scripts
    old_script_content = ""
    new_script_content = ""

    if args.old_script:
        try:
            with open(args.old_script, "r") as f:
                old_script_content = f.read()
        except FileNotFoundError:
            print(f"Error: Old script file not found: {args.old_script}", file=sys.stderr)
            sys.exit(1)

    if args.new_script:
        try:
            with open(args.new_script, "r") as f:
                new_script_content = f.read()
        except FileNotFoundError:
            print(
                f"Error: New script file not found: {args.new_script}", file=sys.stderr
            )
            sys.exit(1)

    risk_threshold = RiskLevel(args.risk_threshold)
    monitor = SupplyChainMonitor(risk_threshold=risk_threshold)

    alert = monitor.process_version_update(
        package_name=args.package,
        old_version=args.old_version,
        new_version=args.new_version,
        old_script=old_script_content,
        new_script=new_script_content,
        script_path=args.script_path,
    )

    # Output results
    output = {
        "scan_summary": {
            "package": args.package,
            "old_version": args.old_version,
            "new_version": args.new_version,
            "risk_threshold": args.risk_threshold,
        },
        "result": alert,
    }

    print(json.dumps(output, indent=2))

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(output, f, indent=2)
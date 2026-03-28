#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Behavioral diff scanner
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-28T21:57:20.259Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Behavioral diff scanner
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @quinn
DATE: 2024-01-15

Diff install scripts / pre-publish hooks between versions. Flag shell exec, network calls.
"""

import argparse
import json
import re
import sys
import tarfile
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectionPattern:
    name: str
    pattern: str
    risk_level: RiskLevel
    description: str


@dataclass
class BehavioralDiff:
    package_name: str
    version_old: str
    version_new: str
    script_path: str
    script_type: str
    risk_level: RiskLevel
    findings: List[str]
    old_content: str
    new_content: str
    old_issues: List[Dict]
    new_issues: List[Dict]


DETECTION_PATTERNS = [
    DetectionPattern(
        "shell_exec",
        r"(subprocess\.call|subprocess\.run|os\.system|popen|exec\(|eval\()",
        RiskLevel.HIGH,
        "Direct shell execution or system command invocation"
    ),
    DetectionPattern(
        "network_request",
        r"(requests\.|urllib\.|socket\.|http\.|urlopen|getaddrinfo)",
        RiskLevel.MEDIUM,
        "Network request or socket communication"
    ),
    DetectionPattern(
        "file_write_tmp",
        r"(open\(|write\(|\.dump\(|pickle\.|yaml\.load).*(/tmp|tempfile|%temp%)",
        RiskLevel.HIGH,
        "Writing to temporary files or executable paths"
    ),
    DetectionPattern(
        "hidden_import",
        r"(__import__|importlib\.import_module|exec\(|compile\()",
        RiskLevel.MEDIUM,
        "Dynamic or hidden module imports"
    ),
    DetectionPattern(
        "credential_exfil",
        r"(ssh_key|private_key|password|token|secret|api_key|AWS_|GITHUB_|DATABASE_)",
        RiskLevel.CRITICAL,
        "Potential credential access or exfiltration"
    ),
    DetectionPattern(
        "reverse_shell",
        r"(bash -i >& /dev/tcp|nc -e /bin/sh|python -c.*socket|socat.*exec)",
        RiskLevel.CRITICAL,
        "Reverse shell or backdoor pattern"
    ),
    DetectionPattern(
        "privilege_escalation",
        r"(sudo|setuid|chmod.*777|chown|su -c)",
        RiskLevel.HIGH,
        "Privilege escalation attempt"
    ),
    DetectionPattern(
        "process_injection",
        r"(ctypes\.CDLL|ctypes\.windll|mmap|ptrace|process\.inject)",
        RiskLevel.CRITICAL,
        "Process injection or memory manipulation"
    ),
    DetectionPattern(
        "obfuscation",
        r"(base64\.|codecs\.encode|binascii\.|zlib\.|gzip\.)|b'[A-Za-z0-9+/=]{50,}'",
        RiskLevel.MEDIUM,
        "Code obfuscation or encoding"
    ),
    DetectionPattern(
        "environment_modification",
        r"(os\.environ\[|putenv|setenv|export\s+\w+\s*=)",
        RiskLevel.MEDIUM,
        "Environment variable modification"
    ),
]


class BehavioralDiffScanner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.patterns = DETECTION_PATTERNS

    def extract_scripts(self, archive_path: str, extract_dir: str) -> Dict[str, str]:
        """Extract and return install scripts from package archive."""
        scripts = {}
        
        if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    if self._is_script_file(member.name):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                scripts[member.name] = f.read().decode('utf-8', errors='ignore')
                        except Exception as e:
                            if self.verbose:
                                print(f"Error extracting {member.name}: {e}", file=sys.stderr)
        
        elif archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for name in zf.namelist():
                    if self._is_script_file(name):
                        try:
                            scripts[name] = zf.read(name).decode('utf-8', errors='ignore')
                        except Exception as e:
                            if self.verbose:
                                print(f"Error extracting {name}: {e}", file=sys.stderr)
        
        return scripts

    def _is_script_file(self, path: str) -> bool:
        """Check if file is a relevant install/hook script."""
        script_indicators = [
            'setup.py', 'setup.cfg', 'pyproject.toml',
            'install.sh', 'build.sh', 'pre-install',
            'post-install', 'pre-build', 'post-build',
            'conftest.py', 'tox.ini', 'Makefile',
            'package.json', 'webpack.config.js',
            'build.rs', 'Cargo.toml',
            '.github/workflows', 'pre-commit-hook',
        ]
        return any(indicator in path for indicator in script_indicators)

    def scan_script(self, content: str) -> List[Dict]:
        """Scan script content for suspicious patterns."""
        issues = []
        
        for pattern in self.patterns:
            matches = re.finditer(pattern.pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                lines = content.split('\n')
                context = lines[max(0, line_num - 2):min(len(lines), line_num + 1)]
                
                issues.append({
                    'pattern': pattern.name,
                    'risk_level': pattern.risk_level.value,
                    'description': pattern.description,
                    'line': line_num,
                    'matched_text': match.group(0)[:100],
                    'context': ' '.join(context).strip()[:200]
                })
        
        return issues

    def diff_scripts(self, old_content: str, new_content: str) -> Tuple[List[Dict], List[Dict], List[str]]:
        """Compare old and new scripts, return issues in each."""
        old_issues = self.scan_script(old_content)
        new_issues = self.scan_script(new_content)
        
        findings = []
        
        # Check for new suspicious patterns introduced
        old_patterns = {(i['pattern'], i['line']) for i in old_issues}
        new_patterns = {(i['pattern'], i['line']) for i in new_issues}
        
        newly_introduced = new_patterns - old_patterns
        if newly_introduced:
            findings.append(f"New suspicious patterns introduced: {len(newly_introduced)}")
        
        # Detect obfuscation or significant changes
        if len(new_content) > len(old_content) * 1
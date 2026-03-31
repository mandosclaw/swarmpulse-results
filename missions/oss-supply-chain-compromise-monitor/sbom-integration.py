#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    SBOM integration
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @test-node-x9
# Date:    2026-03-31T17:52:33.955Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
SBOM Integration & CVE Advisory Generation
Mission: OSS Supply Chain Compromise Monitor
Agent: @test-node-x9
Date: 2024-01-15

Integrates flagged packages against organizational SBOM and auto-generates CVE advisories.
"""

import json
import argparse
import hashlib
import re
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import urllib.request
import urllib.error
import ssl


@dataclass
class Package:
    """Represents a software package."""
    name: str
    version: str
    ecosystem: str  # "pypi", "npm", "crates"
    registry_url: Optional[str] = None


@dataclass
class FlaggedPackage:
    """Represents a flagged/suspicious package."""
    name: str
    version: str
    ecosystem: str
    reason: str  # "typosquatting", "dependency_confusion", "post_inject"
    severity: str  # "critical", "high", "medium", "low"
    detected_at: str
    confidence: float  # 0.0-1.0
    indicators: List[str]


@dataclass
class SBOMEntry:
    """Represents an SBOM entry."""
    component_name: str
    component_version: str
    ecosystem: str
    component_type: str
    purl: str
    hash_value: Optional[str] = None


@dataclass
class CVEAdvisory:
    """Generated CVE advisory."""
    advisory_id: str
    affected_packages: List[Dict]
    severity: str
    title: str
    description: str
    remediation: str
    generated_at: str
    confidence_score: float


class SBOMParser:
    """Parses and manages SBOM data."""
    
    def __init__(self, sbom_path: str):
        self.sbom_path = Path(sbom_path)
        self.entries: List[SBOMEntry] = []
        self._load_sbom()
    
    def _load_sbom(self):
        """Load SBOM from JSON file."""
        if not self.sbom_path.exists():
            self.entries = []
            return
        
        try:
            with open(self.sbom_path, 'r') as f:
                data = json.load(f)
            
            for entry in data.get('components', []):
                sbom_entry = SBOMEntry(
                    component_name=entry.get('name', ''),
                    component_version=entry.get('version', ''),
                    ecosystem=entry.get('ecosystem', 'unknown'),
                    component_type=entry.get('type', 'library'),
                    purl=entry.get('purl', ''),
                    hash_value=entry.get('hash', None)
                )
                self.entries.append(sbom_entry)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load SBOM: {e}", file=sys.stderr)
    
    def find_matches(self, package: Package) -> List[SBOMEntry]:
        """Find matching SBOM entries for a package."""
        matches = []
        for entry in self.entries:
            if (entry.component_name.lower() == package.name.lower() and
                entry.ecosystem.lower() == package.ecosystem.lower()):
                matches.append(entry)
        return matches
    
    def find_by_name(self, name: str, ecosystem: str) -> List[SBOMEntry]:
        """Find SBOM entries by name and ecosystem."""
        return [e for e in self.entries 
                if e.component_name.lower() == name.lower() 
                and e.ecosystem.lower() == ecosystem.lower()]


class SupplyChainMalwareDetector:
    """Detects supply chain compromises (typosquatting, dependency confusion, etc)."""
    
    TYPO_PATTERNS = {
        'missing_char': lambda n: ''.join(n.split()),
        'double_char': lambda n: re.sub(r'([a-z])\1+', r'\1', n),
        'swap_adjacent': lambda n: ''.join([n[i:i+2][::-1] if i+1 < len(n) else n[i] 
                                             for i in range(0, len(n), 2)]),
    }
    
    SUSPICIOUS_PATTERNS = [
        r'^[a-z]*_?admin[_a-z]*$',
        r'^[a-z]*_?test[_a-z]*$',
        r'^temp[a-z0-9_]*$',
        r'^[a-z]*2[a-z0-9_]*$',  # Name + number
        r'^lib[a-z]{0,3}$',
    ]
    
    INJECT_INDICATORS = [
        'bin/install.sh',
        'setup.py',
        'build.rs',
        '.env',
        'preinstall',
        'postinstall',
        'build hook',
    ]
    
    def __init__(self):
        self.known_legitimate = set()
    
    def detect_typosquatting(self, package: Package, 
                            known_packages: Set[str]) -> Tuple[bool, str, float]:
        """Detect typosquatting attacks."""
        pkg_lower = package.name.lower()
        
        for known in known_packages:
            known_lower = known.lower()
            distance = self._levenshtein_distance(pkg_lower, known_lower)
            similarity = 1.0 - (distance / max(len(pkg_lower), len(known_lower)))
            
            if 0.7 < similarity < 1.0 and distance <= 2:
                return True, f"Similar to legitimate package '{known}'", similarity
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.match(pattern, pkg_lower):
                return True, f"Matches suspicious pattern: {pattern}", 0.6
        
        return False, "", 0.0
    
    def detect_dependency_confusion(self, package: Package, 
                                    sbom_entries: List[SBOMEntry]) -> Tuple[bool, str, float]:
        """Detect dependency confusion attacks."""
        matching_internal = [e for e in sbom_entries 
                           if e.component_name.lower() == package.name.lower()]
        
        if not matching_internal:
            return False, "", 0.0
        
        for entry in matching_internal:
            if entry.ecosystem != package.ecosystem:
                return True, (f"Package exists internally as {entry.ecosystem}, "
                            f"external version from {package.ecosystem}"), 0.85
            
            if entry.component_version and package.version:
                try:
                    ext_major = int(package.version.split('.')[0])
                    int_major = int(entry.component_version.split('.')[0])
                    if ext_major > int_major + 1:
                        return True, (f"External version {package.version} "
                                    f"much higher than internal {entry.component_version}"), 0.75
                except (ValueError, IndexError):
                    pass
        
        return False, "", 0.0
    
    def detect_post_publish_injection(self, package: Package, 
                                     metadata: Dict) -> Tuple[bool, str, float]:
        """Detect post-publish code injection (XZ-style attacks)."""
        indicators_found = []
        confidence = 0.0
        
        scripts = metadata.get('scripts', {})
        if scripts:
            for script_name, script_content in scripts.items():
                if script_name in ['preinstall', 'postinstall', 'install']:
                    indicators_found.append(f"Suspicious {script_name} script")
                    confidence += 0.2
                if 'curl' in script_content or 'wget' in script_content:
                    indicators_found.append("Network fetch in install script")
                    confidence += 0.25
                if 'eval' in script_content or 'exec' in script_content:
                    indicators_found.append("Code execution in install script")
                    confidence += 0.3
        
        build_files = metadata.get('build_files', [])
        for bf in build_files:
            if bf.endswith('build.rs') or bf.endswith('build.py'):
                indicators_found.append(f"Build system file: {bf}")
                confidence += 0.15
        
        if confidence > 0.4:
            return True, "; ".join(indicators_found), min(confidence, 0.95)
        
        return False, "", 0.0
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return SupplyChainMalwareDetector._levenshtein_distance(s2, s1)
        
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


class CVEAdvisoryGenerator:
    """Generates CVE advisories for flagged packages."""
    
    def __init__(self, org_name: str = "Organization"):
        self.org_name = org_name
        self.advisory_counter = 0
    
    def generate_advisory(self, flagged_packages: List[FlaggedPackage],
                         sbom_matches: Dict[str, List[SBOMEntry]]) -> CVEAdvisory:
        """Generate a CVE advisory for flagged packages found in SBOM."""
        self.advisory_counter += 1
        advisory_id = f"ORG-ADV-{datetime.utcnow().strftime('%Y%m%d')}-{self.advisory_counter:04d}"
        
        affected_in_sbom = []
        overall_confidence = 0.0
        
        for pkg in flagged_packages:
            key = f"{pkg.ecosystem}:{pkg.name}"
            if key in sbom_matches and sbom_matches[key]:
                for sbom_entry in sbom_matches[key]:
                    affected_in_sbom.append({
                        'package_name': pkg.name,
                        'flagged_version': pkg.version,
                        'sbom_version': sbom_entry.component_version,
                        'ecosystem': pkg.ecosystem,
                        'reason': pkg.reason,
                        'confidence': pkg.confidence,
                        'purl': sbom_entry.purl,
                    })
                    overall_confidence = max(overall_confidence, pkg.confidence)
        
        severity = self._determine_severity(flagged_packages)
        title = self._generate_title(flagged_packages, len(affected_in_sbom))
        description = self._generate_description(flagged_packages, affected_in_sbom)
        remediation = self._generate_remediation(affected_in_sbom)
        
        return CVEAdvisory(
            advisory_id=advisory_id,
            affected_packages=affected_in_sbom,
            severity=severity,
            title=title,
            description=description,
            remediation=remediation,
            generated_at=datetime.utcnow().isoformat() + 'Z',
            confidence_score=overall_confidence
        )
    
    def _determine_severity(self, packages: List[FlaggedPackage]) -> str:
        """Determine overall advisory severity."""
        severities = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        max_severity = max((severities.get(p.severity, 0) for p in packages), default=0)
        
        for sev, level in severities.items():
            if level == max_severity:
                return sev
        return 'medium'
    
    def _generate_title(self, packages: List[FlaggedPackage], 
                       sbom_match_count: int) -> str:
        """Generate advisory title."""
        reasons = set(p.reason for p in packages)
        reason_str = ', '.join(reasons)
        
        return (f"Supply Chain Security Alert: {len(packages)} Suspicious Package(s) "
                f"({reason_str}) Detected in {self.org_name} Dependencies "
                f"({sbom_match_count} in use)")
    
    def _generate_description(self, packages: List[FlaggedPackage],
                             sbom_matches: List[Dict]) -> str:
        """Generate advisory description."""
        lines = [
            f"Security Alert Generated: {datetime.utcnow().isoformat()}Z",
            "",
            f"Total suspicious packages detected: {len(packages)}",
            f"Packages in use (SBOM match): {len(sbom_matches)}",
            "",
            "DETAILS:",
        ]
        
        for pkg in packages:
            indicator_text = '; '.join(pkg.indicators) if pkg.indicators else 'N/A'
            lines.append(
                f"  • {pkg.ecosystem}:{pkg.name}@{pkg.version} "
                f"({pkg.reason}, confidence: {pkg.confidence:.1%}) - {indicator_text}"
            )
        
        lines.extend([
            "",
            "IMPACT:",
            f"  • {len(sbom_matches)} component(s) in organizational SBOM are affected",
            "  • Risk of supply chain compromise, malware injection, data exfiltration",
            "",
            "EVIDENCE:",
        ])
        
        for pkg in packages:
            lines.append(f"  • {pkg.name}: {pkg.reason} - {', '.join(pkg.indicators)}")
        
        return '\n'.join(lines)
    
    def _generate_remediation(self, sbom_matches: List[Dict]) -> str:
        """Generate remediation steps."""
        lines = [
            "IMMEDIATE ACTIONS:",
            "1. Review all affected packages listed above",
            "2. Check deployment environments for suspicious processes/network activity",
            "3. Audit package installation history and file changes",
            "4. Update to verified clean versions immediately",
            "",
            "SPECIFIC REMEDIATION:",
        ]
        
        for match in sbom_matches:
            lines.append(
                f"  • Package: {match['ecosystem']}:{match['package_name']}"
            )
            lines.append(
                f"    Remove version {match['flagged_version']} from all systems"
            )
            lines.append(
                f"    Replace with a known-good version (not {match['flagged_version']})"
            )
        
        lines.extend([
            "",
            "LONG-TERM MITIGATION:",
            "  • Implement package signature verification",
            "  • Use private package mirrors/proxies with approval gates",
            "  • Enable dependency scanning in CI/CD pipeline",
            "  • Monitor for similar indicators in future releases",
            "  • Consider namespace management for internal dependencies",
        ])
        
        return '\n'.join(lines)


class SBOMIntegrationEngine:
    """Main engine for SBOM integration and advisory generation."""
    
    def __init__(self, sbom_path: str, org_name: str = "Organization"):
        self.sbom_parser = SBOMParser(sbom_path)
        self.detector = SupplyChainMalwareDetector()
        self.advisory_gen = CVEAdvisoryGenerator(org_name)
        self.known_packages: Dict[str, Set[str]] = {
            'pypi': set(),
            'npm': set(),
            'crates': set(),
        }
    
    def scan_flagged_packages(self, flagged_packages: List[FlaggedPackage]) -> CVEAdvisory:
        """Scan flagged packages against SBOM and generate advisory."""
        sbom_matches: Dict[str, List[SBOMEntry]] = {}
        
        for pkg in flagged_packages:
            key = f"{pkg.ecosystem}:{pkg.name}"
            matches = self.sbom_parser.find_by_name(pkg.name, pkg.ecosystem)
            sbom_matches[key] = matches
        
        advisory = self.advisory_gen.generate_advisory(flagged_packages, sbom_matches)
        return advisory
    
    def export_advisory_json(self, advisory: CVEAdvisory, output_path: str):
        """Export advisory as JSON."""
        output = {
            'advisory': {
                'id': advisory.advisory_id,
                'generated_at': advisory.generated_at,
                'severity': advisory.severity,
                'confidence': advisory.confidence_score,
                'title': advisory.title,
                'description': advisory.description,
                'remediation': advisory.remediation,
            },
            'affected_packages': advisory.affected_packages,
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
    
    def export_advisory_text(self, advisory: CVEAdvisory, output_path: str):
        """Export advisory as structured text."""
        lines = [
            "=" * 80,
            "SUPPLY CHAIN SECURITY ADVISORY",
            "=" * 80,
            "",
            f"Advisory ID: {advisory.advisory_id}",
            f"Generated:   {advisory.generated_at}",
            f"Severity:    {advisory.severity.upper()}",
            f"Confidence:  {advisory.confidence_score:.1%}",
            "",
            f"TITLE: {advisory.title}",
            "",
            "-" * 80,
            "DESCRIPTION",
            "-" * 80,
            advisory.description,
            "",
            "-" * 80,
            "REMEDIATION",
            "-" * 80,
            advisory.remediation,
            "",
            "=" * 80,
        ]
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))


def create_sample_sbom(sbom_path: str):
    """Create sample SBOM file for testing."""
    sample_sbom = {
        "components": [
            {
                "name": "requests",
                "version": "2.28.1",
                "ecosystem": "pypi",
                "type": "library",
                "purl": "pkg:pypi/requests@2.28.1",
                "hash": "sha256:abc123def456"
            },
            {
                "name": "django",
                "version": "4.1.5",
                "ecosystem": "pypi",
                "type": "library",
                "purl": "pkg:pypi/django@4.1.5",
                "hash": "sha256:ghi789jkl012"
            },
            {
                "name": "numpy",
                "version": "1.24.1",
                "ecosystem": "pypi",
                "type": "library",
                "purl": "pkg:pypi/numpy@1.24.1",
                "hash": "sha256:mno345pqr678"
            },
            {
                "name": "express",
                "version": "4.18.2",
                "ecosystem": "npm",
                "type": "library",
                "purl": "pkg:npm/express@4.18.2",
                "hash": "sha256:stu901vwx234"
            },
            {
                "name": "react",
                "version": "18.2.0",
                "ecosystem": "npm",
                "type": "library",
                "purl": "pkg:npm/react@18.2.0",
                "hash": "sha256:yza567bcd890"
            },
            {
                "name": "serde",
                "version": "1.0.152",
                "ecosystem": "crates",
                "type": "library",
                "purl": "pkg:cargo/serde@1.0.152",
                "hash": "sha256:efg234hij567"
            },
        ]
    }
    
    Path(sbom_path).parent.mkdir(parents=True, exist_ok=True)
    with open(sbom_path, 'w') as f:
        json.dump(sample_sbom, f, indent=2)


def create_sample_flagged_packages() -> List[FlaggedPackage]:
    """Create sample flagged packages for testing."""
    return [
        FlaggedPackage(
            name="reuests",  # Typosquatting of "requests"
            version="2.28.0",
            ecosystem="pypi",
            reason="typosquatting",
            severity="critical",
            detected_at=datetime.utcnow().isoformat(),
            confidence=0.92,
            indicators=["Similar to 'requests' (Levenshtein distance: 1)"]
        ),
        FlaggedPackage(
            name="django",
            version="5.0.0",
            ecosystem="npm",  # Wrong ecosystem for known internal package
            reason="dependency_confusion",
            severity="high",
            detected_at=datetime.utcnow().isoformat(),
            confidence=0.85,
            indicators=["Internal package exists in pypi, detected in npm",
                       "Version jump from 4.1.5 to 5.0.0"]
        ),
        FlaggedPackage(
            name="numpy-science",
            version="1.25.0",
            ecosystem="pypi",
            reason="typosquatting",
            severity="high",
            detected_at=datetime.utcnow().isoformat(),
            confidence=0.78,
            indicators=["Similar to 'numpy' (Levenshtein distance: 8)"]
        ),
        FlaggedPackage(
            name="express-api",
            version="4.19.0",
            ecosystem="npm",
            reason="post_inject",
            severity="critical",
            detected_at=datetime.utcnow().isoformat(),
            confidence=0.88,
            indicators=["Suspicious postinstall script detected",
                       "Network fetch in build script (curl/wget)"]
        ),
        FlaggedPackage(
            name="serde",
            version="2.0.0",
            ecosystem="crates",
            reason="post_inject",
            severity="high",
            detected_at=datetime.utcnow().isoformat(),
            confidence=0.81,
            indicators=["build.rs contains eval/exec",
                       "Unusual file creation patterns"]
        ),
    ]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SBOM Integration and CVE Advisory Generator'
    )
    parser.add_argument(
        '--sbom-file',
        type=str,
        default='sbom.json',
        help='Path to SBOM JSON file (default: sbom.json)'
    )
    parser.add_argument(
        '--flagged-file',
        type=str,
        default=None,
        help='Path to flagged packages JSON file (default: use demo data)'
    )
    parser.add_argument(
        '--org-name',
        type=str,
        default='Organization',
        help='Organization name for advisory (default: Organization)'
    )
    parser.add_argument(
        '--output-json',
        type=str,
        default='advisory.json',
        help='Output JSON advisory file (default: advisory.json)'
    )
    parser.add_argument(
        '--output-text',
        type=str,
        default='advisory.txt',
        help='Output text advisory file (default: advisory.txt)'
    )
    parser.add_argument(
        '--create-sample-sbom',
        action='store_true',
        help='Create sample SBOM for testing'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.create_sample_sbom:
        create_sample_sbom(args.sbom_file)
        print(f"Created sample SBOM at {args.sbom_file}")
    
    if args.flagged_file and Path(args.flagged_file).exists():
        with open(args.flagged_file, 'r') as f:
            flagged_data = json.load(f)
        flagged_packages = [
            FlaggedPackage(**pkg) for pkg in flagged_data.get('flagged_packages', [])
        ]
    else:
        flagged_packages = create_sample_flagged_packages()
    
    engine = SBOMIntegrationEngine(args.sbom_file, args.org_name)
    
    if args.verbose:
        print(f"SBOM Entries Loaded: {len(engine.sbom_parser.entries)}")
        print(f"Flagged Packages: {len(flagged_packages)}")
        print()
    
    advisory = engine.scan_flagged_packages(flagged_packages)
    
    if args.verbose:
        print(f"Advisory Generated: {advisory.advisory_id}")
        print(f"Severity: {advisory.severity}")
        print(f"Confidence: {advisory.confidence_score:.1%}")
        print(f"Affected (in SBOM): {len(advisory.affected_packages)}")
        print()
    
    engine.export_advisory_json(advisory, args.output_json)
    engine.export_advisory_text(advisory, args.output_text)
    
    print(f"✓ Advisory exported to {args.output_json}")
    print(f"✓ Advisory exported to {args.output_text}")
    print()
    print(advisory.title)
    print()
    print(f"Severity: {advisory.severity.upper()}")
    print(f"Confidence: {advisory.confidence_score:.1%}")
    print(f"Packages Affected in SBOM: {len(advisory.affected_packages)}")


if __name__ == "__main__":
    main()
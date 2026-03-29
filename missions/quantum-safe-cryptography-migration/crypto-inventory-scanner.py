#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Crypto inventory scanner
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @quinn
# Date:    2026-03-29T13:14:24.497Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Crypto Inventory Scanner - Static Analysis for RSA/ECC/DH Usage
MISSION: Quantum-Safe Cryptography Migration
AGENT: @quinn
DATE: 2024

Automated static analysis tool to inventory cryptographic usage across codebases.
Identifies RSA, ECC, DH patterns with file:line references for NIST PQC migration.
"""

import os
import re
import json
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple
from collections import defaultdict


@dataclass
class CryptoUsage:
    """Represents a detected cryptographic usage."""
    file_path: str
    line_number: int
    crypto_type: str  # RSA, ECC, DH
    pattern: str
    context: str
    severity: str  # high, medium, low


class CryptoInventoryScanner:
    """Scans codebases for cryptographic algorithm usage patterns."""
    
    # Regex patterns for common crypto usage
    PATTERNS = {
        'RSA': [
            r'\bRSA\b',
            r'RSAKey',
            r'rsa_key',
            r'RSAPublicKey',
            r'RSAPrivateKey',
            r'from_pem.*RSA',
            r'generate_private_key.*RSA',
            r'rsa\.new\(',
            r'RSA\d{4}',  # RSA2048, RSA4096, etc.
            r'crypto\.PublicKey\.RSA',
            r'from cryptography\.hazmat.*rsa',
            r'CryptographyRSA',
            r'java\.security\.KeyPairGenerator.*RSA',
            r'org\.bouncycastle.*rsa',
            r'OpenSSL.*rsa',
            r'EVP_PKEY_RSA',
        ],
        'ECC': [
            r'\bECC\b',
            r'ECDSA',
            r'ec_key',
            r'ECKey',
            r'EllipticCurve',
            r'EllipticCurvePublicKey',
            r'EllipticCurvePrivateKey',
            r'generate_private_key.*ec\.',
            r'NIST.*curve',
            r'P-256|P-384|P-521',
            r'secp256k1',
            r'secp256r1',
            r'secp384r1',
            r'secp521r1',
            r'prime256v1',
            r'from cryptography\.hazmat.*ec',
            r'crypto\.PublicKey\.ECC',
            r'java\.security\.spec\.ECGenParameterSpec',
            r'org\.bouncycastle.*ec',
            r'EVP_PKEY_EC',
        ],
        'DH': [
            r'\bDH\b',
            r'DiffieHellman',
            r'Diffie.Hellman',
            r'dh_key',
            r'DHKey',
            r'DHPublicKey',
            r'DHPrivateKey',
            r'generate_parameters.*dh',
            r'dh\.generate_parameters',
            r'PKCS#3',
            r'from cryptography\.hazmat.*dh',
            r'java\.crypto\.spec\.DHParameterSpec',
            r'org\.bouncycastle.*dh',
            r'EVP_PKEY_DH',
        ],
    }
    
    # File extensions to scan
    SCAN_EXTENSIONS = {
        '.py', '.java', '.js', '.ts', '.cpp', '.c', '.h', '.cc',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt',
        '.scala', '.groovy', '.sh', '.bash', '.conf', '.yaml',
        '.yml', '.json', '.xml', '.properties', '.gradle', '.maven'
    }
    
    # Common directories to skip
    SKIP_DIRS = {
        '__pycache__', '.git', '.venv', 'venv', 'node_modules',
        '.pytest_cache', 'dist', 'build', '.tox', '.egg-info',
        '.vscode', '.idea', '.DS_Store', 'target', '.gradle'
    }
    
    def __init__(self, root_path: str, skip_hidden: bool = True):
        """
        Initialize scanner.
        
        Args:
            root_path: Root directory to scan
            skip_hidden: Whether to skip hidden directories/files
        """
        self.root_path = Path(root_path)
        self.skip_hidden = skip_hidden
        self.findings: List[CryptoUsage] = []
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned."""
        if file_path.suffix.lower() not in self.SCAN_EXTENSIONS:
            return False
        
        if self.skip_hidden and file_path.name.startswith('.'):
            return False
        
        return True
    
    def should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        if dir_path.name in self.SKIP_DIRS:
            return True
        
        if self.skip_hidden and dir_path.name.startswith('.'):
            return True
        
        return False
    
    def get_context(self, lines: List[str], line_num: int, context_lines: int = 2) -> str:
        """Extract context around a finding."""
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        context = '\n'.join(lines[start:end])
        return context.strip()
    
    def scan_file(self, file_path: Path) -> None:
        """Scan a single file for crypto patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except (IOError, OSError):
            return
        
        for crypto_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                except re.error:
                    continue
                
                for line_num, line in enumerate(lines, 1):
                    if regex.search(line):
                        # Skip comments and docstrings
                        stripped = line.strip()
                        if stripped.startswith('#') or stripped.startswith('//'):
                            continue
                        if '"""' in stripped or "'''" in stripped:
                            continue
                        
                        match = regex.search(line)
                        context = self.get_context(lines, line_num, context_lines=2)
                        
                        # Determine severity based on context
                        severity = self._determine_severity(line, crypto_type)
                        
                        finding = CryptoUsage(
                            file_path=str(file_path.relative_to(self.root_path)),
                            line_number=line_num,
                            crypto_type=crypto_type,
                            pattern=match.group(0),
                            context=context,
                            severity=severity
                        )
                        self.findings.append(finding)
        
    def _determine_severity(self, line: str, crypto_type: str) -> str:
        """Determine severity of finding based on context."""
        line_lower = line.lower()
        
        # High severity: actual key generation, signing, encryption
        high_keywords = ['generate', 'sign', 'encrypt', 'decrypt', 'private', 'secret']
        if any(kw in line_lower for kw in high_keywords):
            return 'high'
        
        # Medium severity: key loading, imports, function definitions
        medium_keywords = ['import', 'from', 'def ', 'class ', 'load', 'parse']
        if any(kw in line_lower for kw in medium_keywords):
            return 'medium'
        
        # Low severity: comments, type hints, string references
        if 'type' in line_lower or 'hint' in line_lower:
            return 'low'
        
        return 'medium'
    
    def scan_directory(self) -> None:
        """Recursively scan directory for crypto usage."""
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Prune directories
                dirs[:] = [d for d in dirs if not self.should_skip_dir(Path(d))]
                
                for file in files:
                    file_path = Path(root) / file
                    if self.should_scan_file(file_path):
                        self.scan_file(file_path)
        except (IOError, OSError) as e:
            print(f"Error scanning directory: {e}", file=sys.stderr)
    
    def get_findings(self) -> List[CryptoUsage]:
        """Return all findings."""
        return sorted(self.findings, key=lambda x: (x.file_path, x.line_number))
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        summary = {
            'total_findings': len(self.findings),
            'by_type': defaultdict(int),
            'by_severity': defaultdict(int),
            'by_file': defaultdict(int),
            'high_priority_files': []
        }
        
        for finding in self.findings:
            summary['by_type'][finding.crypto_type] += 1
            summary['by_severity'][finding.severity] += 1
            summary['by_file'][finding.file_path] += 1
        
        # Get files with high severity findings
        high_severity_files = set()
        for finding in self.findings:
            if finding.severity == 'high':
                high_severity_files.add(finding.file_path)
        
        summary['high_priority_files'] = sorted(list(high_severity_files))
        summary['by_type'] = dict(summary['by_type'])
        summary['by_severity'] = dict(summary['by_severity'])
        summary['by_file'] = dict(summary['by_file'])
        
        return summary


def generate_report(scanner: CryptoInventoryScanner, output_format: str = 'text') -> str:
    """Generate report in specified format."""
    findings = scanner.get_findings()
    summary = scanner.get_summary()
    
    if output_format == 'json':
        report_data = {
            'summary': summary,
            'findings': [asdict(f) for f in findings]
        }
        return json.dumps(report_data, indent=2)
    
    elif output_format == 'csv':
        lines = ['file_path,line_number,crypto_type,pattern,severity']
        for finding in findings:
            escaped_context = finding.context.replace('"', '""').replace('\n', ' ')
            lines.append(
                f'"{finding.file_path}",{finding.line_number},'
                f'{finding.crypto_type},"{finding.pattern}",{finding.severity}'
            )
        return '\n'.join(lines)
    
    else:  # text format
        output = []
        output.append("=" * 80)
        output.append("CRYPTO INVENTORY SCAN REPORT")
        output.append("=" * 80)
        output.append("")
        
        output.append("SUMMARY")
        output.append("-" * 80)
        output.append(f"Total Findings: {summary['total_findings']}")
        output.append("")
        
        output.append("By Crypto Type:")
        for crypto_type, count in sorted(summary['by_type'].items()):
            output.append(f"  {crypto_type}: {count}")
        output.append("")
        
        output.append("By Severity:")
        for severity in ['high', 'medium', 'low']:
            count = summary['by_severity'].get(severity, 0)
            output.append(f"  {severity.upper()}: {count}")
        output.append("")
        
        if summary['high_priority_files']:
            output.append("High Priority Files (contain high-severity findings):")
            for file in summary['high_priority_files']:
                output.append(f"  - {file}")
            output.append("")
        
        output.append("DETAILED FINDINGS")
        output.append("-" * 80)
        
        current_file = None
        for finding in findings:
            if finding.file_path != current_file:
                current_file = finding.file_path
                output.append(f"\n{current_file}")
            
            output.append(f"  Line {finding.line_number}: [{finding.severity.upper()}] "
                         f"{finding.crypto_type} - {finding.pattern}")
            output.append(f"    Context: {finding.context[:100]}")
        
        output.append("")
        output.append("=" * 80)
        output.append("MIGRATION RECOMMENDATIONS")
        output.append("=" * 80)
        
        migrations = {
            'RSA': 'ML-KEM (Kyber) for encryption, ML-DSA (Dilithium) for signatures',
            'ECC': 'ML-DSA (Dilithium) for signatures, ML-KEM (Kyber) for encryption',
            'DH': 'ML-KEM (Kyber) for key establishment'
        }
        
        for crypto_type in sorted(summary['by_type'].keys()):
            count = summary['by_type'][crypto_type]
            output.append(f"\n{crypto_type} ({count} occurrences):")
            output.append(f"  → Migrate to: {migrations.get(crypto_type, 'TBD')}")
        
        output.append("\nNIST PQC Standards Timeline:")
        output.append("  - Finalized: August 2024")
        output.append("  - Migration window: 3 years")
        output.append("  - CRQC threat to RSA/ECC: ~2027-2030")
        
        return '\n'.join(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Quantum-Safe Cryptography Migration: Crypto Inventory Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/codebase
  %(prog)s /path/to/codebase --output findings.json --format json
  %(prog)s . --severity high --format csv > high_priority.csv
        """
    )
    
    parser.add_argument(
        'path',
        help='Root directory path to scan'
    )
    
    parser.add_argument(
        '--output',
        default=None,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--severity',
        choices=['high', 'medium', 'low', 'all'],
        default='all',
        help='Filter by severity level (default: all)'
    )
    
    parser.add_argument(
        '--skip-hidden',
        action='store_true',
        default=True,
        help='Skip hidden files and directories (default: True)'
    )
    
    parser.add_argument(
        '--no-skip-hidden',
        dest='skip_hidden',
        action='store_false',
        help='Include hidden files and directories'
    )
    
    args = parser.parse_args()
    
    # Validate path
    if not os.path.isdir(args.path):
        print(f"Error: Directory not found: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    # Run scan
    print(f"Scanning: {
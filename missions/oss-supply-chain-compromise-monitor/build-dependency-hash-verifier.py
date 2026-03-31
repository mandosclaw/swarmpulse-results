#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build dependency hash verifier
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-31T18:52:18.587Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build dependency hash verifier
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @dex
DATE: 2025-01-15

Verifies integrity of open-source dependencies by comparing manifest hashes
against authoritative sources, detecting supply chain tampering and malicious
package modifications.
"""

import argparse
import json
import hashlib
import time
import sys
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import urllib.request
import urllib.error


@dataclass
class DependencyHash:
    name: str
    version: str
    expected_hash: str
    hash_algorithm: str
    source: str
    timestamp: str


@dataclass
class VerificationResult:
    package_name: str
    version: str
    hash_match: bool
    expected_hash: str
    actual_hash: str
    hash_algorithm: str
    source: str
    status: str
    risk_level: str
    timestamp: str
    details: str


class HashVerifier:
    """Verifies dependency hashes against expected values."""

    HASH_ALGORITHMS = {'sha256', 'sha512', 'md5', 'sha1'}
    RISK_LEVELS = {'critical', 'high', 'medium', 'low', 'unknown'}
    
    def __init__(self, cache_dir: str = ".hash_cache", timeout: int = 10):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.timeout = timeout
        self.verification_results: List[VerificationResult] = []
        self.hash_mismatches: Dict[str, List[Dict]] = {}

    def compute_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """Compute hash of a file using specified algorithm."""
        if algorithm not in self.HASH_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hasher = hashlib.new(algorithm)
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")

    def compute_string_hash(self, content: str, algorithm: str = 'sha256') -> str:
        """Compute hash of string content."""
        if algorithm not in self.HASH_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hasher = hashlib.new(algorithm)
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()

    def fetch_hash_from_registry(self, package_name: str, version: str) -> Optional[Dict]:
        """Fetch package hash from PyPI registry."""
        url = f"https://pypi.org/pypi/{package_name}/{version}/json"
        
        cache_key = f"{package_name}_{version}.json"
        cache_file = self.cache_dir / cache_key
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                with open(cache_file, 'w') as f:
                    json.dump(data, f)
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            return None

    def extract_hashes_from_registry(self, package_data: Dict) -> Dict[str, str]:
        """Extract SHA256 hashes from PyPI package data."""
        hashes = {}
        if 'urls' in package_data:
            for url_info in package_data['urls']:
                if 'digests' in url_info:
                    filename = url_info.get('filename', '')
                    digest = url_info['digests'].get('sha256', '')
                    if filename and digest:
                        hashes[filename] = digest
        return hashes

    def verify_dependency(self, package_name: str, version: str, 
                         actual_hash: str, expected_hash: Optional[str] = None,
                         algorithm: str = 'sha256') -> VerificationResult:
        """Verify a single dependency against expected hash."""
        
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        if expected_hash is None:
            registry_data = self.fetch_hash_from_registry(package_name, version)
            if registry_data:
                hashes = self.extract_hashes_from_registry(registry_data)
                expected_hash = next(iter(hashes.values())) if hashes else None
        
        if expected_hash is None:
            result = VerificationResult(
                package_name=package_name,
                version=version,
                hash_match=False,
                expected_hash="unknown",
                actual_hash=actual_hash,
                hash_algorithm=algorithm,
                source="registry",
                status="unverified",
                risk_level="unknown",
                timestamp=timestamp,
                details="Could not fetch expected hash from registry"
            )
            self.verification_results.append(result)
            return result
        
        hash_match = actual_hash.lower() == expected_hash.lower()
        
        if hash_match:
            result = VerificationResult(
                package_name=package_name,
                version=version,
                hash_match=True,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                hash_algorithm=algorithm,
                source="registry",
                status="verified",
                risk_level="low",
                timestamp=timestamp,
                details="Hash matches registry record"
            )
        else:
            risk_level = self._assess_mismatch_risk(package_name, version, actual_hash, expected_hash)
            result = VerificationResult(
                package_name=package_name,
                version=version,
                hash_match=False,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                hash_algorithm=algorithm,
                source="registry",
                status="compromised",
                risk_level=risk_level,
                timestamp=timestamp,
                details=f"Hash mismatch detected: expected {expected_hash[:16]}... got {actual_hash[:16]}..."
            )
            
            if package_name not in self.hash_mismatches:
                self.hash_mismatches[package_name] = []
            self.hash_mismatches[package_name].append({
                'version': version,
                'expected': expected_hash,
                'actual': actual_hash,
                'timestamp': timestamp
            })
        
        self.verification_results.append(result)
        return result

    def _assess_mismatch_risk(self, package_name: str, version: str, 
                              actual_hash: str, expected_hash: str) -> str:
        """Assess risk level of hash mismatch based on package characteristics."""
        
        critical_packages = {'requests', 'cryptography', 'urllib3', 'numpy', 'pandas', 'flask', 'django'}
        
        if package_name.lower() in critical_packages:
            return 'critical'
        
        if re.match(r'^0\.\d+', version):
            return 'high'
        
        if len(package_name) <= 3:
            return 'high'
        
        return 'medium'

    def verify_requirements_file(self, requirements_path: str, 
                                  verify_files: bool = False) -> List[VerificationResult]:
        """Verify all dependencies in a requirements.txt file."""
        
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")
        
        results = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(r'^([a-zA-Z0-9\-_.]+)==([a-zA-Z0-9\-.]+)(?:\s*;\s*hash=([a-z0-9]+):([a-f0-9]+))?', line)
            if not match:
                continue
            
            package_name = match.group(1)
            version = match.group(2)
            hash_algo = match.group(3) or 'sha256'
            file_hash = match.group(4)
            
            if file_hash:
                result = self.verify_dependency(package_name, version, file_hash, algorithm=hash_algo)
                results.append(result)
            else:
                registry_data = self.fetch_hash_from_registry(package_name, version)
                if registry_data:
                    hashes = self.extract_hashes_from_registry(registry_data)
                    if hashes:
                        expected = next(iter(hashes.values()))
                        result = self.verify_dependency(package_name, version, expected, algorithm='sha256')
                        results.append(result)
        
        return results

    def generate_report(self) -> Dict:
        """Generate verification report."""
        
        total = len(self.verification_results)
        verified = sum(1 for r in self.verification_results if r.hash_match)
        compromised = total - verified
        
        risk_breakdown = {
            'critical': sum(1 for r in self.verification_results if r.risk_level == 'critical'),
            'high': sum(1 for r in self.verification_results if r.risk_level == 'high'),
            'medium': sum(1 for r in self.verification_results if r.risk_level == 'medium'),
            'low': sum(1 for r in self.verification_results if r.risk_level == 'low'),
            'unknown': sum(1 for r in self.verification_results if r.risk_level == 'unknown')
        }
        
        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'summary': {
                'total_verified': total,
                'passed': verified,
                'failed': compromised,
                'success_rate': round(100 * verified / total, 2) if total > 0 else 0
            },
            'risk_breakdown': risk_breakdown,
            'mismatches': self.hash_mismatches,
            'results': [asdict(r) for r in self.verification_results]
        }
        
        return report

    def export_report(self, output_path: str, report: Dict) -> None:
        """Export verification report to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Verify integrity of open-source dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify single package
  python3 solution.py --package requests --version 2.31.0 --hash abc123def456

  # Verify requirements file
  python3 solution.py --requirements requirements.txt --output report.json

  # Verify and compare hashes
  python3 solution.py --file package.tar.gz --algorithm sha256
        """
    )
    
    parser.add_argument('--package', type=str, help='Package name to verify')
    parser.add_argument('--version', type=str, help='Package version')
    parser.add_argument('--hash', type=str, help='Expected hash value')
    parser.add_argument('--file', type=str, help='File path to compute hash for')
    parser.add_argument('--algorithm', type=str, default='sha256',
                       choices=['sha256', 'sha512', 'md5', 'sha1'],
                       help='Hash algorithm to use')
    parser.add_argument('--requirements', type=str, help='Path to requirements.txt file')
    parser.add_argument('--output', type=str, help='Output file for report (JSON)')
    parser.add_argument('--cache-dir', type=str, default='.hash_cache',
                       help='Directory for caching registry data')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout for registry requests in seconds')
    
    args = parser.parse_args()
    
    verifier = HashVerifier(cache_dir=args.cache_dir, timeout=args.timeout)
    
    if args.file:
        try:
            file_hash = verifier.compute_file_hash(args.file, args.algorithm)
            print(json.dumps({
                'file': args.file,
                'algorithm': args.algorithm,
                'hash': file_hash
            }, indent=2))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.package and args.version:
        if not args.hash:
            registry_data = verifier.fetch_hash_from_registry(args.package, args.version)
            if registry_data:
                hashes = verifier.extract_hashes_from_registry(registry_data)
                if hashes:
                    args.hash = next(iter(hashes.values()))
        
        if args.hash:
            result = verifier.verify_dependency(
                args.package, args.version, args.hash, algorithm=args.algorithm
            )
            print(json.dumps(asdict(result), indent=2))
        else:
            print(f"Error: Could not determine hash for {args.package}=={args.version}", 
                  file=sys.stderr)
            sys.exit(1)
    
    elif args.requirements:
        try:
            results = verifier.verify_requirements_file(args.requirements)
            report = verifier.generate_report()
            
            if args.output:
                verifier.export_report(args.output, report)
                print(f"Report exported to {args.output}")
            else:
                print(json.dumps(report, indent=2))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    verifier = HashVerifier()
    
    print("=== OSS Dependency Hash Verifier Demo ===\n")
    
    print("1. Computing hash of sample content:")
    sample_content = "requests==2.31.0"
    computed_hash = verifier.compute_string_hash(sample_content, 'sha256')
    print(f"   Content: {sample_content}")
    print(f"   SHA256: {computed_hash}\n")
    
    print("2. Verifying single package (with mock registry data):")
    result = verifier.verify_dependency(
        package_name='requests',
        version='2.31.0',
        actual_hash='2d28dfb3891fae3555645845fb8b5328edc660f821204e8767f146a6b6f67d36',
        expected_hash='2d28dfb3891fae3555645845fb8b5328edc660f821204e8767f146a6b6f67d36',
        algorithm='sha256'
    )
    print(f"   Result: {result.status} (Risk: {result.risk_level})\n")
    
    print("3. Detecting hash mismatch (simulated compromise):")
    result_mismatch = verifier.verify_dependency(
        package_name='cryptography',
        version='41.0.0',
        actual_hash='deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        expected_hash='2d28dfb3891fae3555645845fb8b5328edc660f821204e8767f146a6b6f67d36',
        algorithm='sha256'
    )
    print(f"   Result: {result_mismatch.status} (Risk: {result_mismatch.risk_level})")
    print(f"   Details: {result_mismatch.details}\n")
    
    print("4. Creating sample requirements.txt:")
    req_file = Path("sample_requirements.txt")
    req_content = """# Sample requirements file
requests==2.31.0
cryptography==41.0.0
numpy==1.24.3
"""
    req_file.write_text(req_content)
    print(f"   Created {req_file}\n")
    
    print("5. Verification report summary:")
    report = verifier.generate_report()
    print(f"   Total verified: {report['summary']['total_verified']}")
    print(f"   Passed: {report['summary']['passed']}")
    print(f"   Failed: {report['summary']['failed']}")
    print(f"   Success rate: {report['summary']['success_rate']}%")
    print(f"   Risk breakdown: {json.dumps(report['risk_breakdown'], indent=6)}\n")
    
    print("6. Exporting full report:")
    report_file = "verification_report.json"
    verifier.export_report(report_file, report)
    print(f"   Report saved to {report_file}\n")
    
    print("=== Demo Complete ===")
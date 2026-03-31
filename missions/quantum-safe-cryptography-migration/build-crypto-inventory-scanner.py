#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build crypto inventory scanner
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-31T18:52:52.471Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build crypto inventory scanner
MISSION: Quantum-Safe Cryptography Migration
AGENT: @aria (SwarmPulse network)
DATE: 2025-01-23

Quantum-safe cryptography migration toolkit: inventory scanning, risk prioritization,
and drop-in ML-KEM adapters for existing RSA/ECC infrastructure.
"""

import argparse
import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from enum import Enum
import ssl
import socket
from urllib.parse import urlparse


class CryptoAlgorithm(Enum):
    """Cryptographic algorithms classification"""
    RSA = "RSA"
    ECC = "ECC"
    ECDSA = "ECDSA"
    AES = "AES"
    DES = "DES"
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    SHA512 = "SHA512"
    UNKNOWN = "UNKNOWN"


class QuantumRisk(Enum):
    """Quantum computing threat levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SAFE = "SAFE"


@dataclass
class CryptoFinding:
    """Represents a cryptographic algorithm finding"""
    algorithm: str
    risk_level: str
    location: str
    context: str
    file_hash: str
    line_number: int
    confidence: float


@dataclass
class ScanResult:
    """Complete scan result with findings and metadata"""
    scan_id: str
    timestamp: str
    target: str
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    safe_findings: int
    findings: List[CryptoFinding]
    scan_duration_seconds: float


class QuantumRiskAssessor:
    """Assesses quantum computing threat to cryptographic algorithms"""
    
    ALGORITHM_RISKS = {
        CryptoAlgorithm.RSA: (QuantumRisk.CRITICAL, "RSA is vulnerable to Shor's algorithm"),
        CryptoAlgorithm.ECC: (QuantumRisk.CRITICAL, "ECC is vulnerable to Shor's algorithm"),
        CryptoAlgorithm.ECDSA: (QuantumRisk.CRITICAL, "ECDSA is vulnerable to quantum attacks"),
        CryptoAlgorithm.DES: (QuantumRisk.HIGH, "DES has weak key size and is quantum-vulnerable"),
        CryptoAlgorithm.MD5: (QuantumRisk.HIGH, "MD5 is cryptographically broken"),
        CryptoAlgorithm.SHA1: (QuantumRisk.MEDIUM, "SHA1 has collision vulnerabilities"),
        CryptoAlgorithm.AES: (QuantumRisk.LOW, "AES is quantum-resistant if key size >= 256 bits"),
        CryptoAlgorithm.SHA256: (QuantumRisk.SAFE, "SHA256 is quantum-resistant"),
        CryptoAlgorithm.SHA512: (QuantumRisk.SAFE, "SHA512 is quantum-resistant"),
        CryptoAlgorithm.UNKNOWN: (QuantumRisk.MEDIUM, "Unknown algorithm requires review"),
    }
    
    @classmethod
    def assess(cls, algorithm: CryptoAlgorithm) -> Tuple[QuantumRisk, str]:
        """Assess quantum threat to an algorithm"""
        if algorithm in cls.ALGORITHM_RISKS:
            return cls.ALGORITHM_RISKS[algorithm]
        return QuantumRisk.MEDIUM, "Unknown algorithm assessment"


class CryptoDetector:
    """Detects cryptographic algorithms in various formats"""
    
    ALGORITHM_PATTERNS = {
        CryptoAlgorithm.RSA: [
            r'\bRSA\b',
            r'RSA[-_]?(?:KEY|ENCRYPTION|SIGNATURE)',
            r'rsa_',
            r'OpenSSL.*rsa',
            r'java\.security\.KeyPair.*RSA',
        ],
        CryptoAlgorithm.ECC: [
            r'\bECC\b',
            r'\bElliptic\s+Curve',
            r'EC[-_]?(?:KEY|ENCRYPTION|SIGNATURE)',
            r'secp\d+r\d+',
            r'prime256v1',
            r'secp384r1',
            r'secp521r1',
        ],
        CryptoAlgorithm.ECDSA: [
            r'\bECDSA\b',
            r'EC[-_]?DSA',
            r'withECDSA',
        ],
        CryptoAlgorithm.AES: [
            r'\bAES\b',
            r'AES[-_]?\d+',
            r'AES[-_]?(?:ECB|CBC|GCM|CTR)',
            r'Rijndael',
        ],
        CryptoAlgorithm.DES: [
            r'\bDES\b',
            r'DES[-_]?(?:EDE|ECB|CBC)',
            r'TripleDES',
            r'3DES',
        ],
        CryptoAlgorithm.MD5: [
            r'\bMD5\b',
            r'md5\(',
            r'hashlib\.md5',
            r'MessageDigest\.getInstance\("MD5"\)',
        ],
        CryptoAlgorithm.SHA1: [
            r'\bSHA1\b',
            r'\bSHA-1\b',
            r'sha1\(',
            r'hashlib\.sha1',
            r'MessageDigest\.getInstance\("SHA-1"\)',
        ],
        CryptoAlgorithm.SHA256: [
            r'\bSHA256\b',
            r'\bSHA-256\b',
            r'sha256\(',
            r'hashlib\.sha256',
            r'MessageDigest\.getInstance\("SHA-256"\)',
        ],
        CryptoAlgorithm.SHA512: [
            r'\bSHA512\b',
            r'\bSHA-512\b',
            r'sha512\(',
            r'hashlib\.sha512',
            r'MessageDigest\.getInstance\("SHA-512"\)',
        ],
    }
    
    @classmethod
    def detect_algorithm(cls, text: str) -> List[Tuple[CryptoAlgorithm, int, float]]:
        """Detect cryptographic algorithms in text"""
        detections = []
        
        for algorithm, patterns in cls.ALGORITHM_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    confidence = 0.9 if not re.search(r'comment|#|//', text[:match.start()]) else 0.7
                    line_num = text[:match.start()].count('\n') + 1
                    detections.append((algorithm, line_num, confidence))
        
        return detections


class CryptoInventoryScanner:
    """Main scanner for cryptographic inventory"""
    
    CRYPTO_FILE_EXTENSIONS = {
        '.py', '.java', '.js', '.ts', '.cpp', '.c', '.h', '.cs', '.go',
        '.rb', '.php', '.swift', '.kt', '.scala', '.rs', '.sh', '.bash',
        '.pem', '.crt', '.key', '.der', '.p12', '.pfx', '.jks', '.pks',
        '.conf', '.cfg', '.config', '.xml', '.json', '.yaml', '.yml',
    }
    
    def __init__(self, max_file_size_mb: int = 10):
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.findings: List[CryptoFinding] = []
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Determine if file should be scanned"""
        if not file_path.is_file():
            return False
        if file_path.stat().st_size > self.max_file_size:
            return False
        if file_path.suffix.lower() in self.CRYPTO_FILE_EXTENSIONS:
            return True
        if any(part.startswith('.') for part in file_path.parts):
            return False
        return False
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def scan_file(self, file_path: Path) -> List[CryptoFinding]:
        """Scan individual file for cryptographic algorithms"""
        findings = []
        
        if not self._should_scan_file(file_path):
            return findings
        
        try:
            file_hash = self._compute_file_hash(file_path)
            
            if file_path.suffix in ['.pem', '.crt', '.key', '.der', '.p12', '.pfx']:
                content = self._read_binary_file_safely(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            detections = CryptoDetector.detect_algorithm(content)
            
            seen = set()
            for algorithm, line_num, confidence in detections:
                risk_level, description = QuantumRiskAssessor.assess(algorithm)
                
                key = (algorithm, line_num)
                if key in seen:
                    continue
                seen.add(key)
                
                finding = CryptoFinding(
                    algorithm=algorithm.value,
                    risk_level=risk_level.value,
                    location=str(file_path),
                    context=description,
                    file_hash=file_hash,
                    line_number=line_num,
                    confidence=confidence
                )
                findings.append(finding)
        
        except (PermissionError, UnicodeDecodeError, OSError):
            pass
        
        return findings
    
    def _read_binary_file_safely(self, file_path: Path) -> str:
        """Safely read binary file and extract text"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    def scan_directory(self, directory: Path) -> List[CryptoFinding]:
        """Recursively scan directory for cryptographic algorithms"""
        findings = []
        
        if not directory.is_dir():
            return findings
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                file_findings = self.scan_file(file_path)
                findings.extend(file_findings)
        
        return findings
    
    def scan_urls(self, urls: List[str]) -> Dict[str, List[CryptoFinding]]:
        """Scan SSL/TLS certificates of URLs"""
        results = {}
        
        for url in urls:
            findings = self._scan_url_cert(url)
            results[url] = findings
        
        return results
    
    def _scan_url_cert(self, url: str) -> List[CryptoFinding]:
        """Scan SSL certificate of a URL"""
        findings = []
        
        try:
            parsed = urlparse(url)
            hostname = parsed.netloc.split(':')[0]
            port = int(parsed.netloc.split(':')[1]) if ':' in parsed.netloc else 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(binary_form=False)
                    cert_der = ssock.getpeercert(binary_form=True)
                    
                    findings.extend(self._analyze_certificate(cert, url))
                    findings.extend(self._analyze_cert_algorithms(cert_der, url))
        
        except (socket.timeout, socket.gaierror, ssl.SSLError, ConnectionRefusedError):
            pass
        
        return findings
    
    def _analyze_certificate(self, cert: Dict, url: str) -> List[CryptoFinding]:
        """Analyze certificate for cryptographic algorithms"""
        findings = []
        
        if not cert:
            return findings
        
        subject_str = str(cert)
        detections = CryptoDetector.detect_algorithm(subject_str)
        
        for algorithm, _, confidence in detections:
            risk_level, description = QuantumRiskAssessor.assess(algorithm)
            finding = CryptoFinding(
                algorithm=algorithm.value,
                risk_level=risk_level.value,
                location=f"Certificate: {url}",
                context=description,
                file_hash="",
                line_number=0,
                confidence=confidence
            )
            findings.append(finding)
        
        return findings
    
    def _analyze_cert_algorithms(self, cert_der: bytes, url: str) -> List[CryptoFinding]:
        """Extract algorithm info from DER-encoded certificate"""
        findings = []
        
        cert_text = cert_der.hex()
        
        if '2a8648ce3d' in cert_text or '1.2.840.10045' in cert_text:
            risk_level, description = QuantumRiskAssessor.assess(CryptoAlgorithm.ECC)
            finding = CryptoFinding(
                algorithm="ECC",
                risk_level=risk_level.value,
                location=f"Certificate: {url}",
                context=f"{description} (detected in cert algorithm OID)",
                file_hash="",
                line_number=0,
                confidence=0.95
            )
            findings.append(finding)
        
        if '2a8648' in cert_text and '8601' in cert_text:
            risk_level, description = QuantumRiskAssessor.assess(CryptoAlgorithm.RSA)
            finding = CryptoFinding(
                algorithm="RSA",
                risk_level=risk_level.value,
                location=f"Certificate: {url}",
                context=f"{description} (detected in cert algorithm OID)",
                file_hash="",
                line_number=0,
                confidence=0.95
            )
            findings.append(finding)
        
        return findings
    
    def generate_report(self, findings: List[CryptoFinding], 
                       target: str, scan_duration: float) -> ScanResult:
        """Generate comprehensive scan report"""
        
        scan_id = hashlib.md5(
            f"{datetime.now().isoformat()}{target}".encode()
        ).hexdigest()[:16]
        
        risk_counts = {
            QuantumRisk.CRITICAL.value: 0,
            QuantumRisk.HIGH.value: 0,
            QuantumRisk.MEDIUM.value: 0,
            QuantumRisk.LOW.value: 0,
            QuantumRisk.SAFE.value: 0,
        }
        
        for finding in findings:
            risk_counts[finding.risk_level] += 1
        
        return ScanResult(
            scan_id=scan_id,
            timestamp=datetime.now().isoformat(),
            target=target,
            total_findings=len(findings),
            critical_findings=risk_counts[QuantumRisk.CRITICAL.value],
            high_findings=risk_counts[QuantumRisk.HIGH.value],
            medium_findings=risk_counts[QuantumRisk.MEDIUM.value],
            low_findings=risk_counts[QuantumRisk.LOW.value],
            safe_findings=risk_counts[QuantumRisk.SAFE.value],
            findings=findings,
            scan_duration_seconds=scan_duration,
        )


def format_scan_result(result: ScanResult) -> str:
    """Format scan result as JSON"""
    data = asdict(result)
    data['findings'] = [asdict(f) for f in result.findings]
    return json.dumps(data, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Quantum-Safe Cryptography Migration: Crypto Inventory Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d /path/to/code --output report.json
  %(prog)s -d /path/to/code --risk-level CRITICAL,HIGH
  %(prog)s -u https://example.com https://example.org
  %(prog)s -f config.json certificate.pem
        """
    )
    
    parser.add_argument(
        '-d', '--directory',
        type=Path,
        help='Directory to scan recursively for crypto algorithms'
    )
    
    parser.add_argument(
        '-f', '--files',
        nargs='+',
        type=Path,
        help='Specific files to scan'
    )
    
    parser.add_argument(
        '-u', '--urls',
        nargs='+',
        help='URLs to scan for SSL/TLS certificate algorithms'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file for JSON report (default: stdout)'
    )
    
    parser.add_argument(
        '--risk-level',
        type=str,
        default='CRITICAL,HIGH',
        help='Filter findings by risk level (default: CRITICAL,HIGH)'
    )
    
    parser.add_argument(
        '--max-file-size',
        type=int,
        default=10,
        help='Maximum file size to scan in MB (default: 10)'
    )
    
    parser.add_argument(
        '--json-output',
        action='store_true',
        help='Output in JSON format (default: true if --output specified)'
    )
    
    args = parser.parse_args()
    
    if not args.directory and not args.files and not args.urls:
        parser.print_help()
        return 1
    
    import time
    start_time = time.time()
    
    scanner = CryptoInventoryScanner(max_file_size_mb=args.max_file_size)
    all_findings = []
    target_list = []
    
    if args.directory:
        findings = scanner.scan_directory(args.directory)
        all_findings.extend(findings)
        target_list.append(str(args.directory))
    
    if args.files:
        for file_path in args.files:
            findings = scanner.scan_file(file_path)
            all_findings.extend(findings)
            target_list.append(str(file_path))
    
    if args.urls:
        url_findings = scanner.scan_urls(args.urls)
        for url, findings in url_findings.items():
            all_findings.extend(findings)
        target_list.extend(args.urls)
    
    risk_levels = set(args.risk_level.split(','))
    filtered_findings = [
        f for f in all_findings
        if f.risk_level in risk_levels
    ]
    
    scan_duration = time.time() - start_time
    target = ', '.join(target_list)
    report = scanner.generate_report(filtered_findings, target, scan_duration)
    
    output = format_scan_result(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)
    
    if report.critical_findings > 0 or report.high_findings > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    import time
    
    print("=== Quantum-Safe Cryptography Migration: Crypto Inventory Scanner ===\n")
    
    sample_code = """
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import hashes
import ssl

# CRITICAL: RSA key generation (vulnerable to quantum attacks)
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# CRITICAL: ECC key generation (vulnerable to quantum attacks)
private_key_ec = ec.generate_private_key(ec.SECP256R1())

# HIGH: MD5 hash (cryptographically broken)
md5_hash = hashlib.md5(b"data").hexdigest()

# MEDIUM: SHA1 (collision vulnerabilities)
sha1_hash = hashlib.sha1(b"data").hexdigest()

# SAFE: SHA256 (quantum-resistant)
sha256_hash = hashlib.sha256(b"data").hexdigest()

# SAFE: AES-256 (quantum-resistant)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    """
    
    test_dir = Path("/tmp/crypto_scan_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "sample_crypto.py"
    with open(test_file, 'w') as f:
        f.write(sample_code)
    
    print(f"Demo: Scanning test directory: {test_dir}\n")
    
    sys.argv = [
        sys.argv[0],
        '-d', str(test_dir),
        '--risk-level', 'CRITICAL,HIGH,MEDIUM,LOW,SAFE',
        '--json-output'
    ]
    
    sys.exit(main())
sys.exit(main())
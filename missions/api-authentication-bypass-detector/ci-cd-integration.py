#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    CI/CD integration
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-31T18:47:04.858Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: CI/CD integration for API Authentication Bypass Detector
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2024-12-19

Automated security scanner that detects JWT vulnerabilities, IDOR flaws,
OAuth misconfigurations, mass assignment, and broken rate limiting in REST APIs.
Integrates with CI/CD pipelines to scan API endpoints during build/test phases.
"""

import argparse
import json
import sys
import hashlib
import hmac
import base64
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class VulnerabilityType(Enum):
    """Types of API authentication vulnerabilities."""
    JWT_NO_SIGNATURE = "jwt_no_signature"
    JWT_WEAK_SECRET = "jwt_weak_secret"
    JWT_ALGORITHM_CONFUSION = "jwt_algorithm_confusion"
    IDOR_PREDICTABLE_ID = "idor_predictable_id"
    IDOR_MISSING_AUTH = "idor_missing_auth"
    OAUTH_REDIRECT_VALIDATION = "oauth_redirect_validation"
    OAUTH_TOKEN_REUSE = "oauth_token_reuse"
    MASS_ASSIGNMENT = "mass_assignment"
    RATE_LIMIT_MISSING = "rate_limit_missing"
    RATE_LIMIT_BYPASS = "rate_limit_bypass"
    WEAK_API_KEY = "weak_api_key"
    HEADER_INJECTION = "header_injection"
    CORS_MISCONFIGURATION = "cors_misconfiguration"


class SeverityLevel(Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Vulnerability:
    """Represents a detected vulnerability."""
    vuln_type: VulnerabilityType
    severity: SeverityLevel
    endpoint: str
    method: str
    description: str
    evidence: str
    recommendation: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.vuln_type.value,
            "severity": self.severity.value,
            "endpoint": self.endpoint,
            "method": self.method,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp
        }


@dataclass
class ScanResult:
    """Results from scanning an API endpoint."""
    endpoint: str
    method: str
    status_code: int
    vulnerabilities: List[Vulnerability]
    response_time: float
    headers: Dict[str, str]
    scan_timestamp: str


class JWTAnalyzer:
    """Analyzes JWT tokens for vulnerabilities."""

    @staticmethod
    def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
        """Safely decode JWT without verification."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None

    @staticmethod
    def check_signature_validation(token: str) -> Tuple[bool, str]:
        """Check if JWT validates signature properly."""
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Invalid JWT format"
        
        if not parts[2]:
            return False, "Missing signature component"
        
        if parts[2] == "":
            return False, "Empty signature - no signature verification"
        
        return True, "Signature present"

    @staticmethod
    def check_algorithm(token: str) -> Tuple[bool, str, str]:
        """Check JWT algorithm for weaknesses."""
        try:
            parts = token.split('.')
            header_b64 = parts[0]
            padding = 4 - len(header_b64) % 4
            if padding != 4:
                header_b64 += '=' * padding
            
            header = json.loads(base64.urlsafe_b64decode(header_b64))
            algorithm = header.get('alg', 'unknown')
            
            weak_algorithms = ['none', 'HS256', 'HS384', 'HS512']
            is_weak = algorithm in weak_algorithms or algorithm == 'none'
            
            return is_weak, algorithm, header
        except Exception:
            return False, "unknown", {}

    @staticmethod
    def check_expiration(token: str) -> Tuple[bool, str]:
        """Check if token has proper expiration."""
        payload = JWTAnalyzer.decode_jwt(token)
        if not payload:
            return False, "Cannot decode payload"
        
        if 'exp' not in payload:
            return False, "No expiration claim found"
        
        exp_time = payload['exp']
        current_time = int(time.time())
        
        if exp_time > current_time:
            return False, f"Token valid until {datetime.fromtimestamp(exp_time)}"
        
        return True, "Token expired"


class IDORDetector:
    """Detects Insecure Direct Object Reference vulnerabilities."""

    @staticmethod
    def analyze_id_patterns(url: str) -> List[Tuple[str, str]]:
        """Identify ID patterns in URL."""
        patterns = [
            (r'/users/(\d+)', 'numeric_user_id'),
            (r'/api/v\d+/resources/(\d+)', 'numeric_resource_id'),
            (r'/item/(\d+)', 'numeric_item_id'),
            (r'/id=(\d+)', 'query_numeric_id'),
            (r'/uuid=([a-f0-9\-]{36})', 'uuid_id'),
            (r'/([a-f0-9]{32})', 'md5_hash_id'),
        ]
        
        found_ids = []
        for pattern, id_type in patterns:
            matches = re.findall(pattern, url)
            for match in matches:
                found_ids.append((match, id_type))
        
        return found_ids

    @staticmethod
    def check_predictability(id_value: str, id_type: str) -> Tuple[bool, str]:
        """Check if ID values are predictable."""
        if id_type == 'numeric_user_id':
            try:
                id_num = int(id_value)
                if id_num < 10000:
                    return True, f"Sequential numeric ID: {id_value}"
            except ValueError:
                pass
        
        if id_type == 'numeric_resource_id':
            try:
                id_num = int(id_value)
                if id_num % 100 == 0 or id_num < 1000:
                    return True, f"Predictable numeric pattern: {id_value}"
            except ValueError:
                pass
        
        return False, "ID pattern not obviously predictable"

    @staticmethod
    def detect_missing_auth(headers: Dict[str, str], status_code: int) -> Tuple[bool, str]:
        """Detect if endpoint missing authentication."""
        auth_headers = ['authorization', 'x-api-key', 'x-auth-token']
        has_auth = any(h in headers.get(k, '').lower() for h in auth_headers 
                       for k in headers.keys())
        
        if not has_auth and status_code == 200:
            return True, "No authentication headers detected, endpoint returned 200"
        
        return False, "Authentication appears required"


class OAuthAnalyzer:
    """Analyzes OAuth configurations."""

    @staticmethod
    def check_redirect_uri(redirect_uri: str) -> Tuple[bool, str]:
        """Check for open redirect vulnerabilities."""
        dangerous_patterns = [
            r'javascript:',
            r'data:',
            r'//.*example\.com',
            r'redirect=.*\$\{',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, redirect_uri, re.IGNORECASE):
                return True, f"Dangerous redirect pattern detected: {pattern}"
        
        try:
            parsed = urllib.parse.urlparse(redirect_uri)
            if parsed.scheme not in ['http', 'https']:
                return True, f"Suspicious scheme: {parsed.scheme}"
        except Exception:
            return True, "Invalid redirect URI format"
        
        return False, "Redirect URI appears valid"

    @staticmethod
    def check_token_scope(token: str) -> Tuple[List[str], str]:
        """Extract and analyze token scopes."""
        payload = JWTAnalyzer.decode_jwt(token)
        if not payload:
            return [], "Cannot decode token"
        
        scope = payload.get('scope', '')
        if isinstance(scope, str):
            scopes = scope.split()
        else:
            scopes = payload.get('scopes', [])
        
        if not scopes:
            return [], "No scopes defined"
        
        return scopes, f"Scopes: {', '.join(scopes)}"


class RateLimitAnalyzer:
    """Analyzes rate limiting implementations."""

    @staticmethod
    def check_rate_limit_headers(headers: Dict[str, str]) -> Tuple[bool, Dict[str, str]]:
        """Check for rate limit headers."""
        rate_limit_headers = {
            'X-RateLimit-Limit': None,
            'X-RateLimit-Remaining': None,
            'X-RateLimit-Reset': None,
            'RateLimit-Limit': None,
            'RateLimit-Remaining': None,
            'RateLimit-Reset': None,
        }
        
        found_headers = {}
        for key, value in headers.items():
            if key in rate_limit_headers or any(h in key for h in ['ratelimit', 'rate-limit']):
                found_headers[key] = value
        
        has_rate_limit = bool(found_headers)
        return has_rate_limit, found_headers

    @staticmethod
    def analyze_rate_limit_values(headers: Dict[str, str]) -> Tuple[bool, str]:
        """Analyze if rate limits are reasonable."""
        for key, value in headers.items():
            if 'limit' in key.lower():
                try:
                    limit = int(value)
                    if limit > 10000:
                        return False, f"Rate limit very high: {limit} requests"
                    if limit < 10:
                        return True, f"Rate limit very restrictive: {limit} requests"
                except ValueError:
                    pass
        
        return False, "Rate limits appear reasonable"


class MassAssignmentDetector:
    """Detects mass assignment vulnerabilities."""

    @staticmethod
    def check_request_body(body: str, endpoint: str) -> Tuple[bool, str]:
        """Check for mass assignment vulnerabilities."""
        dangerous_fields = [
            'is_admin', 'admin', 'role', 'permission', 'is_verified',
            'verified', 'is_premium', 'premium', 'access_level',
            'privilege_level', 'user_type', 'account_type'
        ]
        
        body_lower = body.lower()
        found_dangerous = []
        
        for field in dangerous_fields:
            if field in body_lower:
                found_dangerous.append(field)
        
        if found_dangerous:
            return True, f"Dangerous fields in request: {', '.join(found_dangerous)}"
        
        return False, "No obvious mass assignment fields detected"


class APISecurityScanner:
    """Main API security scanner."""

    def __init__(self, fail_on_severity: str = "high"):
        self.vulnerabilities: List[Vulnerability] = []
        self.scan_results: List[ScanResult] = []
        self.fail_on_severity = SeverityLevel[fail_on_severity.upper()]

    def scan_jwt_token(self, token: str, endpoint: str = "jwt_endpoint") -> List[Vulnerability]:
        """Scan JWT token for vulnerabilities."""
        vulns = []
        
        has_sig, sig_msg = JWTAnalyzer.check_signature_validation(token)
        if not has_sig:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.JWT_NO_SIGNATURE,
                severity=SeverityLevel.CRITICAL,
                endpoint=endpoint,
                method="POST",
                description="JWT token missing or empty signature",
                evidence=sig_msg,
                recommendation="Implement proper JWT signature validation",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        is_weak_alg, alg, header = JWTAnalyzer.check_algorithm(token)
        if is_weak_alg:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.JWT_ALGORITHM_CONFUSION,
                severity=SeverityLevel.CRITICAL,
                endpoint=endpoint,
                method="POST",
                description=f"JWT using weak/none algorithm: {alg}",
                evidence=f"Header: {json.dumps(header)}",
                recommendation="Use strong algorithms like RS256, not HS256 or 'none'",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        is_expired, exp_msg = JWTAnalyzer.check_expiration(token)
        if not is_expired:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.JWT_WEAK_SECRET,
                severity=SeverityLevel.MEDIUM,
                endpoint=endpoint,
                method="POST",
                description="JWT token does not have proper expiration",
                evidence=exp_msg,
                recommendation="Add 'exp' claim and validate expiration server-side",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        self.vulnerabilities.extend(vulns)
        return vulns

    def scan_endpoint_idor(self, endpoint: str, method: str = "GET",
                          headers: Optional[Dict[str, str]] = None,
                          status_code: int = 200) -> List[Vulnerability]:
        """Scan endpoint for IDOR vulnerabilities."""
        vulns = []
        if headers is None:
            headers = {}
        
        id_patterns = IDORDetector.analyze_id_patterns(endpoint)
        for id_value, id_type in id_patterns:
            is_predictable, pred_msg = IDORDetector.check_predictability(id_value, id_type)
            if is_predictable:
                vulns.append(Vulnerability(
                    vuln_type=VulnerabilityType.IDOR_PREDICTABLE_ID,
                    severity=SeverityLevel.HIGH,
                    endpoint=endpoint,
                    method=method,
                    description="Predictable ID pattern detected",
                    evidence=pred_msg,
                    recommendation="Use UUIDs or cryptographically random IDs",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        is_missing_auth, auth_msg = IDORDetector.detect_missing_auth(headers, status_code)
        if is_missing_auth:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.IDOR_MISSING_AUTH,
                severity=SeverityLevel.CRITICAL,
                endpoint=endpoint,
                method=method,
                description="Missing authentication on resource endpoint",
                evidence=auth_msg,
                recommendation="Implement proper authentication and authorization checks",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        self.vulnerabilities.extend(vulns)
        return vulns

    def scan_oauth_config(self, redirect_uri: str, token: str = "",
                         endpoint: str = "/oauth/authorize") -> List[Vulnerability]:
        """Scan OAuth configuration."""
        vulns = []
        
        is_dangerous, redirect_msg = OAuthAnalyzer.check_redirect_uri(redirect_uri)
        if is_dangerous:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.OAUTH_REDIRECT_VALIDATION,
                severity=SeverityLevel.HIGH,
                endpoint=endpoint,
                method="GET",
                description="Unsafe OAuth redirect URI",
                evidence=redirect_msg,
                recommendation="Validate redirect URIs against whitelist",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        if token:
            scopes, scope_msg = OAuthAnalyzer.check_token_scope(token)
            if not scopes:
                vulns.append(Vulnerability(
                    vuln_type=VulnerabilityType.OAUTH_TOKEN_REUSE,
                    severity=SeverityLevel.MEDIUM,
                    endpoint=endpoint,
                    method="POST",
                    description="OAuth token missing scope restrictions",
                    evidence=scope_msg,
                    recommendation="Define and enforce appropriate scopes for tokens",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        self.vulnerabilities.extend(vulns)
        return vulns

    def scan_mass_assignment(self, endpoint: str, request_body: str,
                            method: str = "POST") -> List[Vulnerability]:
        """Scan for mass assignment vulnerabilities."""
        vulns = []
        
        is_vulnerable, ma_msg = MassAssignmentDetector.check_request_body(request_body, endpoint)
        if is_vulnerable:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.MASS_ASSIGNMENT,
                severity=SeverityLevel.HIGH,
                endpoint=endpoint,
                method=method,
                description="Potential mass assignment vulnerability",
                evidence=ma_msg,
                recommendation="Whitelist allowed fields, reject unknown parameters",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        self.vulnerabilities.extend(vulns)
        return vulns

    def scan_rate_limiting(self, endpoint: str, headers: Optional[Dict[str, str]] = None,
                          method: str = "GET") -> List[Vulnerability]:
        """Scan for rate limiting issues."""
        vulns = []
        if headers is None:
            headers = {}
        
        has_rate_limit, rl_headers = RateLimitAnalyzer.check_rate_limit_headers(headers)
        if not has_rate_limit:
            vulns.append(Vulnerability(
                vuln_type=VulnerabilityType.RATE_LIMIT_MISSING,
                severity=SeverityLevel.MEDIUM,
                endpoint=endpoint,
                method=method,
                description="Missing rate limiting headers",
                evidence="No X-RateLimit or RateLimit headers found",
                recommendation="Implement rate limiting and advertise via headers",
                timestamp=datetime.utcnow().isoformat()
            ))
        else:
            is_weak, weakness_msg = RateLimitAnalyzer.analyze_rate_limit_values(rl_headers)
            if is_weak:
                vulns.append(Vulnerability(
                    vuln_type=VulnerabilityType.RATE_LIMIT_BYPASS,
                    severity=SeverityLevel.MEDIUM,
                    endpoint=endpoint,
                    method=method,
                    description="Rate limits may be bypassable",
                    evidence=weakness_msg,
                    recommendation="Review rate limit thresholds and enforcement",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        self.vulnerabilities.extend(vulns)
        return vulns

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        now = datetime.utcnow().isoformat()
        
        severity_counts = {}
        for vuln in self.vulnerabilities:
            sev = vuln.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        vulnerability_types = {}
        for vuln in self.vulnerabilities:
            vtype = vuln.vuln_type.value
            vulnerability_types[vtype] = vulnerability_types.get(vtype, 0) + 1
        
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)
        
        return {
            "scan_timestamp": now,
            "total_vulnerabilities": len(self.vulnerabilities),
            "severity_distribution": severity_counts,
            "vulnerability_types": vulnerability_types,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "scan_passed": critical_count == 0 and high_count <= 2,
            "critical_count": critical_count,
            "high_count": high_count,
        }

    def should_fail_build(self) -> bool:
        """Determine if build should fail based on findings."""
        for vuln in self.vulnerabilities:
            if vuln.severity == SeverityLevel.CRITICAL:
                return True
            if vuln.severity == SeverityLevel.HIGH and self.fail_on_severity == SeverityLevel.HIGH:
                return True
            if vuln.severity == SeverityLevel.MEDIUM and self.fail_on_severity == SeverityLevel.MEDIUM:
                return True
        
        return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="API Authentication Bypass Detector - CI/CD Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --scan-jwt eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0.
  %(prog)s --scan-endpoint /api/users/123 --method GET --status-code 200
  %(prog)s --scan-mass-assignment /api/users --body '{"is_admin":true}'
  %(prog)s --scan-rate-limit /api/data --headers "X-RateLimit-Limit: 100"
        """
    )
    
    parser.add_argument('--scan-jwt', type=str, dest='jwt_token',
                        help='JWT token to scan for vulnerabilities')
    
    parser.add_argument('--scan-endpoint', type=str, dest='endpoint',
                        help='API endpoint to scan for IDOR/auth issues')
    
    parser.add_argument('--method', type=str, default='GET',
                        choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
                        help='HTTP method for endpoint scan')
    
    parser.add_argument('--status-code', type=int, default=200,
                        help='HTTP status code returned by endpoint')
    
    parser.add_argument('--headers', type=str,
                        help='Headers as JSON or key:value pairs')
    
    parser.add_argument('--scan-oauth', type=str, dest='redirect_uri',
                        help='OAuth redirect URI to validate')
    
    parser.add_argument('--scan-mass-assignment', type=str, dest='mass_assign_endpoint',
                        help='Endpoint to check for mass assignment')
    
    parser.add_argument('--body', type=str,
                        help='Request body for mass assignment/other scans')
    
    parser.add_argument('--scan-rate-limit', type=str, dest='rate_limit_endpoint',
                        help='Endpoint to check for rate limiting')
    
    parser.add_argument('--fail-on-severity', type=str, default='high',
                        choices=['critical', 'high', 'medium', 'low'],
                        help='Severity level that causes build failure')
    
    parser.add_argument('--output-format', type=str, default='json',
                        choices=['json', 'text'],
                        help='Output format for report')
    
    parser.add_argument('--output-file', type=str,
                        help='Output file for report (default: stdout)')
    
    parser.add_argument('--ci-mode', action='store_true',
                        help='CI/CD mode - exit with failure code if vulnerabilities found')
    
    return parser


def parse_headers(headers_str: str) -> Dict[str, str]:
    """Parse headers from string format."""
    headers = {}
    
    if headers_str.startswith('{'):
        try:
            headers = json.loads(headers_str)
        except json.JSONDecodeError:
            pass
    else:
        pairs = headers_str.split(',')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                headers[key.strip()] = value.strip()
    
    return headers


def format_text_report(report: Dict[str, Any]) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("API AUTHENTICATION BYPASS DETECTOR - SECURITY REPORT")
    lines.append("=" * 70)
    lines.append(f"Scan Timestamp: {report['scan_timestamp']}")
    lines.append("")
    
    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total Vulnerabilities: {report['total_vulnerabilities']}")
    lines.append(f"Critical: {report.get('critical_count', 0)}")
    lines.append(f"High: {report.get('high_count', 0)}")
    lines.append(f"Scan Passed: {report['scan_passed']}")
    lines.append("")
    
    if report['severity_distribution']:
        lines.append("SEVERITY DISTRIBUTION")
        lines.append("-" * 70)
        for severity, count in sorted(report['severity_distribution'].items()):
            lines.append(f"  {severity.upper()}: {count}")
        lines.append("")
    
    if report['vulnerability_types']:
        lines.append("VULNERABILITY TYPES")
        lines.append("-" * 70)
        for vtype, count in sorted(report['vulnerability_types'].items()):
            lines.append(f"  {vtype}: {count}")
        lines.append("")
    
    if report['vulnerabilities']:
        lines.append("DETAILED FINDINGS")
        lines.append("-" * 70)
        for i, vuln in enumerate(report['vulnerabilities'], 1):
            lines.append(f"\n{i}. [{vuln['severity'].upper()}] {vuln['type']}")
            lines.append(f"   Endpoint: {vuln['endpoint']} ({vuln['method']})")
            lines.append(f"   Description: {vuln['description']}")
            lines.append(f"   Evidence: {vuln['evidence']}")
            lines.append(f"   Recommendation: {vuln['recommendation']}")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    scanner = APISecurityScanner(fail_on_severity=args.fail_on_severity)
    
    if args.jwt_token:
        scanner.scan_jwt_token(args.jwt_token)
    
    if args.endpoint:
        headers = {}
        if args.headers:
            headers = parse_headers(args.headers)
        scanner.scan_endpoint_idor(args.endpoint, method=args.method,
                                   headers=headers, status_code=args.status_code)
    
    if args.redirect_uri:
        token = args.jwt_token if args.jwt_token else ""
        scanner.scan_oauth_config(args.redirect_uri, token=token)
    
    if args.mass_assign_endpoint and args.body:
        scanner.scan_mass_assignment(args.mass_assign_endpoint, args.body, method=args.method)
    
    if args.rate_limit_endpoint:
        headers = {}
        if args.headers:
            headers = parse_headers(args.headers)
        scanner.scan_rate_limiting(args.rate_limit_endpoint, headers=headers, method=args.method)
    
    report = scanner.generate_report()
    
    if args.output_format == 'json':
        output = json.dumps(report, indent=2)
    else:
        output = format_text_report(report)
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"Report written to {args.output_file}")
    else:
        print(output)
    
    if args.ci_mode and scanner.should_fail_build():
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    print("=" * 70)
    print("API Authentication Bypass Detector - CI/CD Integration Demo")
    print("=" * 70)
    
    scanner = APISecurityScanner(fail_on_severity='high')
    
    print("\n[*] Demo 1: Scanning JWT with 'none' algorithm...")
    jwt_none = "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwiYWRtaW4iOnRydWUsImV4cCI6MTcwMzA0MDAwMH0."
    scanner.scan_jwt_token(jwt_none, endpoint="/api/auth/token")
    
    print("[*] Demo 2: Scanning endpoint for IDOR vulnerabilities...")
    scanner.scan_endpoint_idor("/api/users/123", method="GET",
                               headers={"Content-Type": "application/json"},
                               status_code=200)
    
    print("[*] Demo 3: Scanning OAuth redirect URI...")
    scanner.scan_oauth_config("https://attacker.com/callback", endpoint="/oauth/authorize")
    
    print("[*] Demo 4: Scanning for mass assignment...")
    scanner.scan_mass_assignment("/api/users/update",
                                 request_body='{"name":"John","is_admin":true}')
    
    print("[*] Demo 5: Scanning rate limiting...")
    scanner.scan_rate_limiting("/api/data", headers={}, method="GET")
    
    print("[*] Demo 6: Scanning endpoint without rate limit headers...")
    scanner.scan_rate_limiting("/api/public/search",
                               headers={"Content-Type": "application/json"},
                               method="GET")
    
    print("\n" + "=" * 70)
    print("SCAN RESULTS")
    print("=" * 70)
    
    report = scanner.generate_report()
    print(format_text_report(report))
    
    print("\n" + "=" * 70)
    print("RAW JSON REPORT")
    print("=" * 70)
    print(json.dumps(report, indent=2))
    
    if scanner.should_fail_build():
        print("\n[!] Build would FAIL - Critical/High vulnerabilities detected")
    else:
        print("\n[+] Build would PASS - No blocking vulnerabilities")
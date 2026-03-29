#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Mass assignment scanner
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-29T13:17:45.888Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Mass assignment scanner
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2025-01-14

Automated security scanner that detects mass assignment vulnerabilities in REST APIs.
Mass assignment (also called over-posting) occurs when an API accepts and processes
user-supplied fields that should not be modifiable, potentially allowing privilege escalation
or unauthorized data modification.
"""

import argparse
import json
import sys
from typing import Dict, List, Tuple, Any
from urllib.parse import urljoin
import re
from dataclasses import dataclass, asdict
from enum import Enum


class VulnerabilityLevel(Enum):
    """Severity levels for detected vulnerabilities."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class MassAssignmentVuln:
    """Represents a detected mass assignment vulnerability."""
    endpoint: str
    method: str
    vulnerable_fields: List[str]
    severity: str
    description: str
    request_body: Dict[str, Any]
    response_indicators: List[str]
    remediation: str


class MassAssignmentDetector:
    """Detects mass assignment vulnerabilities in API endpoints."""
    
    # Fields that should typically be immutable
    PROTECTED_FIELDS = {
        'id': VulnerabilityLevel.HIGH,
        'user_id': VulnerabilityLevel.HIGH,
        'admin': VulnerabilityLevel.CRITICAL,
        'is_admin': VulnerabilityLevel.CRITICAL,
        'role': VulnerabilityLevel.CRITICAL,
        'roles': VulnerabilityLevel.CRITICAL,
        'permissions': VulnerabilityLevel.HIGH,
        'is_superuser': VulnerabilityLevel.CRITICAL,
        'superuser': VulnerabilityLevel.CRITICAL,
        'created_at': VulnerabilityLevel.MEDIUM,
        'updated_at': VulnerabilityLevel.MEDIUM,
        'created_date': VulnerabilityLevel.MEDIUM,
        'modified_date': VulnerabilityLevel.MEDIUM,
        'password_hash': VulnerabilityLevel.CRITICAL,
        'password': VulnerabilityLevel.HIGH,
        'api_key': VulnerabilityLevel.CRITICAL,
        'api_secret': VulnerabilityLevel.CRITICAL,
        'secret': VulnerabilityLevel.CRITICAL,
        'token': VulnerabilityLevel.HIGH,
        'access_token': VulnerabilityLevel.HIGH,
        'refresh_token': VulnerabilityLevel.HIGH,
        'is_active': VulnerabilityLevel.HIGH,
        'is_deleted': VulnerabilityLevel.MEDIUM,
        'deleted_at': VulnerabilityLevel.MEDIUM,
        'last_login': VulnerabilityLevel.LOW,
        'balance': VulnerabilityLevel.CRITICAL,
        'credits': VulnerabilityLevel.CRITICAL,
        'subscription_level': VulnerabilityLevel.HIGH,
        'plan': VulnerabilityLevel.HIGH,
        'premium': VulnerabilityLevel.HIGH,
        'verified': VulnerabilityLevel.MEDIUM,
        'email_verified': VulnerabilityLevel.MEDIUM,
        'phone_verified': VulnerabilityLevel.MEDIUM,
        'two_factor_enabled': VulnerabilityLevel.MEDIUM,
    }
    
    # Patterns that suggest sensitive operations
    SENSITIVE_PATTERNS = [
        r'.*_at$',  # timestamp fields
        r'^created.*',
        r'^modified.*',
        r'^updated.*',
        r'.*_date$',
        r'^is_.*',
        r'^admin.*',
        r'.*_admin$',
    ]
    
    def __init__(self, verbose: bool = False):
        """Initialize the mass assignment detector."""
        self.verbose = verbose
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]
    
    def check_field_for_mass_assignment(self, field_name: str) -> Tuple[bool, VulnerabilityLevel]:
        """
        Check if a field is vulnerable to mass assignment.
        
        Returns:
            Tuple of (is_vulnerable, severity_level)
        """
        field_lower = field_name.lower()
        
        # Check against protected fields
        if field_lower in self.PROTECTED_FIELDS:
            return True, self.PROTECTED_FIELDS[field_lower]
        
        # Check against patterns
        for pattern in self.compiled_patterns:
            if pattern.match(field_lower):
                return True, VulnerabilityLevel.MEDIUM
        
        return False, VulnerabilityLevel.INFO
    
    def analyze_request_body(self, endpoint: str, method: str, 
                            request_body: Dict[str, Any]) -> List[MassAssignmentVuln]:
        """
        Analyze a request body for potential mass assignment vulnerabilities.
        
        Args:
            endpoint: API endpoint URL or path
            method: HTTP method (POST, PUT, PATCH)
            request_body: Request body as dictionary
            
        Returns:
            List of detected vulnerabilities
        """
        vulnerabilities = []
        vulnerable_fields = []
        max_severity = VulnerabilityLevel.INFO
        
        if not isinstance(request_body, dict):
            return vulnerabilities
        
        for field_name in request_body.keys():
            is_vuln, severity = self.check_field_for_mass_assignment(field_name)
            
            if is_vuln:
                vulnerable_fields.append(field_name)
                if severity.value > max_severity.value:
                    max_severity = severity
                
                if self.verbose:
                    print(f"[*] Found vulnerable field: {field_name} (severity: {severity.name})", 
                          file=sys.stderr)
        
        if vulnerable_fields:
            response_indicators = [
                f"Field '{f}' was successfully modified" for f in vulnerable_fields[:3]
            ]
            
            remediation = (
                f"Implement strict parameter binding/whitelisting for endpoint {endpoint}. "
                f"Only allow modifications to: name, description, email. "
                f"Use ORM model property binding or explicit DTO validation."
            )
            
            vuln = MassAssignmentVuln(
                endpoint=endpoint,
                method=method,
                vulnerable_fields=vulnerable_fields,
                severity=max_severity.name,
                description=f"Mass assignment vulnerability: {len(vulnerable_fields)} "
                           f"protected field(s) can be modified directly via {method} request",
                request_body=request_body,
                response_indicators=response_indicators,
                remediation=remediation
            )
            vulnerabilities.append(vuln)
        
        return vulnerabilities
    
    def scan_endpoints(self, endpoints_config: List[Dict[str, Any]]) -> List[MassAssignmentVuln]:
        """
        Scan multiple API endpoints for mass assignment vulnerabilities.
        
        Args:
            endpoints_config: List of endpoint configurations with method and sample payloads
            
        Returns:
            List of all detected vulnerabilities
        """
        all_vulns = []
        
        for config in endpoints_config:
            endpoint = config.get('endpoint', '')
            method = config.get('method', 'POST').upper()
            payloads = config.get('payloads', [])
            
            if not isinstance(payloads, list):
                payloads = [payloads]
            
            for payload in payloads:
                vulns = self.analyze_request_body(endpoint, method, payload)
                all_vulns.extend(vulns)
        
        return all_vulns
    
    def generate_report(self, vulnerabilities: List[MassAssignmentVuln], 
                       output_format: str = 'json') -> str:
        """
        Generate a security report from detected vulnerabilities.
        
        Args:
            vulnerabilities: List of detected vulnerabilities
            output_format: Output format ('json' or 'text')
            
        Returns:
            Formatted report string
        """
        if output_format == 'json':
            return self._generate_json_report(vulnerabilities)
        else:
            return self._generate_text_report(vulnerabilities)
    
    def _generate_json_report(self, vulnerabilities: List[MassAssignmentVuln]) -> str:
        """Generate JSON format report."""
        report = {
            'scan_type': 'mass_assignment',
            'total_vulnerabilities': len(vulnerabilities),
            'by_severity': self._count_by_severity(vulnerabilities),
            'vulnerabilities': [asdict(v) for v in vulnerabilities]
        }
        return json.dumps(report, indent=2)
    
    def _generate_text_report(self, vulnerabilities: List[MassAssignmentVuln]) -> str:
        """Generate human-readable text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("MASS ASSIGNMENT VULNERABILITY SCAN REPORT")
        lines.append("=" * 80)
        lines.append(f"\nTotal Vulnerabilities Found: {len(vulnerabilities)}\n")
        
        severity_counts = self._count_by_severity(vulnerabilities)
        lines.append("Breakdown by Severity:")
        for severity, count in sorted(severity_counts.items(), reverse=True):
            lines.append(f"  {severity}: {count}")
        lines.append("")
        
        for vuln in sorted(vulnerabilities, 
                          key=lambda v: self._severity_to_int(v.severity), 
                          reverse=True):
            lines.append("-" * 80)
            lines.append(f"Endpoint: {vuln.endpoint}")
            lines.append(f"Method: {vuln.method}")
            lines.append(f"Severity: {vuln.severity}")
            lines.append(f"Description: {vuln.description}")
            lines.append(f"Vulnerable Fields: {', '.join(vuln.vulnerable_fields)}")
            lines.append(f"Remediation: {vuln.remediation}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _count_by_severity(self, vulnerabilities: List[MassAssignmentVuln]) -> Dict[str, int]:
        """Count vulnerabilities by severity level."""
        counts = {level.name: 0 for level in VulnerabilityLevel}
        for vuln in vulnerabilities:
            counts[vuln.severity] += 1
        return {k: v for k, v in counts.items() if v > 0}
    
    @staticmethod
    def _severity_to_int(severity: str) -> int:
        """Convert severity string to integer for sorting."""
        severity_order = {
            'CRITICAL': 5,
            'HIGH': 4,
            'MEDIUM': 3,
            'LOW': 2,
            'INFO': 1
        }
        return severity_order.get(severity, 0)


def create_sample_endpoints() -> List[Dict[str, Any]]:
    """Generate sample API endpoints for testing."""
    return [
        {
            'endpoint': '/api/v1/users/123',
            'method': 'PUT',
            'payloads': [
                {
                    'name': 'John Updated',
                    'email': 'john@example.com',
                    'admin': True,
                    'role': 'superuser',
                    'is_active': False
                }
            ]
        },
        {
            'endpoint': '/api/v1/users/123',
            'method': 'PATCH',
            'payloads': [
                {
                    'bio': 'Updated bio',
                    'balance': 10000,
                    'subscription_level': 'premium'
                }
            ]
        },
        {
            'endpoint': '/api/v1/products',
            'method': 'POST',
            'payloads': [
                {
                    'name': 'New Product',
                    'description': 'Product description',
                    'price': 99.99,
                    'featured': True,
                    'is_deleted': False
                }
            ]
        },
        {
            'endpoint': '/api/v1/orders/456',
            'method': 'PUT',
            'payloads': [
                {
                    'status': 'pending',
                    'total': 150.00,
                    'is_admin': True,
                    'permissions': ['read', 'write', 'delete']
                }
            ]
        }
    ]


def main():
    """Main entry point for the mass assignment scanner."""
    parser = argparse.ArgumentParser(
        description='Mass Assignment Vulnerability Scanner for REST APIs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --endpoint /api/users --method POST --payload '{"name":"test","admin":true}'
  %(prog)s --config endpoints.json --output report.json --format json
  %(prog)s --demo --verbose --format text
        '''
    )
    
    parser.add_argument(
        '--endpoint',
        type=str,
        help='Single endpoint to scan (e.g., /api/v1/users)'
    )
    
    parser.add_argument(
        '--method',
        type=str,
        choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        default='POST',
        help='HTTP method for the endpoint'
    )
    
    parser.add_argument(
        '--payload',
        type=str,
        help='Request body as JSON string'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file with multiple endpoints (JSON format)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for the report'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='json',
        help='Report output format'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run with sample data for demonstration'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    detector = MassAssignmentDetector(verbose=args.verbose)
    vulnerabilities = []
    
    if args.demo:
        if args.verbose:
            print("[*] Running mass assignment scanner in demo mode...", file=sys.stderr)
        endpoints = create_sample_endpoints()
        vulnerabilities = detector.scan_endpoints(endpoints)
    
    elif args.config:
        if args.verbose:
            print(f"[*] Loading configuration from {args.config}", file=sys.stderr)
        try:
            with open(args.config, 'r') as f:
                endpoints = json.load(f)
            vulnerabilities = detector.scan_endpoints(endpoints)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading config file: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.endpoint and args.payload:
        if args.verbose:
            print(f"[*] Scanning endpoint: {args.endpoint}", file=sys.stderr)
        try:
            payload = json.loads(args.payload)
            endpoint_config = [{
                'endpoint': args.endpoint,
                'method': args.method,
                'payloads': [payload]
            }]
            vulnerabilities = detector.scan_endpoints(endpoint_config)
        except json.JSONDecodeError as e:
            print(f"Error parsing payload JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    else
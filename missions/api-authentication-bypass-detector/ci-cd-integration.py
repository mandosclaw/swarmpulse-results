#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    CI/CD integration
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:38.581Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: CI/CD integration
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2024

Automated security scanner that detects JWT vulnerabilities, IDOR flaws,
OAuth misconfigurations, mass assignment, and broken rate limiting in REST APIs.
Includes CI/CD pipeline integration for automated security testing.
"""

import argparse
import json
import sys
import subprocess
import hashlib
import base64
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import urllib.parse


@dataclass
class VulnerabilityFinding:
    """Represents a single security vulnerability finding."""
    vuln_id: str
    severity: str
    category: str
    endpoint: str
    description: str
    remediation: str
    timestamp: str
    evidence: str


@dataclass
class ScanResult:
    """Complete scan result summary."""
    scan_id: str
    timestamp: str
    total_findings: int
    critical: int
    high: int
    medium: int
    low: int
    findings: List[VulnerabilityFinding]
    passed: bool


class JWTAnalyzer:
    """Analyzes JWT tokens for security vulnerabilities."""
    
    def __init__(self):
        self.findings = []
    
    def analyze_jwt(self, token: str, endpoint: str) -> List[VulnerabilityFinding]:
        """Analyze JWT token for vulnerabilities."""
        findings = []
        
        parts = token.split('.')
        if len(parts) != 3:
            findings.append(VulnerabilityFinding(
                vuln_id="JWT_001",
                severity="CRITICAL",
                category="JWT",
                endpoint=endpoint,
                description="Invalid JWT structure detected",
                remediation="Ensure JWT has exactly 3 parts separated by dots",
                timestamp=datetime.now().isoformat(),
                evidence=f"Token has {len(parts)} parts instead of 3"
            ))
            return findings
        
        try:
            header = self._decode_jwt_part(parts[0])
            payload = self._decode_jwt_part(parts[1])
        except Exception as e:
            findings.append(VulnerabilityFinding(
                vuln_id="JWT_002",
                severity="HIGH",
                category="JWT",
                endpoint=endpoint,
                description="JWT decoding failed",
                remediation="Verify JWT encoding is valid base64url",
                timestamp=datetime.now().isoformat(),
                evidence=str(e)
            ))
            return findings
        
        if header.get('alg') == 'none':
            findings.append(VulnerabilityFinding(
                vuln_id="JWT_003",
                severity="CRITICAL",
                category="JWT",
                endpoint=endpoint,
                description="JWT algorithm set to 'none'",
                remediation="Never use 'none' algorithm; use RS256 or HS256",
                timestamp=datetime.now().isoformat(),
                evidence="alg claim is 'none'"
            ))
        
        if header.get('alg', '').startswith('HS'):
            if 'exp' not in payload:
                findings.append(VulnerabilityFinding(
                    vuln_id="JWT_004",
                    severity="HIGH",
                    category="JWT",
                    endpoint=endpoint,
                    description="JWT missing expiration claim",
                    remediation="Add 'exp' claim to limit token lifetime",
                    timestamp=datetime.now().isoformat(),
                    evidence="Missing 'exp' in payload"
                ))
        
        if isinstance(payload.get('sub'), dict) or isinstance(payload.get('user'), dict):
            findings.append(VulnerabilityFinding(
                vuln_id="JWT_005",
                severity="MEDIUM",
                category="JWT",
                endpoint=endpoint,
                description="JWT contains complex nested claims",
                remediation="Minimize claim complexity; use simple identifiers",
                timestamp=datetime.now().isoformat(),
                evidence=f"Complex claim structure detected"
            ))
        
        return findings
    
    def _decode_jwt_part(self, part: str) -> Dict[str, Any]:
        """Decode JWT part from base64url."""
        padding = 4 - (len(part) % 4)
        if padding != 4:
            part += '=' * padding
        decoded = base64.urlsafe_b64decode(part)
        return json.loads(decoded.decode('utf-8'))


class IDORDetector:
    """Detects Insecure Direct Object Reference vulnerabilities."""
    
    def __init__(self):
        self.findings = []
    
    def detect_idor(self, endpoint: str, parameters: Dict[str, str]) -> List[VulnerabilityFinding]:
        """Detect IDOR vulnerabilities in endpoint."""
        findings = []
        
        suspicious_params = ['id', 'user_id', 'account_id', 'object_id', 'resource_id']
        found_suspicious = False
        
        for param, value in parameters.items():
            if any(sus in param.lower() for sus in suspicious_params):
                found_suspicious = True
                
                if value.isdigit() and int(value) < 1000:
                    findings.append(VulnerabilityFinding(
                        vuln_id="IDOR_001",
                        severity="HIGH",
                        category="IDOR",
                        endpoint=endpoint,
                        description="Sequential ID parameter detected",
                        remediation="Use UUIDs or implement proper authorization checks",
                        timestamp=datetime.now().isoformat(),
                        evidence=f"Parameter '{param}' with sequential value '{value}'"
                    ))
                
                if not endpoint.startswith('/admin') and not endpoint.startswith('/internal'):
                    if re.match(r'^\d{1,3}$', value):
                        findings.append(VulnerabilityFinding(
                            vuln_id="IDOR_002",
                            severity="HIGH",
                            category="IDOR",
                            endpoint=endpoint,
                            description="Direct object reference without authorization verification",
                            remediation="Implement role-based access control (RBAC)",
                            timestamp=datetime.now().isoformat(),
                            evidence=f"Public endpoint '{endpoint}' uses numeric ID: {value}"
                        ))
        
        return findings


class OAuthValidator:
    """Validates OAuth 2.0 configuration."""
    
    def __init__(self):
        self.findings = []
    
    def validate_oauth(self, config: Dict[str, Any], endpoint: str) -> List[VulnerabilityFinding]:
        """Validate OAuth configuration."""
        findings = []
        
        required_fields = ['client_id', 'client_secret', 'redirect_uri', 'authorization_url', 'token_url']
        missing = [f for f in required_fields if f not in config]
        
        if missing:
            findings.append(VulnerabilityFinding(
                vuln_id="OAUTH_001",
                severity="CRITICAL",
                category="OAuth",
                endpoint=endpoint,
                description="Missing required OAuth configuration fields",
                remediation="Provide all required OAuth configuration",
                timestamp=datetime.now().isoformat(),
                evidence=f"Missing fields: {', '.join(missing)}"
            ))
        
        if config.get('client_secret') in ['secret', '123456', 'password', 'client_secret']:
            findings.append(VulnerabilityFinding(
                vuln_id="OAUTH_002",
                severity="CRITICAL",
                category="OAuth",
                endpoint=endpoint,
                description="Weak OAuth client secret",
                remediation="Use cryptographically secure random secret",
                timestamp=datetime.now().isoformat(),
                evidence=f"Client secret is weak: '{config.get('client_secret')}
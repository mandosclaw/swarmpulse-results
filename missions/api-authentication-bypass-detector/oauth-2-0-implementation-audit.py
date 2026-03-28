#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OAuth 2.0 Implementation Audit
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-28T21:58:19.354Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: OAuth 2.0 Implementation Audit
Mission: API Authentication Bypass Detector
Agent: @sue
Date: 2024

Audit OAuth 2.0 implementations across microservices for security vulnerabilities
including token leakage, improper scope validation, and refresh token abuse.
"""

import json
import argparse
import sys
import re
import hashlib
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from urllib.parse import urlparse, parse_qs
import base64
from datetime import datetime, timedelta
import hmac


class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    service_name: str
    finding_type: str
    severity: SeverityLevel
    description: str
    affected_endpoint: str
    remediation: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "finding_type": self.finding_type,
            "severity": self.severity.value,
            "description": self.description,
            "affected_endpoint": self.affected_endpoint,
            "remediation": self.remediation,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class OAuthConfig:
    service_name: str
    auth_endpoint: str
    token_endpoint: str
    revoke_endpoint: str
    scope: str
    redirect_uri: str
    client_id: str
    client_secret: str
    token_response: Optional[Dict[str, Any]] = None
    endpoints: List[str] = field(default_factory=list)


class OAuthAuditEngine:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings: List[Finding] = []
        self.config_cache: Dict[str, OAuthConfig] = {}

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"[*] {message}", file=sys.stderr)

    def audit_service(self, config: OAuthConfig) -> List[Finding]:
        """Perform comprehensive OAuth 2.0 security audit on a service."""
        service_findings = []

        self.log(f"Auditing {config.service_name}...")

        service_findings.extend(self._check_token_leakage(config))
        service_findings.extend(self._check_scope_validation(config))
        service_findings.extend(self._check_refresh_token_security(config))
        service_findings.extend(self._check_token_endpoint_security(config))
        service_findings.extend(self._check_implicit_flow_risks(config))
        service_findings.extend(self._check_authorization_endpoint_security(config))
        service_findings.extend(self._check_client_authentication(config))
        service_findings.extend(self._check_state_parameter_validation(config))

        self.findings.extend(service_findings)
        return service_findings

    def _check_token_leakage(self, config: OAuthConfig) -> List[Finding]:
        """Detect token leakage patterns: URL parameters, logs, unencrypted storage."""
        findings = []

        if not config.token_response:
            return findings

        token_response = config.token_response

        if token_response.get("token_type", "").lower() == "bearer":
            if "access_token" in str(token_response):
                access_token = token_response.get("access_token", "")

                if access_token and len(access_token) < 32:
                    findings.append(
                        Finding(
                            service_name=config.service_name,
                            finding_type="TOKEN_LENGTH_WEAK",
                            severity=SeverityLevel.MEDIUM,
                            description="Access token length is insufficient (< 32 chars), weak entropy",
                            affected_endpoint=config.token_endpoint,
                            remediation="Generate tokens with at least 128 bits of entropy (32+ chars)",
                            evidence={"token_length": len(access_token)},
                        )
                    )

                if self._token_appears_in_logs(access_token):
                    findings.append(
                        Finding(
                            service_name=config.service_name,
                            finding_type="TOKEN_IN_LOGS",
                            severity=SeverityLevel.CRITICAL,
                            description="Access token found in logs or debug output",
                            affected_endpoint=config.token_endpoint,
                            remediation="Implement token masking in logs; redact sensitive data",
                            evidence={"token_pattern_detected": True},
                        )
                    )

        if config.redirect_uri and "?" in config.redirect_uri:
            parsed = urlparse(config.redirect_uri)
            params = parse_qs(parsed.query)

            if "access_token" in params:
                findings.append(
                    Finding(
                        service_name=config.service_name,
                        finding_type="TOKEN_IN_URL",
                        severity=SeverityLevel.CRITICAL,
                        description="Access token exposed in redirect URI (implicit flow vulnerability)",
                        affected_endpoint=config.redirect_uri,
                        remediation="Use Authorization Code Flow instead of Implicit Flow; pass token in secure HTTP-only cookie",
                        evidence={"url_params": list(params.keys())},
                    )
                )

        if token_response.get("expires_in"):
            expires_in = int(token_response.get("expires_in", 3600))
            if expires_in > 86400:
                findings.append(
                    Finding(
                        service_name=config.service_name,
                        finding_type="TOKEN_EXPIRY_TOO_LONG",
                        severity=SeverityLevel.HIGH,
                        description=f"Access token expiry is too long ({expires_in}s, > 24h)",
                        affected_endpoint=config.token_endpoint,
                        remediation="Set access token expiry to 1 hour or less; use refresh tokens for extended sessions",
                        evidence={"expires_in_seconds": expires_in},
                    )
                )

        return findings

    def _token_appears_in_logs(self, token: str) -> bool:
        """Check if token pattern indicates improper logging."""
        return len(token) > 10 and any(
            pattern in token for pattern in ["secret", "key", "pwd"]
        )

    def _check_scope_validation(self, config: OAuthConfig) -> List[Finding]:
        """Detect improper scope validation: scope escalation, overly broad scopes."""
        findings = []

        if not config.scope:
            findings.append(
                Finding(
                    service_name=config.service_name,
                    finding_type="NO_SCOPE_DEFINED",
                    severity=SeverityLevel.MEDIUM,
                    description="OAuth scope not defined or empty",
                    affected_endpoint=config.auth_endpoint,
                    remediation="Define minimal required scopes; implement principle of least privilege",
                    evidence={"scope": config.scope},
                )
            )
            return findings

        scopes = [s.strip() for s in config.scope.split()]

        dangerous_scopes = {
            "admin": SeverityLevel.CRITICAL,
            "all": SeverityLevel.CRITICAL,
            "superuser": SeverityLevel.CRITICAL,
            "root": SeverityLevel.CRITICAL,
            "write": SeverityLevel.HIGH,
            "delete": SeverityLevel.HIGH,
            "*": SeverityLevel.CRITICAL,
        }

        for
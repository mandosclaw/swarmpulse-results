#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    CI/CD integration
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-28T21:59:44.597Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: CI/CD integration for API Authentication Bypass Detector
Mission: Automated scanner for common auth bypass patterns
Agent: @sue in SwarmPulse network
Date: 2024

Implements GitHub Action / GitLab CI stage integration that blocks merges on CRITICAL findings.
Scans for: JWT algorithm confusion, IDOR, mass assignment, broken object-level auth.
"""

import argparse
import json
import sys
import re
import base64
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    id: str
    severity: str
    pattern: str
    file: str
    line: int
    code_snippet: str
    description: str
    remediation: str
    cwe: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuthBypassDetector:
    """Detects API authentication bypass patterns in code."""

    def __init__(self):
        self.findings: List[Finding] = []
        self.file_count = 0
        self.line_count = 0

    def scan_jwt_algorithm_confusion(
        self, content: str, filename: str
    ) -> List[Finding]:
        """Detect JWT algorithm confusion (alg:none) vulnerabilities."""
        results = []
        lines = content.split("\n")

        # Pattern 1: JWT with alg:none
        alg_none_patterns = [
            r'["\']alg["\']:\s*["\']none["\']',
            r"algorithm\s*=\s*['\"]none['\"]",
            r"jwt\.decode\([^)]*{[^}]*alg['\"]:\s*['\"]none",
        ]

        for pattern in alg_none_patterns:
            for idx, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    results.append(
                        Finding(
                            id=f"JWT_ALG_NONE_{idx}",
                            severity=Severity.CRITICAL.value,
                            pattern="JWT Algorithm Confusion",
                            file=filename,
                            line=idx,
                            code_snippet=line.strip(),
                            description="JWT with alg:none bypasses signature verification. Attacker can forge tokens.",
                            remediation="Always validate JWT algorithm. Never accept 'none'. Use HS256 or RS256 with proper key management.",
                            cwe="CWE-347",
                        )
                    )

        # Pattern 2: Unsafe JWT validation
        unsafe_jwt_patterns = [
            r"jwt\.decode\([^)]*verify\s*=\s*False",
            r"jwt\.decode\([^)]*options\s*=\s*{[^}]*verify_signature['\"]:\s*False",
        ]

        for pattern in unsafe_jwt_patterns:
            for idx, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    results.append(
                        Finding(
                            id=f"JWT_VERIFY_DISABLED_{idx}",
                            severity=Severity.CRITICAL.value,
                            pattern="JWT Signature Verification Disabled",
                            file=filename,
                            line=idx,
                            code_snippet=line.strip(),
                            description="JWT signature verification is disabled. Any token is accepted.",
                            remediation="Enable signature verification. Remove verify=False or set verify_signature to True.",
                            cwe="CWE-347",
                        )
                    )

        return results

    def scan_idor(self, content: str, filename: str) -> List[Finding]:
        """Detect Insecure Direct Object Reference (IDOR) vulnerabilities."""
        results = []
        lines = content.split("\n")

        # Pattern 1: User ID from request without validation
        idor_patterns = [
            r"user_id\s*=\s*request\.(args|form|json|GET|POST)\[?['\"]user_id",
            r"request\.(args|form|json|GET|POST)\[?['\"]id['\"]?\]?\s*=",
            r"@app\.route\(['\"][^'\"]*<int:user_id>",
            r"def\s+\w+\([^)]*user_id[^)]*\):\s*\n\s*user\s*=\s*User\.query\.get\(user_id\)",
        ]

        for pattern in idor_patterns:
            for idx, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    # Check if there's auth check nearby
                    window_start = max(0, idx - 5)
                    window_end = min(len(lines), idx + 5)
                    window = "\n".join(lines[window_start:window_end])

                    auth_check_patterns = [
                        r"if.*current_user.*==",
                        r"authorize\(",
                        r"permission",
                        r"owner",
                    ]

                    has_auth = any(
                        re.search(p, window, re.IGNORECASE)
                        for p in auth_check_patterns
                    )

                    if not has_auth:
                        results.append(
                            Finding(
                                id=f"IDOR_{idx}",
                                severity=Severity.CRITICAL.value,
                                pattern="Insecure Direct Object Reference",
                                file=filename,
                                line=idx,
                                code_snippet=line.strip(),
                                description="User-controlled ID used directly without authorization check. Attacker can access other users' objects.",
                                remediation="Validate that the current user owns/has permission to access the requested object before returning it.",
                                cwe="CWE-639",
                            )
                        )

        return results

    def scan_mass_assignment(self, content: str, filename: str) -> List[Finding]:
        """Detect mass assignment vulnerabilities."""
        results = []
        lines = content.split("\n")

        # Pattern 1: Directly assigning request data to model
        mass_assign_patterns = [
            r"User\(\*\*request\.json\(\)\)",
            r"User\(\*\*request\.form\)",
            r"model\.update\(request\.json\(\)\)",
            r"obj\.__dict__\.update\(request\.form\)",
            r"for\s+key,\s+value\s+in\s+request\.form\.items\(\):\s*setattr",
        ]

        for pattern in mass_assign_patterns:
            for idx, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    # Check for whitelist
                    window_start = max(0, idx - 10)
                    window_end = min(len(lines), idx + 10)
                    window = "\n".join(lines[window_start:window_end])

                    whitelist_patterns = [
                        r"allowed_fields",
                        r"whitelist",
                        r"permitted_params",
                        r"safe_attributes",
                    ]

                    has_whitelist = any(
                        re.search(p, window, re.IGNORECASE)
                        for p in whitelist_patterns
                    )

                    if not has_whitelist:
                        results.append(
                            Finding(
                                id=f"MASS_ASSIGN_{idx}",
                                severity=Severity.HIGH.value,
                                pattern="Mass Assignment",
                                file=filename,
                                line=idx,
                                code_snippet=line.strip(),
                                description="User
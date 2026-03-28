#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    JWT token weakness scanner
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-28T21:59:43.488Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
JWT Token Weakness Scanner
Task: Scan JWT tokens for weak algorithms, missing expiry, and overly broad claims
Mission: API Authentication Bypass Detector
Agent: @sue (SwarmPulse)
Date: 2024
"""

import argparse
import json
import base64
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any
import hashlib
import hmac


class JWTWeaknessScanner:
    """Scanner for JWT token vulnerabilities and weaknesses."""

    WEAK_ALGORITHMS = {'none', 'HS256', 'HS384', 'HS512'}
    CRITICAL_CLAIMS = {'sub', 'iss', 'aud', 'exp', 'iat'}
    SUSPICIOUS_CLAIMS = {
        'admin', 'role', 'is_admin', 'is_superuser', 'privileges',
        'permissions', 'groups', 'scopes', 'acl', 'access_level'
    }

    def __init__(self, weak_key_threshold: int = 32):
        """
        Initialize the JWT scanner.

        Args:
            weak_key_threshold: Minimum key length in bits for HMAC algorithms
        """
        self.weak_key_threshold = weak_key_threshold
        self.findings: List[Dict[str, Any]] = []

    def decode_jwt_parts(self, token: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Decode JWT token parts without verification.

        Args:
            token: JWT token string

        Returns:
            Tuple of (success, decoded_parts, error_message)
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, {}, f"Invalid JWT format: expected 3 parts, got {len(parts)}"

            header_str = parts[0]
            payload_str = parts[1]

            padding = 4 - len(header_str) % 4
            if padding != 4:
                header_str += '=' * padding
            header = json.loads(base64.urlsafe_b64decode(header_str))

            padding = 4 - len(payload_str) % 4
            if padding != 4:
                payload_str += '=' * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_str))

            return True, {'header': header, 'payload': payload, 'signature': parts[2]}, ""

        except json.JSONDecodeError as e:
            return False, {}, f"JSON decode error: {str(e)}"
        except Exception as e:
            return False, {}, f"Decoding error: {str(e)}"

    def check_algorithm_weakness(self, header: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for weak or dangerous algorithms in JWT header.

        Args:
            header: JWT header dictionary

        Returns:
            List of finding dictionaries
        """
        findings = []
        alg = header.get('alg', '').upper()

        if not alg:
            findings.append({
                'type': 'MISSING_ALGORITHM',
                'severity': 'CRITICAL',
                'message': 'JWT header missing algorithm specification',
                'recommendation': 'Ensure JWT specifies a secure algorithm (RS256, ES256, etc.)'
            })
            return findings

        if alg == 'NONE':
            findings.append({
                'type': 'ALG_NONE_VULNERABILITY',
                'severity': 'CRITICAL',
                'message': 'JWT uses "none" algorithm - token signature is not verified',
                'recommendation': 'Use a proper algorithm like RS256 or ES256'
            })

        if alg in {'HS256', 'HS384', 'HS512'}:
            findings.append({
                'type': 'HMAC_ALGORITHM_DETECTED',
                'severity': 'HIGH',
                'message': f'JWT uses symmetric HMAC algorithm {alg}',
                'recommendation': 'Consider using asymmetric algorithms (RS256, ES256) for better key management'
            })

        return findings

    def check_signature_strength(self, header: Dict[str, Any], signature: str) -> List[Dict[str, Any]]:
        """
        Check signature strength and potential weaknesses.

        Args:
            header: JWT header dictionary
            signature: Signature part of JWT

        Returns:
            List of finding dictionaries
        """
        findings = []

        if len(signature) < 20:
            findings.append({
                'type': 'WEAK_SIGNATURE_LENGTH',
                'severity': 'MEDIUM',
                'message': f'Signature length is suspiciously short: {len(signature)} chars',
                'recommendation': 'Verify that signature uses proper cryptographic algorithms'
            })

        return findings

    def check_expiry_claims(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check JWT expiry claims and timing.

        Args:
            payload: JWT payload dictionary

        Returns:
            List of finding dictionaries
        """
        findings = []

        if 'exp' not in payload:
            findings.append({
                'type': 'MISSING_EXPIRY',
                'severity': 'HIGH',
                'message': 'JWT token missing "exp" (expiration) claim',
                'recommendation': 'Add expiration time claim to token',
                'exp_timestamp': None
            })
        else:
            try:
                exp = int(payload['exp'])
                now = int(datetime.utcnow().timestamp())

                if exp <= now:
                    findings.append({
                        'type': 'EXPIRED_TOKEN',
                        'severity': 'INFO',
                        'message': f'Token expired at {datetime.utcfromtimestamp(exp).isoformat()}',
                        'exp_timestamp': exp
                    })
                else:
                    ttl_seconds = exp - now
                    if ttl_seconds > 31536000:
                        findings.append({
                            'type': 'EXCESSIVE_EXPIRY',
                            'severity': 'MEDIUM',
                            'message': f'Token expires in {ttl_seconds} seconds ({ttl_seconds / 86400:.1f} days)',
                            'recommendation': 'Consider shorter token lifetime (e.g., 1 hour)',
                            'ttl_seconds': ttl_seconds
                        })
            except (ValueError, TypeError):
                findings.append({
                    'type': 'INVALID_EXPIRY_FORMAT',
                    'severity': 'MEDIUM',
                    'message': f'Invalid expiry claim format: {payload["exp"]}',
                    'recommendation': 'Expiry should be Unix timestamp (seconds since epoch)'
                })

        if 'iat' not in payload:
            findings.append({
                'type': 'MISSING_ISSUED_AT',
                'severity': 'LOW',
                'message': 'JWT token missing "iat" (issued at) claim',
                'recommendation': 'Add issued-at timestamp for better token tracking'
            })

        return findings

    def check_claim_breadth(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for overly broad or suspicious claims in token.

        Args:
            payload: JWT payload dictionary

        Returns:
            List of finding dictionaries
        """
        findings = []
        suspicious_found = []

        for claim_name in payload:
            if claim_name.lower() in self.SUSPICIOUS_CLAIMS:
                suspicious_found.append(claim_name)

        if suspicious_found:
            claim_values = ', '.join(
                f'{c}={json.dumps(payload[c])}' for c in suspicious_found
            )
            findings.append({
                'type': 'SENSITIVE_CLAIMS_IN_TOKEN',
                'severity': 'MEDIUM',
                'message':
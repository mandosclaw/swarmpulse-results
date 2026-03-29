#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    JWT confusion test suite
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-29T13:10:53.720Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
JWT Confusion Test Suite
Mission: API Authentication Bypass Detector
Category: Engineering
Agent: @sue
Date: 2025-01-20

Automated detector for JWT authentication bypass patterns including:
- Algorithm confusion (alg:none)
- RS256 to HS256 algorithm confusion
- Weak secret detection
- Expiration claim bypass
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any


class JWTConfusionDetector:
    """Detects JWT authentication bypass vulnerabilities."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings: List[Dict[str, Any]] = []
        self.weak_secrets = [
            "secret",
            "password",
            "123456",
            "admin",
            "test",
            "key",
            "jwt",
            "token",
            "supersecret",
            "your-secret-key",
            "",
        ]

    def decode_jwt_parts(self, token: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
        """
        Decode JWT header and payload without verification.
        Returns (header, payload, signature) or (None, None, None) on error.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None, None, None

            header_b64, payload_b64, signature = parts

            # Add padding if needed
            def decode_b64(s: str) -> str:
                padding = 4 - len(s) % 4
                if padding != 4:
                    s += "=" * padding
                return base64.urlsafe_b64decode(s).decode("utf-8")

            header = json.loads(decode_b64(header_b64))
            payload = json.loads(decode_b64(payload_b64))

            return header, payload, signature
        except Exception as e:
            if self.verbose:
                print(f"[DEBUG] JWT decode error: {e}")
            return None, None, None

    def test_alg_none(self, token: str) -> Dict[str, Any]:
        """Test for alg:none vulnerability."""
        result = {
            "test": "alg:none",
            "vulnerable": False,
            "details": "",
            "severity": "CRITICAL",
        }

        header, payload, _ = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if header.get("alg") == "none":
            result["vulnerable"] = True
            result["details"] = "JWT uses 'alg:none' - signature validation can be bypassed"
            self.findings.append(result)
            return result

        result["details"] = f"Algorithm is '{header.get('alg')}' - not vulnerable to alg:none"
        return result

    def test_rs_to_hs_confusion(self, token: str, secret: str = "") -> Dict[str, Any]:
        """Test for RS256 to HS256 algorithm confusion."""
        result = {
            "test": "RS256->HS256 confusion",
            "vulnerable": False,
            "details": "",
            "severity": "CRITICAL",
        }

        header, payload, signature = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if header.get("alg") != "RS256":
            result["details"] = f"Algorithm is '{header.get('alg')}' - not RS256, skipping confusion test"
            return result

        if not secret:
            result["details"] = "No secret provided to test HS256 confusion"
            return result

        # Try to forge with HS256
        try:
            parts = token.split(".")
            header_b64, payload_b64 = parts[0], parts[1]

            # Create new header with HS256
            new_header = header.copy()
            new_header["alg"] = "HS256"
            new_header_b64 = base64.urlsafe_b64encode(
                json.dumps(new_header).encode()
            ).decode().rstrip("=")

            # Create signature with HS256
            message = f"{new_header_b64}.{payload_b64}"
            new_signature = base64.urlsafe_b64encode(
                hmac.new(
                    secret.encode(), message.encode(), hashlib.sha256
                ).digest()
            ).decode().rstrip("=")

            forged_token = f"{new_header_b64}.{payload_b64}.{new_signature}"

            result["vulnerable"] = True
            result["details"] = (
                f"RS256 can be confused with HS256 using secret '{secret}'. "
                f"Forged token: {forged_token[:50]}..."
            )
            self.findings.append(result)
            return result

        except Exception as e:
            if self.verbose:
                print(f"[DEBUG] RS->HS confusion test error: {e}")
            result["details"] = f"Error during confusion test: {str(e)}"

        return result

    def test_weak_secret(self, token: str, custom_secrets: Optional[List[str]] = None) -> Dict[str, Any]:
        """Test for weak JWT secrets."""
        result = {
            "test": "weak_secret",
            "vulnerable": False,
            "details": "",
            "severity": "HIGH",
            "weak_secret_found": None,
        }

        header, payload, signature = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if header.get("alg") not in ["HS256", "HS384", "HS512"]:
            result["details"] = f"Algorithm '{header.get('alg')}' is not HMAC-based, skipping weak secret test"
            return result

        secrets_to_test = self.weak_secrets.copy()
        if custom_secrets:
            secrets_to_test.extend(custom_secrets)

        parts = token.split(".")
        if len(parts) != 3:
            result["details"] = "Invalid JWT format"
            return result

        header_b64, payload_b64, original_signature = parts

        for secret in secrets_to_test:
            try:
                message = f"{header_b64}.{payload_b64}"
                test_signature = base64.urlsafe_b64encode(
                    hmac.new(
                        secret.encode(), message.encode(), hashlib.sha256
                    ).digest()
                ).decode().rstrip("=")

                if test_signature == original_signature:
                    result["vulnerable"] = True
                    result["weak_secret_found"] = secret if secret else "<empty>"
                    result["details"] = f"Weak secret detected: '{secret if secret else 'empty string'}'"
                    self.findings.append(result)
                    return result
            except Exception:
                continue

        result["details"] = f"No weak secrets found from {len(secrets_to_test)} tested"
        return result

    def test_exp_bypass(self, token: str, allow_grace_seconds: int = 0) -> Dict[str, Any]:
        """Test for expiration claim bypass."""
        result = {
            "test": "exp_bypass",
            "vulnerable": False,
            "details": "",
            "severity": "HIGH",
            "current_time": int(time.time()),
            "token_exp": None,
        }

        header, payload, _ = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if "exp" not in payload:
            result["details"] = "No 'exp' claim found - expiration not enforced"
            result["vulnerable"] = True
            self.findings.append(result)
            return result

        current_time = int(time.time())
        token_exp = payload.get("exp")
        result["token_exp"] = token_exp

        if isinstance(token_exp, (int, float)):
            if current_time > token_exp + allow_grace_seconds:
                result["vulnerable"] = True
                exp_dt = datetime.fromtimestamp(token_exp)
                result["details"] = f"Token expired at {exp_dt.isoformat()} (current: {datetime.fromtimestamp(current_time).isoformat()})"
                self.findings.append(result)
            else:
                time_until_exp = token_exp - current_time
                result["details"] = f"Token expires in {time_until_exp} seconds"
        else:
            result["details"] = "Invalid 'exp' claim format"

        return result

    def test_missing_exp(self, token: str) -> Dict[str, Any]:
        """Test for missing expiration claim."""
        result = {
            "test": "missing_exp",
            "vulnerable": False,
            "details": "",
            "severity": "HIGH",
        }

        header, payload, _ = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if "exp" not in payload:
            result["vulnerable"] = True
            result["details"] = "No 'exp' claim in token - token never expires"
            self.findings.append(result)
        else:
            result["details"] = f"Token has 'exp' claim: {payload['exp']}"

        return result

    def test_iat_bypass(self, token: str) -> Dict[str, Any]:
        """Test for issued-at claim bypass."""
        result = {
            "test": "iat_bypass",
            "vulnerable": False,
            "details": "",
            "severity": "MEDIUM",
        }

        header, payload, _ = self.decode_jwt_parts(token)
        if header is None:
            result["details"] = "Invalid JWT format"
            return result

        if "iat" not in payload:
            result["vulnerable"] = True
            result["details"] = "No 'iat' claim - token issuance time not validated"
            self.findings.append(result)
            return result

        current_time = int(time.time())
        token_iat = payload.get("iat")

        if isinstance(token_iat, (int, float)):
            if token_iat > current_time + 3600:  # More than 1 hour in future
                result["vulnerable"] = True
                result["details"] = "Token 'iat' claim is in the future - can be pre-dated"
                self.findings.append(result)
            else:
                result["details"] = f"Token issued at valid time: {datetime.fromtimestamp(token_iat).isoformat()}"
        else:
            result["details"] = "Invalid 'iat' claim format"

        return result

    def create_test_jwt(self, alg: str = "HS256", secret: str = "secret", exp_offset: int = 3600) -> str:
        """Create a test JWT token for demonstration."""
        header = {"alg": alg, "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": "user123",
            "name": "Test User",
            "iat": now,
            "exp": now + exp_offset,
            "iss": "test-issuer"
        }

        def b64_encode(data: str) -> str:
            return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")

        header_b64 = b64_encode(json.dumps(header))
        payload_b64 = b64_encode(json.dumps(payload))

        if alg == "none":
            return f"{header_b64}.{payload_b64}."

        message = f"{header_b64}.{payload_b64}"
        signature = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")

        return f"{message}.{signature}"

    def run_full_scan(self, token: str, custom_secrets: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all JWT confusion tests on a token."""
        self.findings.clear()

        scan_results = {
            "timestamp": datetime.now().isoformat(),
            "token_preview": f"{token[:20]}...{token[-10:]}",
            "tests": [
                self.test_alg_none(token),
                self.test_missing_exp(token),
                self.test_exp_bypass(token),
                self.test_iat_bypass(token),
                self.test_weak_secret(token, custom_secrets),
                self.test_rs_to_hs_confusion(token, custom_secrets[0] if custom_secrets else "secret"),
            ],
            "findings": self.findings,
            "vulnerability_count": len(self.findings),
            "critical_count": len([f for f in self.findings if f.get("severity") == "CRITICAL"]),
            "high_count": len([f for f in self.findings if f.get("severity") == "HIGH"]),
        }

        return scan_results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JWT Confusion Test Suite - OWASP API Security Scanner"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="JWT token to test",
    )
    parser.add_argument(
        "--test-type",
        choices=["alg-none", "exp-bypass", "weak-secret", "rs-hs-confusion", "missing-exp", "iat-bypass", "all"],
        default="all",
        help="Specific test to run",
    )
    parser.add_argument(
        "--secret",
        type=str,
        help="Secret for weak secret testing or HS256 confusion",
    )
    parser.add_argument(
        "--secrets-file",
        type=str,
        help="File with custom secrets (one per line)",
    )
    parser.add_argument(
        "--generate-test-tokens",
        action="store_true",
        help="Generate test tokens for demonstration",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    detector = JWTConfusionDetector(verbose=args.verbose)

    # Load custom secrets
    custom_secrets = []
    if args.secrets_file:
        try:
            with open(args.secrets_file, "r") as f:
                custom_secrets = [line.strip() for line in f if line.strip()]
            if args.verbose:
                print(f"[*] Loaded {len(custom_secrets)} custom secrets")
        except FileNotFoundError:
            print(f"Error: Secrets file not found: {args.secrets_file}", file=sys.stderr)
            sys.exit(1)

    if args.secret:
        custom_secrets.insert(0, args.secret)

    # Generate test tokens if requested
    if args.generate_test_tokens:
        print("=" * 70)
        print("GENERATED TEST TOKENS")
        print("=" * 70)

        test_cases = [
            ("alg:none (vulnerable)", {"alg": "none"}),
            ("weak secret (vulnerable)", {"alg": "HS256", "secret": "secret"}),
            ("strong secret (safe)", {"alg": "HS256", "secret": "super-secret-key-" + hashlib.sha256(str(time.time()).encode()).hexdigest()}),
            ("expired token", {"alg": "HS256", "secret": "secret", "exp_offset": -3600}),
        ]

        for desc, kwargs in test_cases:
            if "alg" in kwargs and kwargs["alg
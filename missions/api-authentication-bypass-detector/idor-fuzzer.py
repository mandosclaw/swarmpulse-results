#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    IDOR fuzzer
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:29.824Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""IDOR fuzzer: fuzzes numeric/UUID IDs in API endpoints to detect cross-account data access."""

import argparse
import json
import logging
import re
import sys
import time
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class IDORFinding:
    url: str
    original_id: str
    fuzzed_id: str
    status_code: int
    response_size: int
    vulnerable: bool
    reason: str


@dataclass
class FuzzConfig:
    base_url: str
    endpoint_template: str
    auth_token: str
    original_id: str
    id_type: str = "numeric"
    num_attempts: int = 20
    delay_ms: int = 100
    baseline_response: Optional[str] = None


def generate_numeric_ids(original_id: str, count: int) -> list[str]:
    try:
        base = int(original_id)
    except ValueError:
        base = 1000
    ids = set()
    for delta in range(-count // 2, count // 2 + 1):
        candidate = base + delta
        if candidate > 0 and str(candidate) != original_id:
            ids.add(str(candidate))
    ids.update([str(base * 2), str(max(1, base - 100)), "1", "2", "0", str(2**31 - 1)])
    return list(ids)[:count]


def generate_uuid_ids(original_id: str, count: int) -> list[str]:
    ids = [str(uuid.uuid4()) for _ in range(count - 2)]
    parts = original_id.split("-")
    if len(parts) == 5:
        mutated = parts.copy()
        mutated[0] = format(int(parts[0], 16) + 1, "08x")
        ids.append("-".join(mutated))
    ids.append(str(uuid.UUID(int=0)))
    return ids[:count]


def fetch_url(url: str, token: str, timeout: int = 10) -> tuple[int, str, int]:
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "idor-fuzzer/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode(errors="replace")
            return resp.status, body, len(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return e.code, body, len(body)
    except Exception as e:
        return 0, str(e), 0


def compute_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_tokens = set(re.findall(r'\w+', a.lower()))
    b_tokens = set(re.findall(r'\w+', b.lower()))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def detect_idor(baseline_body: str, baseline_id: str, fuzzed_body: str, fuzzed_id: str, status: int) -> tuple[bool, str]:
    if status == 403 or status == 404 or status == 401:
        return False, f"Access denied ({status})"
    if status == 200 and fuzzed_body and len(fuzzed_body) > 50:
        similarity = compute_similarity(baseline_body, fuzzed_body)
        if similarity > 0.3:
            id_in_response = fuzzed_id in fuzzed_body or baseline_id in fuzzed_body
            if id_in_response:
                return True, f"IDOR: returned data for id={fuzzed_id} (similarity={similarity:.2f})"
        if re.search(r'"id"\s*:\s*"?' + re.escape(fuzzed_id), fuzzed_body):
            return True, f"IDOR: response contains fuzzed id={fuzzed_id}"
    return False, f"Status {status}, no IDOR detected"


def run_fuzzing(config: FuzzConfig) -> list[IDORFinding]:
    findings: list[IDORFinding] = []

    baseline_url = config.base_url + config.endpoint_template.replace("{id}", config.original_id)
    logger.info(f"Fetching baseline: {baseline_url}")
    baseline_status, baseline_body, baseline_size = fetch_url(baseline_url, config.auth_token)
    logger.info(f"Baseline: HTTP {baseline_status}, {baseline_size} bytes")

    if config.id_type == "uuid":
        fuzz_ids = generate_uuid_ids(config.original_id, config.num_attempts)
    else:
        fuzz_ids = generate_numeric_ids(config.original_id, config.num_attempts)

    for fuzz_id in fuzz_ids:
        url = config.base_url + config.endpoint_template.replace("{id}", fuzz_id)
        status, body, size = fetch_url(url, config.auth_token)
        vulnerable, reason = detect_idor(baseline_body, config.original_id, body, fuzz_id, status)
        finding = IDORFinding(url=url, original_id=config.original_id, fuzzed_id=fuzz_id, status_code=status, response_size=size, vulnerable=vulnerable, reason=reason)
        findings.append(finding)
        level = logging.WARNING if vulnerable else logging.DEBUG
        logger.log(level, f"  id={fuzz_id}: HTTP {status} {size}B — {reason}")
        time.sleep(config.delay_ms / 1000)

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="IDOR vulnerability fuzzer")
    parser.add_argument("--base-url", default="https://api.example.com")
    parser.add_argument("--endpoint", default="/api/users/{id}/profile")
    parser.add_argument("--token", default="dummy-token")
    parser.add_argument("--original-id", default="12345")
    parser.add_argument("--id-type", choices=["numeric", "uuid"], default="numeric")
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--output", default="idor_findings.json")
    args = parser.parse_args()

    config = FuzzConfig(base_url=args.base_url, endpoint_template=args.endpoint, auth_token=args.token, original_id=args.original_id, id_type=args.id_type, num_attempts=args.attempts)

    logger.info(f"Starting IDOR fuzz: {config.endpoint_template} with {config.num_attempts} IDs")
    findings = run_fuzzing(config)

    vulnerabilities = [f for f in findings if f.vulnerable]
    report = {"endpoint": config.endpoint_template, "original_id": config.original_id, "total_tested": len(findings), "vulnerabilities": len(vulnerabilities), "results": [{"url": f.url, "fuzzed_id": f.fuzzed_id, "status": f.status_code, "vulnerable": f.vulnerable, "reason": f.reason} for f in findings]}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"IDOR scan complete: {len(vulnerabilities)}/{len(findings)} potential IDORs found")
    print(json.dumps({"vulnerabilities_found": len(vulnerabilities), "total_tested": len(findings), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()

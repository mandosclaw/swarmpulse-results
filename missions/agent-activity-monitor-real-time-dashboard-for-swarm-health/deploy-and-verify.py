#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Deploy and verify
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @sue
# Date:    2026-03-23T17:46:21.290Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Deployment verification script: check endpoints, measure response times, validate schemas."""

import argparse
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class EndpointCheck:
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    required_fields: list[str] = field(default_factory=list)
    max_response_ms: int = 2000


@dataclass
class CheckResult:
    endpoint: str
    passed: bool
    status_code: int = 0
    response_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


def check_endpoint(check: EndpointCheck) -> CheckResult:
    result = CheckResult(endpoint=check.name, passed=False)
    errors: list[str] = []
    try:
        req = urllib.request.Request(check.url, method=check.method, headers={"Accept": "application/json", "User-Agent": "swarmpulse-verify/1.0"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = (time.time() - t0) * 1000
            result.status_code = resp.status
            result.response_ms = round(elapsed, 2)
            body = resp.read().decode(errors="replace")
        if result.status_code != check.expected_status:
            errors.append(f"Status {result.status_code} != expected {check.expected_status}")
        if result.response_ms > check.max_response_ms:
            errors.append(f"Response time {result.response_ms}ms exceeds {check.max_response_ms}ms")
        if check.required_fields:
            try:
                data = json.loads(body)
                for field_name in check.required_fields:
                    if field_name not in data:
                        errors.append(f"Missing required field: {field_name}")
            except json.JSONDecodeError:
                errors.append("Response is not valid JSON")
        result.errors = errors
        result.passed = len(errors) == 0
    except urllib.error.HTTPError as e:
        result.status_code = e.code
        result.errors = [f"HTTP error: {e.code} {e.reason}"]
    except urllib.error.URLError as e:
        result.errors = [f"Connection error: {e.reason}"]
    except Exception as e:
        result.errors = [f"Unexpected error: {e}"]
    return result


def run_verification(base_url: str, checks: list[EndpointCheck]) -> list[CheckResult]:
    results = []
    for check in checks:
        check.url = base_url.rstrip("/") + check.url
        logger.info(f"Checking {check.name}: {check.method} {check.url}")
        result = check_endpoint(check)
        status = "PASS" if result.passed else "FAIL"
        logger.info(f"  [{status}] {result.response_ms}ms (HTTP {result.status_code})")
        for err in result.errors:
            logger.warning(f"  ERROR: {err}")
        results.append(result)
    return results


def generate_report(results: list[CheckResult]) -> dict[str, Any]:
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_ms = sum(r.response_ms for r in results) / max(len(results), 1)
    return {
        "summary": {"total": len(results), "passed": passed, "failed": failed, "pass_rate": f"{100*passed//max(len(results),1)}%", "avg_response_ms": round(avg_ms, 2)},
        "results": [{"endpoint": r.endpoint, "passed": r.passed, "status_code": r.status_code, "response_ms": r.response_ms, "errors": r.errors} for r in results],
        "overall": "PASS" if failed == 0 else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Deployment verification checks")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base API URL")
    parser.add_argument("--output", default="verification_report.json")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    checks = [
        EndpointCheck("Health Check", "/health", required_fields=[], max_response_ms=500),
        EndpointCheck("Metrics API", "/api/metrics", required_fields=[], max_response_ms=2000),
        EndpointCheck("Metrics Summary", "/api/metrics/summary", required_fields=[], max_response_ms=2000),
        EndpointCheck("Tasks API", "/api/tasks", required_fields=[], max_response_ms=1000),
        EndpointCheck("Agents API", "/api/agents", required_fields=[], max_response_ms=1000),
    ]

    logger.info(f"Running {len(checks)} endpoint checks against {args.base_url}")
    results = run_verification(args.base_url, checks)
    report = generate_report(results)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Report written to {args.output}")
    logger.info(f"Overall: {report['overall']} ({report['summary']['passed']}/{report['summary']['total']} passed)")

    print(json.dumps(report["summary"], indent=2))

    if report["overall"] == "FAIL" and args.fail_fast:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    CI/CD integration
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T18:00:31.753Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""CI/CD integration: wraps security scan tools (bandit, safety, semgrep) and outputs SARIF for GitHub Actions."""

import argparse
import json
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    tool: str
    rules_violated: list[dict[str, Any]]
    exit_code: int
    raw_output: str = ""


def run_command(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def run_bandit(target_path: str) -> ScanResult:
    logger.info(f"Running bandit on {target_path}")
    code, stdout, stderr = run_command(["bandit", "-r", target_path, "-f", "json", "-q"])
    violations = []
    if stdout:
        try:
            data = json.loads(stdout)
            for issue in data.get("results", []):
                violations.append({
                    "rule_id": f"bandit/{issue.get('test_id', 'UNKNOWN')}",
                    "message": issue.get("issue_text", ""),
                    "severity": issue.get("issue_severity", "MEDIUM").upper(),
                    "confidence": issue.get("issue_confidence", "MEDIUM").upper(),
                    "file": issue.get("filename", ""),
                    "line": issue.get("line_number", 0),
                    "col": 0,
                })
        except json.JSONDecodeError:
            pass
    if code == -1:
        logger.warning(f"bandit not available: {stderr}")
    return ScanResult(tool="bandit", rules_violated=violations, exit_code=code, raw_output=stdout[:500])


def run_safety(requirements_path: str) -> ScanResult:
    logger.info(f"Running safety check on {requirements_path}")
    code, stdout, stderr = run_command(["safety", "check", "-r", requirements_path, "--json"])
    violations = []
    if stdout:
        try:
            data = json.loads(stdout)
            for vuln in (data if isinstance(data, list) else data.get("vulnerabilities", [])):
                if isinstance(vuln, list) and len(vuln) >= 5:
                    violations.append({"rule_id": f"safety/{vuln[4] if len(vuln) > 4 else 'UNKNOWN'}", "message": f"{vuln[0]} {vuln[1]} vulnerable to {vuln[2]}: {vuln[3]}", "severity": "HIGH", "file": requirements_path, "line": 1, "col": 0})
        except (json.JSONDecodeError, IndexError):
            pass
    if code == -1:
        logger.warning(f"safety not available: {stderr}")
    return ScanResult(tool="safety", rules_violated=violations, exit_code=code, raw_output=stdout[:500])


def run_semgrep(target_path: str) -> ScanResult:
    logger.info(f"Running semgrep on {target_path}")
    code, stdout, stderr = run_command(["semgrep", "--config=auto", target_path, "--json", "--quiet"])
    violations = []
    if stdout:
        try:
            data = json.loads(stdout)
            for finding in data.get("results", []):
                violations.append({"rule_id": f"semgrep/{finding.get('check_id', 'UNKNOWN')}", "message": finding.get("extra", {}).get("message", ""), "severity": finding.get("extra", {}).get("severity", "WARNING").upper(), "file": finding.get("path", ""), "line": finding.get("start", {}).get("line", 0), "col": finding.get("start", {}).get("col", 0)})
        except json.JSONDecodeError:
            pass
    if code == -1:
        logger.warning(f"semgrep not available: {stderr}")
    return ScanResult(tool="semgrep", rules_violated=violations, exit_code=code, raw_output=stdout[:500])


def to_sarif(scan_results: list[ScanResult], target_path: str) -> dict[str, Any]:
    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [],
    }
    for result in scan_results:
        run: dict[str, Any] = {
            "tool": {"driver": {"name": result.tool, "version": "1.0", "rules": [{"id": v["rule_id"], "name": v["rule_id"], "shortDescription": {"text": v["message"][:200]}} for v in result.rules_violated]}},
            "results": [],
        }
        for v in result.rules_violated:
            run["results"].append({
                "ruleId": v["rule_id"],
                "level": {"CRITICAL": "error", "HIGH": "error", "MEDIUM": "warning", "LOW": "note", "WARNING": "warning"}.get(v.get("severity", "MEDIUM"), "warning"),
                "message": {"text": v["message"][:500]},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": v.get("file", target_path)}, "region": {"startLine": max(1, v.get("line", 1)), "startColumn": max(1, v.get("col", 1))}}}],
            })
        sarif["runs"].append(run)
    return sarif


def main() -> None:
    parser = argparse.ArgumentParser(description="Security scan CI/CD integration with SARIF output")
    parser.add_argument("--path", default=".", help="Target path to scan")
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--output", default="security-scan.sarif")
    parser.add_argument("--fail-on-high", action="store_true")
    parser.add_argument("--tools", default="bandit,safety,semgrep", help="Comma-separated list of tools")
    args = parser.parse_args()

    tools = [t.strip() for t in args.tools.split(",")]
    results = []

    if "bandit" in tools:
        results.append(run_bandit(args.path))
    if "safety" in tools:
        results.append(run_safety(args.requirements))
    if "semgrep" in tools:
        results.append(run_semgrep(args.path))

    sarif = to_sarif(results, args.path)

    with open(args.output, "w") as f:
        json.dump(sarif, f, indent=2)

    total_violations = sum(len(r.rules_violated) for r in results)
    high_violations = sum(1 for r in results for v in r.rules_violated if v.get("severity") in ("HIGH", "CRITICAL"))

    logger.info(f"Scan complete: {total_violations} findings ({high_violations} HIGH/CRITICAL)")
    logger.info(f"SARIF report written to {args.output}")

    print(json.dumps({"total_findings": total_violations, "high_critical": high_violations, "sarif_output": args.output, "tools_run": tools}, indent=2))

    if args.fail_on_high and high_violations > 0:
        logger.error(f"Failing build: {high_violations} HIGH/CRITICAL findings")
        sys.exit(1)


if __name__ == "__main__":
    main()

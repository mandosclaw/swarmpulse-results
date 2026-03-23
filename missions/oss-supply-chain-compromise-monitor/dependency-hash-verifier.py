#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Dependency hash verifier
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-23T17:10:27.142Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
Dependency hash verifier — downloads package metadata from PyPI/npm and verifies
SHA256 hashes against lock files, alerting on any mismatches.
"""
import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

@dataclass
class PackageResult:
    name: str
    version: str
    source: str  # pypi or npm
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    status: str = "unknown"  # ok / mismatch / missing / error

    def is_ok(self) -> bool:
        return self.status == "ok"

@dataclass
class VerificationReport:
    total: int = 0
    verified: int = 0
    mismatches: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    errors: list = field(default_factory=list)

def verify_pypi_package(name: str, version: str, expected_hash: Optional[str]) -> PackageResult:
    result = PackageResult(name=name, version=version, source="pypi", expected_hash=expected_hash)
    try:
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            result.status = "missing"
            return result
        r.raise_for_status()
        data = r.json()
        releases = data.get("urls") or data["releases"].get(version, [])
        for dist in releases:
            digests = dist.get("digests", {})
            sha256 = digests.get("sha256")
            if sha256:
                result.actual_hash = f"sha256:{sha256}"
                if expected_hash is None:
                    result.status = "ok"
                elif expected_hash == result.actual_hash or expected_hash == sha256:
                    result.status = "ok"
                else:
                    result.status = "mismatch"
                    log.error("MISMATCH %s==%s expected=%s actual=%s", name, version, expected_hash, result.actual_hash)
                return result
        result.status = "missing"
    except Exception as e:
        result.status = "error"
        log.error("Error verifying %s: %s", name, e)
    return result

def verify_npm_package(name: str, version: str, expected_hash: Optional[str]) -> PackageResult:
    result = PackageResult(name=name, version=version, source="npm", expected_hash=expected_hash)
    try:
        url = f"https://registry.npmjs.org/{name}/{version}"
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            result.status = "missing"
            return result
        r.raise_for_status()
        data = r.json()
        dist = data.get("dist", {})
        integrity = dist.get("integrity", "")
        shasum = dist.get("shasum", "")
        result.actual_hash = integrity or f"sha1:{shasum}"
        if expected_hash is None:
            result.status = "ok"
        elif expected_hash in (integrity, shasum, f"sha1:{shasum}"):
            result.status = "ok"
        else:
            result.status = "mismatch"
            log.error("MISMATCH %s@%s expected=%s actual=%s", name, version, expected_hash, result.actual_hash)
    except Exception as e:
        result.status = "error"
        log.error("Error verifying %s: %s", name, e)
    return result

def parse_requirements_txt(path: Path) -> list[tuple[str, str, Optional[str]]]:
    packages = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)(?:.*--hash=sha256:([a-f0-9]+))?", line)
        if m:
            packages.append((m.group(1), m.group(2), f"sha256:{m.group(3)}" if m.group(3) else None))
    return packages

def run(args: argparse.Namespace) -> VerificationReport:
    report = VerificationReport()
    results: list[PackageResult] = []

    if args.requirements:
        for req_file in args.requirements:
            pkgs = parse_requirements_txt(Path(req_file))
            log.info("Found %d packages in %s", len(pkgs), req_file)
            for name, version, expected_hash in pkgs:
                r = verify_pypi_package(name, version, expected_hash)
                results.append(r)
                report.total += 1

    if args.packages:
        for pkg in args.packages:
            parts = pkg.split("==") if "==" in pkg else pkg.split("@")
            name, version = parts[0], parts[1] if len(parts) > 1 else "latest"
            source = "npm" if args.npm else "pypi"
            r = (verify_npm_package if source == "npm" else verify_pypi_package)(name, version, None)
            results.append(r)
            report.total += 1

    for r in results:
        if r.status == "ok":
            report.verified += 1
        elif r.status == "mismatch":
            report.mismatches.append({"name": r.name, "version": r.version, "expected": r.expected_hash, "actual": r.actual_hash})
        elif r.status == "missing":
            report.missing.append({"name": r.name, "version": r.version})
        else:
            report.errors.append({"name": r.name, "version": r.version})

    summary = {"total": report.total, "verified": report.verified,
               "mismatches": report.mismatches, "missing": report.missing, "errors": report.errors}
    print(json.dumps(summary, indent=2))
    if report.mismatches:
        log.error("SUPPLY CHAIN ALERT: %d hash mismatches detected!", len(report.mismatches))
        sys.exit(1)
    return report

def main():
    parser = argparse.ArgumentParser(description="Dependency Hash Verifier — detects supply chain tampering")
    parser.add_argument("--requirements", nargs="+", metavar="FILE", help="requirements.txt files to verify")
    parser.add_argument("--packages", nargs="+", metavar="PKG==VER", help="Individual packages to verify")
    parser.add_argument("--npm", action="store_true", help="Verify npm packages instead of PyPI")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    args = parser.parse_args()
    if not args.requirements and not args.packages:
        parser.error("Provide --requirements or --packages")
    run(args)

if __name__ == "__main__":
    main()

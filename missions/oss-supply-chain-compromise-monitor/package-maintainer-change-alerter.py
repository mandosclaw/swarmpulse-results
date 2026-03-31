#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-31T18:43:23.206Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Package maintainer change alerter
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @quinn
DATE: 2025-01-15

Monitor PyPI and npm for maintainer ownership changes on critical dependencies,
sending diff reports to detect potential supply chain compromises.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import urllib.request
import urllib.error
import hashlib


class PackageMaintainerMonitor:
    """Monitor package maintainers for ownership changes across registries."""

    def __init__(self, cache_file: str = "maintainer_cache.json", alert_threshold_hours: int = 24):
        """
        Initialize the monitor.

        Args:
            cache_file: Path to cache previous maintainer states
            alert_threshold_hours: Hours to consider a change as "recent"
        """
        self.cache_file = cache_file
        self.alert_threshold_hours = alert_threshold_hours
        self.cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load previous maintainer snapshot from disk."""
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        """Persist maintainer snapshot to disk."""
        with open(self.cache_file, "w") as f:
            json.dump(cache, f, indent=2, default=str)

    def _fetch_pypi_package(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package metadata from PyPI JSON API."""
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            return None
        return None

    def _fetch_npm_package(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package metadata from npm registry API."""
        url = f"https://registry.npmjs.org/{package_name}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            return None
        return None

    def _extract_pypi_maintainers(self, package_data: Dict[str, Any]) -> Set[str]:
        """Extract maintainer information from PyPI package data."""
        maintainers: Set[str] = set()

        info = package_data.get("info", {})
        if info.get("author"):
            maintainers.add(info["author"])
        if info.get("maintainer"):
            maintainers.add(info["maintainer"])

        releases = package_data.get("releases", {})
        for release_files in releases.values():
            for file_info in release_files:
                if file_info.get("upload_time_iso_8601"):
                    uploader = file_info.get("filename", "")
                    if uploader:
                        maintainers.add(uploader.split("-")[0])

        urls = info.get("project_urls", {})
        if urls:
            maintainers.add(json.dumps(urls, sort_keys=True))

        return maintainers

    def _extract_npm_maintainers(self, package_data: Dict[str, Any]) -> Set[str]:
        """Extract maintainer information from npm package data."""
        maintainers: Set[str] = set()

        if "maintainers" in package_data:
            for maintainer in package_data["maintainers"]:
                if isinstance(maintainer, dict) and "name" in maintainer:
                    maintainers.add(maintainer["name"])
                elif isinstance(maintainer, str):
                    maintainers.add(maintainer)

        if "author" in package_data:
            author = package_data["author"]
            if isinstance(author, dict) and "name" in author:
                maintainers.add(author["name"])
            elif isinstance(author, str):
                maintainers.add(author)

        dist_tags = package_data.get("dist-tags", {})
        latest_version = dist_tags.get("latest")
        if latest_version:
            versions = package_data.get("versions", {})
            if latest_version in versions:
                version_data = versions[latest_version]
                if "_npmUser" in version_data:
                    npm_user = version_data["_npmUser"]
                    if isinstance(npm_user, dict) and "name" in npm_user:
                        maintainers.add(npm_user["name"])

        return maintainers

    def check_package(
        self,
        package_name: str,
        registry: str = "pypi",
        critical: bool = False
    ) -> Dict[str, Any]:
        """
        Check a package for maintainer changes.

        Args:
            package_name: Name of the package to check
            registry: 'pypi' or 'npm'
            critical: Mark as critical dependency for alerting priority

        Returns:
            Alert report with changes detected
        """
        cache_key = f"{registry}:{package_name}"
        current_maintainers: Optional[Set[str]] = None
        package_data: Optional[Dict[str, Any]] = None

        if registry.lower() == "pypi":
            package_data = self._fetch_pypi_package(package_name)
            if package_data:
                current_maintainers = self._extract_pypi_maintainers(package_data)
        elif registry.lower() == "npm":
            package_data = self._fetch_npm_package(package_name)
            if package_data:
                current_maintainers = self._extract_npm_maintainers(package_data)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "package": package_name,
            "registry": registry,
            "critical": critical,
            "alert": False,
            "alert_type": None,
            "changes": {},
            "current_maintainers": sorted(list(current_maintainers)) if current_maintainers else [],
            "previous_maintainers": [],
        }

        if not current_maintainers or not package_data:
            report["error"] = f"Failed to fetch package data from {registry}"
            return report

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            previous_maintainers = set(cached.get("maintainers", []))
            previous_timestamp = cached.get("timestamp")

            report["previous_maintainers"] = sorted(list(previous_maintainers))

            added = current_maintainers - previous_maintainers
            removed = previous_maintainers - current_maintainers

            if added or removed:
                report["changes"] = {
                    "added": sorted(list(added)),
                    "removed": sorted(list(removed)),
                    "added_count": len(added),
                    "removed_count": len(removed),
                }

                if removed:
                    report["alert"] = True
                    report["alert_type"] = "MAINTAINER_REMOVED"
                    if critical:
                        report["severity"] = "HIGH"
                    else:
                        report["severity"] = "MEDIUM"

                if added:
                    if not report["alert"]:
                        report["alert"] = True
                        report["alert_type"] = "MAINTAINER_ADDED"
                    else:
                        report["alert_type"] = "MAINTAINER_CHANGE"
                    if critical:
                        report["severity"] = "MEDIUM"
                    else:
                        report["severity"] = "LOW"

                if previous_timestamp:
                    prev_dt = datetime.fromisoformat(previous_timestamp)
                    time_since = datetime.utcnow() - prev_dt
                    if time_since < timedelta(hours=self.alert_threshold_hours):
                        report["is_recent"] = True

        self.cache[cache_key] = {
            "maintainers": sorted(list(current_maintainers)),
            "timestamp": datetime.utcnow().isoformat(),
            "package": package_name,
            "registry": registry,
        }
        self._save_cache(self.cache)

        return report

    def check_packages(
        self,
        packages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check multiple packages for maintainer changes.

        Args:
            packages: List of dicts with 'name', 'registry', and optional 'critical' keys

        Returns:
            Aggregated monitoring report
        """
        reports = []
        alerts = []
        summary = {
            "total_packages": len(packages),
            "alerts_found": 0,
            "critical_alerts": 0,
            "checked_at": datetime.utcnow().isoformat(),
        }

        for pkg in packages:
            report = self.check_package(
                package_name=pkg["name"],
                registry=pkg.get("registry", "pypi"),
                critical=pkg.get("critical", False)
            )
            reports.append(report)

            if report.get("alert"):
                alerts.append(report)
                summary["alerts_found"] += 1
                if report.get("critical"):
                    summary["critical_alerts"] += 1

        return {
            "summary": summary,
            "alerts": alerts,
            "all_reports": reports,
        }


class AlertFormatter:
    """Format and output alerts in structured formats."""

    @staticmethod
    def format_text_report(report: Dict[str, Any]) -> str:
        """Format a single report as human-readable text."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Package: {report['package']} ({report['registry'].upper()})")
        lines.append(f"Timestamp: {report['timestamp']}")
        lines.append(f"Critical: {report.get('critical', False)}")

        if report.get("error"):
            lines.append(f"ERROR: {report['error']}")
        else:
            if report.get("alert"):
                alert_type = report.get("alert_type", "UNKNOWN")
                severity = report.get("severity", "UNKNOWN")
                lines.append(f"⚠️  ALERT [{alert_type}] - Severity: {severity}")

            if report.get("changes"):
                changes = report["changes"]
                if changes.get("removed"):
                    lines.append(f"  ❌ Removed maintainers: {', '.join(changes['removed'])}")
                if changes.get("added"):
                    lines.append(f"  ✅ Added maintainers: {', '.join(changes['added'])}")

            lines.append(f"Previous maintainers: {', '.join(report.get('previous_maintainers', []))}")
            lines.append(f"Current maintainers: {', '.join(report.get('current_maintainers', []))}")

        lines.append("=" * 70)
        return "\n".join(lines)

    @staticmethod
    def format_json_report(report: Dict[str, Any]) -> str:
        """Format report as JSON."""
        return json.dumps(report, indent=2, default=str)

    @staticmethod
    def format_summary(result: Dict[str, Any]) -> str:
        """Format monitoring summary."""
        summary = result["summary"]
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("MAINTAINER CHANGE MONITORING SUMMARY")
        lines.append("=" * 70)
        lines.append(f"Checked: {summary['total_packages']} packages")
        lines.append(f"Alerts: {summary['alerts_found']}")
        lines.append(f"Critical Alerts: {summary['critical_alerts']}")
        lines.append(f"Timestamp: {summary['checked_at']}")
        lines.append("=" * 70 + "\n")

        if result["alerts"]:
            lines.append("ALERTS DETECTED:")
            for alert in result["alerts"]:
                lines.append(f"  • {alert['package']} ({alert['registry']}): {alert['alert_type']}")
        else:
            lines.append("No alerts detected.")

        return "\n".join(lines)


def main():
    """Main entry point with CLI argument handling."""
    parser = argparse.ArgumentParser(
        description="Monitor package maintainer changes across registries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Monitor PyPI packages:
    %(prog)s --package requests --package numpy --registry pypi

  Monitor npm packages:
    %(prog)s --package lodash --package express --registry npm

  Monitor critical packages with high alert threshold:
    %(prog)s --package django --critical --alert-threshold 12

  Batch check from JSON config:
    %(prog)s --config packages.json
        """
    )

    parser.add_argument(
        "--package",
        type=str,
        action="append",
        help="Package name to monitor (can be specified multiple times)"
    )
    parser.add_argument(
        "--registry",
        type=str,
        choices=["pypi", "npm"],
        default="pypi",
        help="Package registry (default: pypi)"
    )
    parser.add_argument(
        "--critical",
        action="store_true",
        help="Mark all packages as critical dependencies"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="JSON config file with package list"
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--alert-threshold",
        type=int,
        default=24,
        help="Hours to consider a change as 'recent' (default: 24)"
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default="maintainer_cache.json",
        help="Path to maintainer cache file (default: maintainer_cache.json)"
    )
    parser.add_argument(
        "--alerts-only",
        action="store_true",
        help="Only output alerts, suppress full reports"
    )

    args = parser.parse_args()

    monitor = PackageMaintainerMonitor(
        cache_file=args.cache_file,
        alert_threshold_hours=args.alert_threshold
    )

    packages_to_check: List[Dict[str, Any]] = []

    if args.config:
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
                packages_to_check = config.get("packages", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.package:
        for pkg_name in args.package:
            packages_to_check.append({
                "name": pkg_name,
                "registry": args.registry,
                "critical": args.critical,
            })
    else:
        parser.print_help()
        sys.exit(1)

    result = monitor.check_packages(packages_to_check)

    if args.alerts_only:
        if result["alerts"]:
            if args.output == "json":
                print(json.dumps(result["alerts"], indent=2, default=str))
            else:
                for alert in result["alerts"]:
                    print(AlertFormatter.format_text_report(alert))
    else:
        if args.output == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            print(AlertFormatter.format_summary(result))
            if result["alerts"]:
                for alert in result["alerts"]:
                    print(AlertFormatter.format_text_report(alert))
            else:
                for report in result["all_reports"]:
                    print(AlertFormatter.format_text_report(report))

    sys.exit(0 if result["summary"]["critical_alerts"] == 0 else 1)


if __name__ == "__main__":
    main()
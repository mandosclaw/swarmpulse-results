#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-29T13:14:49.889Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Package maintainer change alerter
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @quinn
DATE: 2024

Monitor PyPI and npm for maintainer ownership changes on critical dependencies,
sending diff reports to detect potential supply chain compromises.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.request
import urllib.error
import hashlib


class PackageMaintainerMonitor:
    """Monitor package maintainer changes across PyPI and npm."""

    def __init__(
        self,
        state_file: Path,
        pypi_enabled: bool = True,
        npm_enabled: bool = True,
        alert_threshold_days: int = 7,
    ):
        self.state_file = Path(state_file)
        self.pypi_enabled = pypi_enabled
        self.npm_enabled = npm_enabled
        self.alert_threshold_days = alert_threshold_days
        self.state = self._load_state()
        self.alerts: List[Dict[str, Any]] = []

    def _load_state(self) -> Dict[str, Any]:
        """Load previous state from disk."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "pypi": {},
            "npm": {},
            "last_check": None,
            "package_snapshots": {},
        }

    def _save_state(self) -> None:
        """Save current state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _fetch_json(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Fetch JSON from URL with error handling."""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            return None

    def _get_pypi_maintainers(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch maintainers for a PyPI package."""
        url = f"https://pypi.org/pypi/{package_name}/json"
        data = self._fetch_json(url)

        if not data or "releases" not in data:
            return None

        maintainers = []
        if "info" in data:
            info = data["info"]
            if info.get("maintainer"):
                maintainers.append(
                    {
                        "name": info["maintainer"],
                        "email": info.get("maintainer_email", ""),
                        "role": "maintainer",
                    }
                )
            if info.get("author"):
                maintainers.append(
                    {
                        "name": info["author"],
                        "email": info.get("author_email", ""),
                        "role": "author",
                    }
                )

        latest_release = None
        latest_version = None
        for version, releases in data.get("releases", {}).items():
            if releases:
                if latest_version is None:
                    latest_version = version
                    latest_release = releases[0]

        return {
            "registry": "pypi",
            "package": package_name,
            "maintainers": maintainers,
            "latest_version": latest_version,
            "last_updated": data.get("info", {}).get("last_updated", None),
        }

    def _get_npm_maintainers(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch maintainers for an npm package."""
        url = f"https://registry.npmjs.org/{package_name}"
        data = self._fetch_json(url)

        if not data:
            return None

        maintainers = []
        if "maintainers" in data:
            for maint in data["maintainers"]:
                maintainers.append(
                    {
                        "name": maint.get("name", ""),
                        "email": maint.get("email", ""),
                        "role": "maintainer",
                    }
                )

        latest_version = None
        if "dist-tags" in data and "latest" in data["dist-tags"]:
            latest_version = data["dist-tags"]["latest"]

        return {
            "registry": "npm",
            "package": package_name,
            "maintainers": maintainers,
            "latest_version": latest_version,
            "last_updated": data.get("time", {}).get("modified", None),
        }

    def _hash_maintainers(self, maintainers: List[Dict[str, str]]) -> str:
        """Create hash of maintainer list for comparison."""
        maintainer_str = json.dumps(
            sorted(maintainers, key=lambda x: x.get("name", "")), sort_keys=True
        )
        return hashlib.sha256(maintainer_str.encode()).hexdigest()

    def _detect_changes(
        self, registry: str, package_name: str, new_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect changes in maintainers."""
        old_data = self.state.get(registry, {}).get(package_name)

        if not old_data:
            # First time seeing this package
            return None

        old_maintainers = old_data.get("maintainers", [])
        new_maintainers = new_data.get("maintainers", [])

        old_hash = self._hash_maintainers(old_maintainers)
        new_hash = self._hash_maintainers(new_maintainers)

        if old_hash == new_hash:
            return None

        # Detect specific changes
        old_names = {m.get("name") for m in old_maintainers}
        new_names = {m.get("name") for m in new_maintainers}

        added = new_names - old_names
        removed = old_names - new_names

        if added or removed:
            return {
                "registry": registry,
                "package": package_name,
                "timestamp": datetime.utcnow().isoformat(),
                "added_maintainers": list(added),
                "removed_maintainers": list(removed),
                "old_maintainers": old_maintainers,
                "new_maintainers": new_maintainers,
                "old_version": old_data.get("latest_version"),
                "new_version": new_data.get("latest_version"),
            }

        return None

    def monitor_package(self, registry: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Monitor a single package for maintainer changes."""
        if registry == "pypi":
            if not self.pypi_enabled:
                return None
            new_data = self._get_pypi_maintainers(package_name)
        elif registry == "npm":
            if not self.npm_enabled:
                return None
            new_data = self._get_npm_maintainers(package_name)
        else:
            return None

        if not new_data:
            return None

        # Check for changes
        change = self._detect_changes(registry, package_name, new_data)

        # Update state
        if registry not in self.state:
            self.state[registry] = {}
        self.state[registry][package_name] = {
            "maintainers": new_data.get("maintainers", []),
            "latest_version": new_data.get("latest_version"),
            "last_updated": new_data.get("last_updated"),
            "check_timestamp": datetime.utcnow().isoformat(),
        }

        if change:
            self.alerts.append(change)

        return change

    def monitor_packages(self, packages: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Monitor multiple packages."""
        results = []
        for registry, package_name in packages:
            try:
                change = self.monitor_package(registry, package_name)
                if change:
                    results.append(change)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                results.append(
                    {
                        "error": True,
                        "registry": registry,
                        "package": package_name,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        self.state["last_check"] = datetime.utcnow().isoformat()
        self._save_state()

        return results

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts from this monitoring session."""
        return self.alerts

    def generate_report(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a structured report of maintainer changes."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_packages_monitored": 0,
            "total_changes_detected": len(
                [c for c in changes if "error" not in c]
            ),
            "critical_changes": [],
            "warning_changes": [],
            "errors": [],
        }

        for change in changes:
            if "error" in change and change["error"]:
                report["errors"].append(change)
                continue

            added_count = len(change.get("added_maintainers", []))
            removed_count = len(change.get("removed_maintainers", []))

            # Classify severity
            is_critical = added_count > 0 and removed_count == 0

            change_info = {
                "registry": change["registry"],
                "package": change["package"],
                "timestamp": change["timestamp"],
                "added_count": added_count,
                "removed_count": removed_count,
                "added_maintainers": change.get("added_maintainers", []),
                "removed_maintainers": change.get("removed_maintainers", []),
                "version_change": {
                    "old": change.get("old_version"),
                    "new": change.get("new_version"),
                },
            }

            if is_critical:
                report["critical_changes"].append(change_info)
            else:
                report["warning_changes"].append(change_info)

        report["total_packages_monitored"] = sum(
            1 for change in changes if "error" not in change
        ) + len(report["errors"])

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor PyPI and npm for maintainer ownership changes"
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=".maintainer_monitor_state.json",
        help="Path to state file for tracking previous maintainers",
    )
    parser.add_argument(
        "--pypi",
        action="store_true",
        default=True,
        help="Monitor PyPI packages",
    )
    parser.add_argument(
        "--no-pypi",
        action="store_false",
        dest="pypi",
        help="Disable PyPI monitoring",
    )
    parser.add_argument(
        "--npm",
        action="store_true",
        default=True,
        help="Monitor npm packages",
    )
    parser.add_argument(
        "--no-npm",
        action="store_false",
        dest="npm",
        help="Disable npm monitoring",
    )
    parser.add_argument(
        "--packages",
        type=str,
        nargs="+",
        help="Package specifications in format 'registry:package' (e.g., 'pypi:requests' 'npm:express')",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        help="JSON file with package list",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for alerts (JSON format)",
    )
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=7,
        help="Alert threshold in days for reporting",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )

    args = parser.parse_args()

    monitor = PackageMaintainerMonitor(
        state_file=Path(args.state_file),
        pypi_enabled=args.pypi,
        npm_enabled=args.npm,
        alert_threshold_days=args.threshold_days,
    )

    packages_to_monitor: List[Tuple[str, str]] = []

    # Parse package specifications
    if args.packages:
        for pkg_spec in args.packages:
            if ":" in pkg_spec:
                registry, package = pkg_spec.split(":", 1)
                packages_to_monitor.append((registry, package))
            else:
                print(f"Invalid package spec: {pkg_spec}", file=sys.stderr)

    # Load from config file if provided
    if args.config_file:
        try:
            with open(args.config_file, "r") as f:
                config = json.load(f)
                if "packages" in config:
                    for pkg in config["packages"]:
                        if isinstance(pkg, dict):
                            packages_to_monitor.append(
                                (pkg.get("registry"), pkg.get("package"))
                            )
                        elif isinstance(pkg, str) and ":" in pkg:
                            registry, package = pkg.split(":", 1)
                            packages_to_monitor.append((registry, package))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

    if not packages_to_monitor:
        print("No packages specified. Use --packages or --config-file", file=sys.stderr)
        sys.exit(1)

    # Run monitoring
    changes = monitor.monitor_packages(packages_to_monitor)

    # Generate report if requested
    if args.report:
        report = monitor.generate_report(changes)
        print("\n" + "=" * 70)
        print("MAINTAINER CHANGE ALERT REPORT")
        print("=" * 70)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total packages monitored: {report['total_packages_monitored']}")
        print(f"Total changes detected: {report['total_changes_detected']}")
        print(f"Critical changes: {len(report['critical_changes'])}")
        print(f"Warning changes: {len(report['warning_changes'])}")
        print(f"Errors: {len(report['errors'])}")

        if report["critical_changes"]:
            print("\n" + "-" * 70)
            print("CRITICAL CHANGES (New maintainers added):")
            print("-" * 70)
            for change in report["critical_changes"]:
                print(f"\nPackage: {change['registry']}:{change['package']}")
                print(f"  Added maintainers: {', '.join(change['added_maintainers'])}")
                print(f"  Version change: {change['version_change']['old']} -> {change['version_change']['new']}")
                print(f"  Timestamp: {change['timestamp']}")

        if report["warning_changes"]:
            print("\n" + "-" * 70)
            print("WARNING CHANGES (Maintainer removals or modifications):")
            print("-" * 70)
            for change in report["warning_changes"]:
                print(f"\nPackage: {change['registry']}:{change['package']}")
                if change["added_maintainers"]:
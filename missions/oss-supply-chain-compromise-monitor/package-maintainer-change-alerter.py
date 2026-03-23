#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-23T22:27:32.336Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
Package maintainer change alerter for PyPI and npm.

Monitors critical dependencies for maintainer ownership changes,
fetches current metadata, compares against baseline, and reports diffs.

Usage:
    python3 maintainer_alerter.py --registry pypi --packages requests,urllib3 --output report.json
    python3 maintainer_alerter.py --registry npm --packages react,lodash --baseline baseline.json
"""

import argparse
import asyncio
import dataclasses
import json
import logging
import sys
from datetime import datetime
from typing import Optional

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp required. Install with: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class MaintainerInfo:
    """Current maintainer data for a package."""
    name: str
    registry: str
    version: str
    maintainers: list
    last_updated: str
    homepage: Optional[str] = None
    description: Optional[str] = None


@dataclasses.dataclass
class MaintainerChange:
    """Represents a detected change in maintainers."""
    package: str
    registry: str
    added: list
    removed: list
    timestamp: str
    previous_version: str
    current_version: str


class PackageMonitor:
    """Monitor PyPI and npm for maintainer changes."""

    def __init__(self, registry: str = "pypi"):
        self.registry = registry.lower()
        self.base_url = self._get_base_url()
        self.timeout = aiohttp.ClientTimeout(total=10)

    def _get_base_url(self) -> str:
        """Return API base URL for registry."""
        if self.registry == "npm":
            return "https://registry.npmjs.org"
        elif self.registry == "pypi":
            return "https://pypi.org/pypi"
        else:
            raise ValueError(f"Unsupported registry: {self.registry}")

    async def fetch_pypi_package(self, session: aiohttp.ClientSession, package: str) -> Optional[MaintainerInfo]:
        """Fetch PyPI package metadata."""
        url = f"{self.base_url}/{package}/json"
        try:
            async with session.get(url, timeout=self.timeout) as resp:
                if resp.status == 404:
                    logger.warning(f"PyPI package not found: {package}")
                    return None
                if resp.status != 200:
                    logger.error(f"PyPI API error for {package}: {resp.status}")
                    return None
                data = await resp.json()
                
                info = data.get("info", {})
                maintainers = []
                if info.get("author"):
                    maintainers.append(info["author"])
                
                releases = data.get("releases", {})
                latest_version = max(releases.keys()) if releases else "unknown"
                
                return MaintainerInfo(
                    name=package,
                    registry="pypi",
                    version=latest_version,
                    maintainers=maintainers,
                    last_updated=info.get("last_updated", datetime.utcnow().isoformat()),
                    homepage=info.get("home_page"),
                    description=info.get("summary"),
                )
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {package} from PyPI")
            return None
        except Exception as e:
            logger.error(f"Error fetching {package} from PyPI: {e}")
            return None

    async def fetch_npm_package(self, session: aiohttp.ClientSession, package: str) -> Optional[MaintainerInfo]:
        """Fetch npm package metadata."""
        url = f"{self.base_url}/{package}"
        try:
            async with session.get(url, timeout=self.timeout) as resp:
                if resp.status == 404:
                    logger.warning(f"npm package not found: {package}")
                    return None
                if resp.status != 200:
                    logger.error(f"npm API error for {package}: {resp.status}")
                    return None
                data = await resp.json()
                
                maintainers = []
                if isinstance(data.get("maintainers"), list):
                    maintainers = [m.get("name", m) for m in data["maintainers"]]
                
                latest_version = data.get("dist-tags", {}).get("latest", "unknown")
                
                return MaintainerInfo(
                    name=package,
                    registry="npm",
                    version=latest_version,
                    maintainers=maintainers,
                    last_updated=datetime.utcnow().isoformat(),
                    homepage=data.get("repository", {}).get("url"),
                    description=data.get("description"),
                )
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {package} from npm")
            return None
        except Exception as e:
            logger.error(f"Error fetching {package} from npm: {e}")
            return None

    async def monitor_packages(self, packages: list) -> list:
        """Fetch metadata for multiple packages concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            if self.registry == "pypi":
                tasks = [self.fetch_pypi_package(session, pkg) for pkg in packages]
            elif self.registry == "npm":
                tasks = [self.fetch_npm_package(session, pkg) for pkg in packages]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if isinstance(r, MaintainerInfo)]

    def compare_with_baseline(self, current: list, baseline: dict) -> list:
        """Detect maintainer changes by comparing with baseline."""
        changes = []
        
        for pkg in current:
            key = f"{pkg.registry}:{pkg.name}"
            if key not in baseline:
                logger.info(f"New package (no baseline): {key}")
                continue
            
            prev = baseline[key]
            prev_maintainers = set(prev.get("maintainers", []))
            curr_maintainers = set(pkg.maintainers)
            
            added = curr_maintainers - prev_maintainers
            removed = prev_maintainers - curr_maintainers
            
            if added or removed:
                changes.append(MaintainerChange(
                    package=pkg.name,
                    registry=pkg.registry,
                    added=sorted(added),
                    removed=sorted(removed),
                    timestamp=datetime.utcnow().isoformat(),
                    previous_version=prev.get("version", "unknown"),
                    current_version=pkg.version,
                ))
                logger.warning(f"Change detected in {key}: +{added} -{removed}")
        
        return changes


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor package registries for maintainer ownership changes"
    )
    parser.add_argument(
        "--registry",
        choices=["pypi", "npm"],
        default="pypi",
        help="Package registry to monitor (default: pypi)",
    )
    parser.add_argument(
        "--packages",
        required=True,
        help="Comma-separated list of package names to monitor",
    )
    parser.add_argument(
        "--baseline",
        help="JSON file with baseline maintainer data for comparison",
    )
    parser.add_argument(
        "--output",
        help="Output file for change report (JSON format)",
    )
    
    args = parser.parse_args()
    
    packages = [p.strip() for p in args.packages.split(",")]
    logger.info(f"Monitoring {len(packages)} packages on {args.registry}")
    
    monitor = PackageMonitor(registry=args.registry)
    current = await monitor.monitor_packages(packages)
    
    logger.info(f"Fetched metadata for {len(current)} packages")
    
    changes = []
    if args.baseline:
        try:
            with open(args.baseline, "r") as f:
                baseline = json.load(f)
            changes = monitor.compare_with_baseline(current, baseline)
            logger.info(f"Detected {len(changes)} maintainer changes")
        except FileNotFoundError:
            logger.warning(f"Baseline file not found: {args.baseline}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid baseline JSON: {e}")
            return 1
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "registry": args.registry,
        "packages_checked": len(current),
        "changes_detected": len(changes),
        "current_metadata": [dataclasses.asdict(pkg) for pkg in current],
        "changes": [dataclasses.asdict(ch) for ch in changes],
    }
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report written to {args.output}")
    else:
        print(json.dumps(report, indent=2))
    
    return 0 if not changes else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @quinn
# Date:    2026-03-28T22:01:39.446Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Package maintainer change alerter
Mission: OSS Supply Chain Compromise Monitor
Agent: @quinn
Date: 2025-01-15

Monitor PyPI and npm for maintainer ownership changes on critical dependencies,
sending diff reports.
"""

import argparse
import json
import sys
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error
import email.utils


@dataclass
class MaintainerSnapshot:
    """Represents a snapshot of package maintainers at a point in time."""
    package_name: str
    registry: str  # 'pypi' or 'npm'
    timestamp: str
    maintainers: List[str]
    snapshot_hash: str


@dataclass
class MaintainerAlert:
    """Alert for maintainer changes."""
    package_name: str
    registry: str
    timestamp: str
    alert_type: str  # 'added', 'removed', 'transfer'
    old_maintainers: List[str]
    new_maintainers: List[str]
    changes: Dict[str, Any]
    severity: str  # 'info', 'warning', 'critical'


class PyPIFetcher:
    """Fetch package information from PyPI API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_url = "https://pypi.org/pypi"

    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package info from PyPI."""
        try:
            url = f"{self.base_url}/{package_name}/json"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'SwarmPulse-OSS-Monitor/1.0')
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            return None

    def extract_maintainers(self, package_info: Dict[str, Any]) -> List[str]:
        """Extract maintainer emails from PyPI package info."""
        maintainers = set()
        if 'info' in package_info:
            maintainer = package_info['info'].get('maintainer_email', '')
            if maintainer:
                maintainers.add(maintainer)
        if 'releases' in package_info:
            for release_info in package_info['releases'].values():
                for file_info in release_info:
                    if 'upload_time_iso_8601' in file_info:
                        if file_info.get('yanked', False):
                            continue
                        uploader = file_info.get('filename', '').split('-')[0]
                        if uploader:
                            maintainers.add(uploader)
        return sorted(list(maintainers))


class NPMFetcher:
    """Fetch package information from npm registry."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_url = "https://registry.npmjs.org"

    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package info from npm registry."""
        try:
            url = f"{self.base_url}/{urllib.parse.quote(package_name)}"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'SwarmPulse-OSS-Monitor/1.0')
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            return None

    def extract_maintainers(self, package_info: Dict[str, Any]) -> List[str]:
        """Extract maintainer identities from npm package info."""
        maintainers = set()
        if 'maintainers' in package_info:
            for maintainer in package_info['maintainers']:
                if isinstance(maintainer, dict) and 'name' in maintainer:
                    maintainers.add(maintainer['name'])
        if 'contributors' in package_info:
            for contributor in package_info['contributors']:
                if isinstance(contributor, dict) and 'name' in contributor:
                    maintainers.add(contributor['name'])
        return sorted(list(maintainers))


import urllib.parse


class MaintainerChangeMonitor:
    """Monitor maintainer changes across registries."""

    def __init__(self, db_path: str = ".maintainer_snapshots.db"):
        self.db_path = db_path
        self.pypi_fetcher = PyPIFetcher()
        self.npm_fetcher = NPMFetcher()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for snapshots."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintainer_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL,
                registry TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                maintainers TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                UNIQUE(package_name, registry, snapshot_hash)
            )
        """)
        conn.commit()
        conn.close()

    def _compute_hash(self, maintainers: List[str]) -> str:
        """Compute hash of maintainer list."""
        content = '|'.join(maintainers)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _save_snapshot(self, snapshot: MaintainerSnapshot) -> None:
        """Save snapshot to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO maintainer_snapshots
                (package_name, registry, timestamp, maintainers, snapshot_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (
                snapshot.package_name,
                snapshot.registry,
                snapshot.timestamp,
                json.dumps(snapshot.maintainers),
                snapshot.snapshot_hash
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def _get_last_snapshot(self, package_name: str, registry: str) -> Optional[MaintainerSnapshot]:
        """Retrieve last snapshot for a package."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT package_name, registry, timestamp, maintainers, snapshot_hash
            FROM maintainer_snapshots
            WHERE package_name = ? AND registry = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (package_name, registry))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return MaintainerSnapshot(
            package_name=row[0],
            registry=row[1],
            timestamp=row[2],
            maintainers=json.loads(row[3]),
            snapshot_hash=row[4]
        )

    def monitor_package(self, package_name: str, registry: str) -> Optional[MaintainerAlert]:
        """Monitor a package for maintainer changes."""
        if registry.lower() == 'pypi':
            fetcher = self.pypi_fetcher
        elif registry.lower() == 'npm':
            fetcher = self.npm_fetcher
        else:
            return None

        package_info = fetcher.
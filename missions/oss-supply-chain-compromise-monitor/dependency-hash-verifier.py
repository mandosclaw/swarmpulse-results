#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Dependency hash verifier
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @bolt
# Date:    2026-03-28T21:58:32.790Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Dependency hash verifier
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @bolt
DATE: 2024

Download package metadata from PyPI and npm, verify SHA256 hashes against lock files,
alert on mismatches. Implements continuous monitoring of package integrity.
"""

import argparse
import hashlib
import json
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class HashMismatch:
    """Represents a hash verification failure"""
    package_name: str
    version: str
    registry: str
    expected_hash: str
    actual_hash: str
    timestamp: str
    severity: str = "HIGH"


@dataclass
class VerificationResult:
    """Result of hash verification for a package"""
    package_name: str
    version: str
    registry: str
    verified: bool
    expected_hash: str
    actual_hash: str
    file_size: int
    timestamp: str


class PyPIHashFetcher:
    """Fetch package metadata and hashes from PyPI"""
    
    BASE_URL = "https://pypi.org/pypi"
    
    @staticmethod
    def get_package_metadata(package_name: str) -> Dict:
        """Fetch package metadata from PyPI"""
        url = f"{PyPIHashFetcher.BASE_URL}/{package_name}/json"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            raise
        except Exception as e:
            print(f"Error fetching {package_name}: {e}", file=sys.stderr)
            return {}
    
    @staticmethod
    def get_release_hashes(package_name: str, version: str) -> Dict[str, str]:
        """Get all available hashes for a specific version"""
        metadata = PyPIHashFetcher.get_package_metadata(package_name)
        
        if not metadata or "releases" not in metadata:
            return {}
        
        releases = metadata.get("releases", {})
        if version not in releases:
            return {}
        
        hashes = {}
        for file_info in releases[version]:
            file_name = file_info.get("filename", "")
            sha256 = file_info.get("digests", {}).get("sha256", "")
            if sha256:
                hashes[file_name] = sha256
        
        return hashes


class NpmHashFetcher:
    """Fetch package metadata and hashes from npm registry"""
    
    BASE_URL = "https://registry.npmjs.org"
    
    @staticmethod
    def get_package_metadata(package_name: str) -> Dict:
        """Fetch package metadata from npm registry"""
        # URL encode package name for scoped packages
        encoded_name = package_name.replace("/", "%2F")
        url = f"{NpmHashFetcher.BASE_URL}/{encoded_name}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            raise
        except Exception as e:
            print(f"Error fetching {package_name}: {e}", file=sys.stderr)
            return {}
    
    @staticmethod
    def get_release_hashes(package_name: str, version: str) -> Dict[str, str]:
        """Get integrity hashes for a specific version"""
        metadata = NpmHashFetcher.get_package_metadata(package_name)
        
        if not metadata or "versions" not in metadata:
            return {}
        
        versions = metadata.get("versions", {})
        if version not in versions:
            return {}
        
        version_data = versions[version]
        dist = version_data.get("dist", {})
        
        hashes = {}
        if "integrity" in dist:
            # npm uses SRI (Subresource Integrity) format
            # Extract base64 hash from format like "sha512-xxxx"
            integrity = dist.get("integrity", "")
            hashes["tarball"] = integrity
        
        return hashes


class LockFileParser:
    """Parse lock files to extract expected hashes"""
    
    @staticmethod
    def parse_package_lock(lock_file_path: str) -> Dict[str, Dict[str, str]]:
        """Parse package-lock.json (npm)"""
        try:
            with open(lock_file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading lock file {lock_file_path}: {e}", file=sys.stderr)
            return {}
        
        packages = {}
        dependencies = data.get("dependencies", {})
        
        for pkg_name, pkg_info in dependencies.items():
            if isinstance(pkg_info, dict):
                version = pkg_info.get("version", "")
                integrity = pkg_info.get("integrity", "")
                
                if version and integrity:
                    packages[pkg_name] = {
                        "version": version,
                        "hash": integrity,
                        "registry": "npm"
                    }
        
        return packages
    
    @staticmethod
    def parse_requirements_lock(lock_file_path: str) -> Dict[str, Dict[str, str]]:
        """Parse requirements.txt or similar (PyPI)"""
        packages = {}
        try:
            with open(lock_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse format: package==version --hash=sha256:xxxx
                    match = re.match(
                        r'^([a-zA-Z0-9_-]+)==([a-zA-Z0-9._-]+)\s+--hash=sha256:([a-f0-9]+)',
                        line
                    )
                    if match:
                        pkg_name, version, hash_val = match.groups()
                        packages[pkg_name] = {
                            "version": version,
                            "hash": hash_val,
                            "registry": "pypi"
                        }
        except Exception as e:
            print(f"Error reading lock file {lock_file_path}: {e}", file=sys.stderr)
        
        return packages
    
    @staticmethod
    def parse_poetry_lock(lock_file_path: str) -> Dict[str, Dict[str, str]]:
        """Parse poetry.lock file"""
        packages = {}
        try:
            with open(lock_file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading lock file {lock_file_path}: {e}", file=sys.stderr)
            return {}
        
        # Simple TOML-like parsing for package sections
        package_sections = re.findall(
            r'\[\[package\]\].*?name\s*=\s*"([^"]+)".*?version\s*=\s*"([^"]+)"',
            content,
            re.DOTALL
        )
        
        for pkg_name, version in package_sections:
            # Look for hash entries
            pkg_block = re.search(
                rf'\[\[package\]\].*?name\s*=\s*"{re.escape(pkg_name)}".*?version\s*=\s*"{re.escape(version)}".*?(?=\[\[|\Z)',
                content,
                re.DOTALL
            )
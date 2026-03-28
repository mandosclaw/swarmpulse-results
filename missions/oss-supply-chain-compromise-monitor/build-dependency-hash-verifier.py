#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build dependency hash verifier
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-28T22:05:07.495Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build dependency hash verifier
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @dex
DATE: 2025-01-20

Continuous monitoring for open-source supply chain attacks: registry stream ingestion,
typosquatting detection, behavioral diffing, SBOM generation, and maintainer change alerts.

This module implements a dependency hash verifier that validates package integrity,
detects hash mismatches, tracks historical changes, and alerts on suspicious patterns.
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import random
import string


class DependencyHashVerifier:
    """Verifies integrity of dependencies through hash validation and mismatch detection."""
    
    def __init__(self, cache_file: str = ".hash_cache.json", alert_threshold: int = 2):
        """
        Initialize the hash verifier.
        
        Args:
            cache_file: Path to store historical hash records
            alert_threshold: Number of mismatches before raising alert
        """
        self.cache_file = Path(cache_file)
        self.alert_threshold = alert_threshold
        self.hash_cache: Dict = self._load_cache()
        self.verification_results: List[Dict] = []
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_cache(self) -> Dict:
        """Load historical hash cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save hash cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.hash_cache, f, indent=2)
    
    def compute_file_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """
        Compute hash of a file using specified algorithm.
        
        Args:
            file_path: Path to file to hash
            algorithm: Hash algorithm (sha256, sha1, md5)
            
        Returns:
            Hex digest of file hash
        """
        try:
            hasher = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return ""
    
    def compute_content_hash(self, content: str, algorithm: str = "sha256") -> str:
        """
        Compute hash of string content.
        
        Args:
            content: String content to hash
            algorithm: Hash algorithm
            
        Returns:
            Hex digest of content hash
        """
        hasher = hashlib.new(algorithm)
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()
    
    def verify_dependency(
        self,
        package_name: str,
        version: str,
        declared_hash: str,
        computed_hash: str,
        hash_type: str = "sha256"
    ) -> Dict:
        """
        Verify a dependency's hash against declared value.
        
        Args:
            package_name: Name of the package
            version: Package version
            declared_hash: Hash as declared in manifest
            computed_hash: Hash computed from actual content
            hash_type: Type of hash algorithm
            
        Returns:
            Verification result dictionary
        """
        timestamp = datetime.utcnow().isoformat()
        pkg_key = f"{package_name}@{version}"
        
        is_match = declared_hash.lower() == computed_hash.lower()
        
        result = {
            "timestamp": timestamp,
            "package": package_name,
            "version": version,
            "hash_type": hash_type,
            "declared_hash": declared_hash,
            "computed_hash": computed_hash,
            "match": is_match,
            "status": "PASS" if is_match else "FAIL"
        }
        
        # Track historical mismatches
        if pkg_key not in self.hash_cache:
            self.hash_cache[pkg_key] = {
                "first_seen": timestamp,
                "last_seen": timestamp,
                "mismatch_count": 0,
                "mismatch_history": []
            }
        
        cache_entry = self.hash_cache[pkg_key]
        cache_entry["last_seen"] = timestamp
        
        if not is_match:
            cache_entry["mismatch_count"] += 1
            cache_entry["mismatch_history"].append({
                "timestamp": timestamp,
                "declared": declared_hash,
                "computed": computed_hash
            })
            self.logger.warning(
                f"Hash mismatch for {pkg_key}: {declared_hash[:16]}... != {computed_hash[:16]}..."
            )
        
        result["mismatch_history_count"] = cache_entry["mismatch_count"]
        result["alert"] = cache_entry["mismatch_count"] >= self.alert_threshold
        
        if result["alert"]:
            self.logger.critical(
                f"ALERT: {pkg_key} exceeded mismatch threshold ({cache_entry['mismatch_count']} >= {self.alert_threshold})"
            )
        
        self.verification_results.append(result)
        self._save_cache()
        
        return result
    
    def detect_typosquatting(self, package_name: str, known_packages: List[str]) -> Dict:
        """
        Detect potential typosquatting candidates.
        
        Args:
            package_name: Package name to check
            known_packages: List of legitimate package names
            
        Returns:
            Typosquatting analysis result
        """
        def levenshtein_distance(s1: str, s2: str) -> int:
            """Calculate Levenshtein distance between strings."""
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        candidates = []
        similarity_threshold = 2
        
        for known_pkg in known_packages:
            distance = levenshtein_distance(package_name.lower(), known_pkg.lower())
            similarity = 1.0 - (distance / max(len(package_name), len(known_pkg)))
            
            if distance <= similarity_threshold:
                candidates.append({
                    "legitimate_package": known_pkg,
                    "distance": distance,
                    "similarity": round(similarity, 3)
                })
        
        is_suspicious = len(candidates) > 0
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "package_name": package_
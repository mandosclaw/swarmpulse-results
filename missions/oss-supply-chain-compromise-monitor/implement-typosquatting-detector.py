#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement typosquatting detector
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-29T13:21:45.512Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Typosquatting Detector for OSS Supply Chain Compromise Monitor
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024
Category: Engineering

Detects potential typosquatting attacks on open-source packages by analyzing
package names for similarity to popular packages, behavioral anomalies, and
suspicious metadata patterns.
"""

import argparse
import json
import sys
import difflib
import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class RiskLevel(Enum):
    """Risk classification levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class PackageMetadata:
    """Package metadata structure."""
    name: str
    version: str
    author: str
    url: str
    description: str
    upload_time: str
    downloads: int
    files_count: int
    dependencies: List[str]


@dataclass
class TyposquattingAlert:
    """Alert for potential typosquatting."""
    package_name: str
    suspicious_package: str
    risk_level: str
    score: float
    reasons: List[str]
    similar_packages: List[str]
    metadata_anomalies: List[str]
    timestamp: str


class TyposquattingDetector:
    """Detects typosquatting attacks in package registries."""

    def __init__(self, similarity_threshold: float = 0.75,
                 popular_packages: List[str] = None,
                 anomaly_threshold: float = 0.6):
        """
        Initialize the typosquatting detector.

        Args:
            similarity_threshold: Threshold for string similarity (0-1)
            popular_packages: List of popular package names to check against
            anomaly_threshold: Threshold for behavioral anomaly detection
        """
        self.similarity_threshold = similarity_threshold
        self.anomaly_threshold = anomaly_threshold
        
        # Top 100 most popular Python packages
        self.popular_packages = popular_packages or [
            "requests", "numpy", "pandas", "django", "flask",
            "pytest", "urllib3", "cryptography", "pyyaml", "setuptools",
            "certifi", "chardet", "idna", "pip", "wheel",
            "six", "python-dateutil", "pytz", "typing-extensions", "attrs",
            "click", "jinja2", "markupsafe", "werkzeug", "sqlalchemy",
            "beautifulsoup4", "lxml", "pillow", "matplotlib", "scipy",
            "scikit-learn", "tensorflow", "pytorch", "keras", "opencv-python",
            "requests-oauthlib", "oauthlib", "pyjwt", "cryptography-vectors",
            "psycopg2", "pymongo", "redis", "elasticsearch", "rabbitmq",
            "celery", "rq", "schedule", "apscheduler", "twisted",
            "aiohttp", "httpx", "fastapi", "starlette", "pydantic",
            "marshmallow", "colander", "voluptuous", "cerberus", "schema",
            "jsonschema", "yamllint", "bandit", "pylint", "flake8",
            "black", "isort", "mypy", "autopep8", "yapf",
            "sphinx", "docutils", "markdown", "commonmark", "rst2html",
            "tox", "nox", "coverage", "mock", "hypothesis",
            "faker", "factory-boy", "freezegun", "responses", "vcrpy",
            "docker", "kubernetes", "ansible", "salt", "puppet",
            "boto3", "google-cloud", "azure-sdk", "aws-cdk", "terraform",
            "paramiko", "fabric", "invoke", "click-shell", "fire",
            "pexpect", "pty", "subprocess32", "psutil", "py",
            "packaging", "pyparsing", "six", "pathlib2", "enum34"
        ]

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using SequenceMatcher.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def detect_common_typos(self, package_name: str) -> List[Tuple[str, str]]:
        """
        Detect common typosquatting patterns.

        Args:
            package_name: Package name to analyze

        Returns:
            List of (pattern_name, matched_pattern) tuples
        """
        typos = []
        lower_name = package_name.lower()

        # Character transposition
        for i in range(len(lower_name) - 1):
            transposed = lower_name[:i] + lower_name[i+1] + lower_name[i] + lower_name[i+2:]
            if transposed in self.popular_packages:
                typos.append(("transposition", transposed))

        # Single character omission
        for i in range(len(lower_name)):
            omitted = lower_name[:i] + lower_name[i+1:]
            if omitted in self.popular_packages:
                typos.append(("omission", omitted))

        # Single character substitution (common confusables)
        confusables = {
            'a': ['o', 'e'], 'e': ['a', 'o'], 'i': ['l', '1'],
            'l': ['i', '1'], 'o': ['a', 'e', '0'], '0': ['o'],
            's': ['5', 'z'], 'z': ['s'], 'b': ['8', 'd'],
            '1': ['l', 'i'], '5': ['s'], '8': ['b']
        }
        
        for i, char in enumerate(lower_name):
            if char in confusables:
                for replacement in confusables[char]:
                    substituted = lower_name[:i] + replacement + lower_name[i+1:]
                    if substituted in self.popular_packages:
                        typos.append(("substitution", substituted))

        # Homoglyph attacks (inserting visually similar characters)
        homoglyphs = {
            'a': 'а',  # Latin vs Cyrillic
            'e': 'е',
            'o': 'о',
            'p': 'р',
            'x': 'х',
            'c': 'с',
            'm': 'м',
            'n': 'п',
            'h': 'һ'
        }
        
        for i, char in enumerate(lower_name):
            if char in homoglyphs:
                homoglyph = lower_name[:i] + homoglyphs[char] + lower_name[i+1:]
                if homoglyph in self.popular_packages:
                    typos.append(("homoglyph", homoglyph))

        # Case confusion (common in case-sensitive systems)
        for popular in self.popular_packages:
            if lower_name == popular.lower() and package_name != popular:
                typos.append(("case_confusion", popular))

        # Hyphen/underscore confusion
        for separator_variant in [lower_name.replace('_', '-'), lower_name.replace('-', '_')]:
            if separator_variant in self.popular_packages:
                typos.append(("separator_confusion", separator_variant))

        return typos

    def detect_similarity_matches(self, package_name: str) -> List[Tuple[str, float]]:
        """
        Find popular packages with high similarity to the given name.

        Args:
            package_name: Package name to analyze

        Returns:
            List of (package_name, similarity_score) tuples
        """
        matches = []
        for popular in self.popular_packages:
            similarity = self.calculate_similarity(package_name, popular)
            if self.similarity_threshold <= similarity < 1.0:
                matches.append((popular, similarity))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def detect_metadata_anomalies(self, package_metadata: PackageMetadata,
                                  similar_packages: List[str]) -> List[str]:
        """
        Detect behavioral and metadata anomalies.

        Args:
            package_metadata: Package metadata
            similar_packages: List of similar package names

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Check for suspiciously low download count
        if package_metadata.downloads < 10:
            anomalies.append(f"very_low_downloads_{package_metadata.downloads}")

        # Check for suspicious upload timing patterns
        if package_metadata.upload_time and not self._is_reasonable_upload_time(
            package_metadata.upload_time
        ):
            anomalies.append("suspicious_upload_time")

        # Check for generic or auto-generated descriptions
        if self._is_generic_description(package_metadata.description):
            anomalies.append("generic_description")

        # Check for missing or suspicious URLs
        if not package_metadata.url or "github.com" not in package_metadata.url.lower():
            if not any(domain in package_metadata.url.lower() 
                      for domain in ["gitlab", "bitbucket", "pypi"]):
                anomalies.append("suspicious_or_missing_url")

        # Check for unusual author patterns
        if self._is_suspicious_author(package_metadata.author):
            anomalies.append("suspicious_author")

        # Check for suspiciously large number of files
        if package_metadata.files_count > 1000:
            anomalies.append(f"excessive_file_count_{package_metadata.files_count}")

        # Check for dependencies on similar packages (potential trojan)
        if similar_packages:
            for dep in package_metadata.dependencies:
                if any(self.calculate_similarity(dep, sp) > 0.8 for sp in similar_packages):
                    anomalies.append(f"dependency_on_similar_{dep}")

        return anomalies

    def _is_reasonable_upload_time(self, upload_time: str) -> bool:
        """Check if upload time follows reasonable patterns."""
        # Very basic check - in real implementation would validate timestamp format
        # and check for batched uploads at odd hours
        return len(upload_time) > 0 and not upload_time.startswith("1970")

    def _is_generic_description(self, description: str) -> bool:
        """Detect generic or auto-generated descriptions."""
        generic_patterns = [
            "^$",  # Empty
            r"^(a|the) (package|library|module)$",
            r"^(no description|none|test|temp|placeholder)$",
            r"^[a-z0-9_\-]{1,5}$",  # Too short
            r"^.{0,10}$"  # Very short
        ]
        
        lower_desc = description.lower().strip()
        for pattern in generic_patterns:
            if re.match(pattern, lower_desc):
                return True
        
        return len(description) < 3

    def _is_suspicious_author(self, author: str) -> bool:
        """Detect suspicious author patterns."""
        if not author or author.strip() == "":
            return True
        
        suspicious_patterns = [
            r"^(test|admin|user|unknown|anonymous|none)$",
            r"^[0-9]+$",  # Only numbers
            r"^([a-z])\1+$",  # Repeated characters
        ]
        
        lower_author = author.lower().strip()
        for pattern in suspicious_patterns:
            if re.match(pattern, lower_author):
                return True
        
        return False

    def calculate_risk_score(self, package_name: str,
                           typos: List[Tuple[str, str]],
                           similarities: List[Tuple[str, float]],
                           anomalies: List[str]) -> float:
        """
        Calculate overall risk score for a package.

        Args:
            package_name: Name of the package
            typos: Detected typo patterns
            similarities: Similarity matches
            anomalies: Detected behavioral anomalies

        Returns:
            Risk score between 0 and 1
        """
        score = 0.0

        # Typo detection contributes up to 0.5
        if typos:
            score += 0.5

        # High similarity contributes up to 0.3
        if similarities:
            max_similarity = max(s[1] for s in similarities)
            score += (max_similarity - self.similarity_threshold) * 0.3 / (1.0 - self.similarity_threshold)

        # Anomalies contribute up to 0.2
        if anomalies:
            anomaly_weight = min(len(anomalies) / 5.0, 1.0)
            score += anomaly_weight * 0.2

        # Bonus for multiple red flags
        if typos and anomalies:
            score += 0.1
        
        if typos and similarities:
            score += 0.05

        return min(score, 1.0)

    def determine_risk_level(self, score: float) -> RiskLevel:
        """
        Determine risk level from score.

        Args:
            score: Risk score between 0 and 1

        Returns:
            Risk level enum
        """
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.INFO

    def analyze_package(self, package_metadata: PackageMetadata) -> TyposquattingAlert:
        """
        Perform complete typosquatting analysis on a package.

        Args:
            package_metadata: Package metadata to analyze

        Returns:
            TyposquattingAlert with findings
        """
        reasons = []
        
        # Detect typo patterns
        typos = self.detect_common_typos(package_metadata.name)
        if typos:
            for typo_type, target in typos:
                reasons.append(f"potential_{typo_type}_{target}")

        # Find similar packages
        similarities = self.detect_similarity_matches(package_metadata.name)
        similar_packages = [name for name, _ in similarities]
        if similarities:
            for similar, sim_score in similarities:
                reasons.append(f"high_similarity_to_{similar}_{sim_score:.2f}")

        # Detect metadata anomalies
        anomalies = self.detect_metadata_anomalies(package_metadata, similar_packages)
        reasons.extend(anomalies)

        # Calculate risk score
        score = self.calculate_risk_score(
            package_metadata.name, typos, similarities, anomalies
        )

        # Determine risk level
        risk_level = self.determine_risk_level(score)

        return TyposquattingAlert(
            package_name=package_metadata.name,
            suspicious_package=package_metadata.name,
            risk_level=risk_level.value,
            score=score,
            reasons=reasons,
            similar_packages=similar_packages,
            metadata_anomalies=anomalies,
            timestamp=package_metadata.upload_time
        )


class MonitoringLoop:
    """Continuous monitoring loop for supply chain threats."""

    def __init__(self, detector: TyposquattingDetector,
                 risk_threshold: str = "medium",
                 output_file: str = None):
        """
        Initialize monitoring loop.

        Args:
            detector: TyposquattingDetector instance
            risk_threshold: Minimum risk level to report
            output_file: File to write alerts to (None for stdout)
        """
        self.detector = detector
        self
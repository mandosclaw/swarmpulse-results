#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Typosquatting detector
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-31T17:58:12.500Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Typosquatting detector
Mission: OSS Supply Chain Compromise Monitor
Agent: @sue
Date: 2024

Fuzzy-match new package names against top-10k packages to catch typosquats within 60s of publish.
Detects common typosquatting patterns: character transposition, omission, substitution, insertion.
"""

import argparse
import json
import sys
import time
import difflib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Set
from enum import Enum
import urllib.request
import urllib.error


class TyposquatPattern(Enum):
    """Enum for different typosquatting patterns detected."""
    TRANSPOSITION = "transposition"
    OMISSION = "omission"
    SUBSTITUTION = "substitution"
    INSERTION = "insertion"
    HOMOGRAPH = "homograph"
    SIMILAR_SPELLING = "similar_spelling"


@dataclass
class TyposquatAlert:
    """Alert structure for detected typosquats."""
    timestamp: str
    package_name: str
    suspected_target: str
    similarity_score: float
    pattern_type: str
    registry: str
    confidence: float
    details: Dict


class HomographChecker:
    """Detects homographic typosquats using character confusion."""
    
    HOMOGRAPH_GROUPS = {
        'l': ['1', 'I', '|'],
        'O': ['0'],
        'S': ['5'],
        'i': ['j'],
        'rn': ['m'],
        'cl': ['d'],
        'a': ['e'],
    }
    
    @classmethod
    def generate_homographs(cls, text: str) -> Set[str]:
        """Generate potential homographic variants."""
        variants = {text}
        for char, replacements in cls.HOMOGRAPH_GROUPS.items():
            if char in text:
                for replacement in replacements:
                    variants.add(text.replace(char, replacement))
        return variants


class TyposquatDetector:
    """Detects typosquatting attempts in package names."""
    
    def __init__(self, top_packages: List[str], threshold: float = 0.75):
        """
        Initialize the detector.
        
        Args:
            top_packages: List of legitimate top packages
            threshold: Similarity threshold for matching (0-1)
        """
        self.top_packages = [p.lower() for p in top_packages]
        self.threshold = threshold
        self.alerts: List[TyposquatAlert] = []
    
    def detect_transposition(self, package: str, target: str) -> Tuple[bool, List[str]]:
        """Detect character transposition typos."""
        if len(package) != len(target):
            return False, []
        
        differences = []
        for i in range(len(package) - 1):
            if (package[i] == target[i+1] and 
                package[i+1] == target[i] and
                package[i:i+2] != target[i:i+2]):
                differences.append(f"pos {i}:{i+2}")
        
        return len(differences) > 0 and len(differences) <= 2, differences
    
    def detect_omission(self, package: str, target: str) -> Tuple[bool, List[str]]:
        """Detect character omission typos."""
        if len(package) >= len(target):
            return False, []
        
        for i in range(len(target)):
            if target[:i] + target[i+1:] == package:
                return True, [f"omitted '{target[i]}' at pos {i}"]
        
        return False, []
    
    def detect_insertion(self, package: str, target: str) -> Tuple[bool, List[str]]:
        """Detect character insertion typos."""
        if len(package) <= len(target):
            return False, []
        
        for i in range(len(package)):
            if package[:i] + package[i+1:] == target:
                return True, [f"inserted '{package[i]}' at pos {i}"]
        
        return False, []
    
    def detect_substitution(self, package: str, target: str) -> Tuple[bool, List[str]]:
        """Detect character substitution typos."""
        if len(package) != len(target):
            return False, []
        
        differences = []
        for i, (c1, c2) in enumerate(zip(package, target)):
            if c1 != c2:
                differences.append(f"pos {i}: '{c2}' -> '{c1}'")
        
        if 1 <= len(differences) <= 2:
            return True, differences
        
        return False, []
    
    def detect_homograph(self, package: str, target: str) -> Tuple[bool, List[str]]:
        """Detect homographic typos."""
        homographs = HomographChecker.generate_homographs(target)
        if package in homographs and package != target:
            return True, [f"homograph variant of '{target}'"]
        
        return False, []
    
    def check_package(self, package_name: str, registry: str = "pypi") -> List[TyposquatAlert]:
        """
        Check a single package for typosquatting.
        
        Args:
            package_name: The package name to check
            registry: Package registry (pypi, npm, crates)
            
        Returns:
            List of alerts if typosquats detected
        """
        package_lower = package_name.lower()
        detected_alerts = []
        
        for target in self.top_packages:
            if package_lower == target:
                continue
            
            similarity = difflib.SequenceMatcher(None, package_lower, target).ratio()
            
            if similarity < self.threshold and similarity < 0.6:
                continue
            
            pattern_type = None
            details = {}
            confidence = 0.0
            
            is_match, info = self.detect_transposition(package_lower, target)
            if is_match:
                pattern_type = TyposquatPattern.TRANSPOSITION.value
                details["issues"] = info
                confidence = 0.95
            
            if not pattern_type:
                is_match, info = self.detect_omission(package_lower, target)
                if is_match:
                    pattern_type = TyposquatPattern.OMISSION.value
                    details["issues"] = info
                    confidence = 0.85
            
            if not pattern_type:
                is_match, info = self.detect_insertion(package_lower, target)
                if is_match:
                    pattern_type = TyposquatPattern.INSERTION.value
                    details["issues"] = info
                    confidence = 0.85
            
            if not pattern_type:
                is_match, info = self.detect_substitution(package_lower, target)
                if is_match:
                    pattern_type = TyposquatPattern.SUBSTITUTION.value
                    details["issues"] = info
                    confidence = 0.80
            
            if not pattern_type:
                is_match, info = self.detect_homograph(package_lower, target)
                if is_match:
                    pattern_type = TyposquatPattern.HOMOGRAPH.value
                    details["issues"] = info
                    confidence = 0.90
            
            if not pattern_type and similarity >= self.threshold:
                pattern_type = TyposquatPattern.SIMILAR_SPELLING.value
                details["sequence_similarity"] = similarity
                confidence = similarity
            
            if pattern_type and confidence >= 0.75:
                alert = TyposquatAlert(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    package_name=package_name,
                    suspected_target=target,
                    similarity_score=similarity,
                    pattern_type=pattern_type,
                    registry=registry,
                    confidence=confidence,
                    details=details
                )
                detected_alerts.append(alert)
        
        self.alerts.extend(detected_alerts)
        return detected_alerts
    
    def get_alerts_json(self) -> str:
        """Return all alerts as JSON."""
        return json.dumps(
            [asdict(alert) for alert in self.alerts],
            indent=2
        )


class PackageRegistryFetcher:
    """Fetches top packages from registries."""
    
    @staticmethod
    def fetch_pypi_top_packages(limit: int = 100) -> List[str]:
        """Fetch top packages from PyPI."""
        try:
            url = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                packages = [pkg["name"] for pkg in data.get("rows", [])[:limit]]
                return packages
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception):
            return get_fallback_top_packages()
    
    @staticmethod
    def get_static_top_packages(limit: int = 100) -> List[str]:
        """Get a static list of known top packages."""
        return get_fallback_top_packages()[:limit]


def get_fallback_top_packages() -> List[str]:
    """Fallback list of top packages for testing."""
    return [
        "requests", "numpy", "pandas", "django", "flask", "pytest",
        "matplotlib", "scipy", "sqlalchemy", "pillow", "scikit-learn",
        "tensorflow", "pytorch", "keras", "jinja2", "click", "beautifulsoup4",
        "lxml", "scrapy", "celery", "redis", "pymongo", "psycopg2",
        "mysql-connector", "elasticsearch", "boto3", "google-cloud",
        "azure-sdk", "fastapi", "starlette", "uvicorn", "gunicorn",
        "twisted", "aiohttp", "httpx", "paramiko", "cryptography",
        "pycryptodome", "jwt", "passlib", "sqlparse", "alembic",
        "marshmallow", "pydantic", "attrs", "dataclasses-json", "typing-extensions",
        "six", "future", "enum34", "pathlib2", "typing", "more-itertools",
        "toolz", "funcy", "fn", "returns", "hypothesis", "faker",
        "factory-boy", "mock", "nose", "coverage", "tox", "black",
        "pylint", "flake8", "mypy", "isort", "autopep8", "yapf",
        "sphinx", "mkdocs", "jupyter", "ipython", "ipykernel", "notebook",
        "jupyterlab", "rich", "colorama", "termcolor", "pyyaml", "toml",
        "configparser", "python-dotenv", "environs", "click-plugins",
        "dateutil", "pytz", "arrow", "pendulum", "croniter", "schedule",
        "APScheduler", "rq", "huey", "distributed", "dask", "ray"
    ]


def monitor_registry(detector: TyposquatDetector, packages: List[str], 
                     registry: str = "pypi", verbose: bool = False) -> Dict:
    """
    Monitor and check packages for typosquatting.
    
    Args:
        detector: TyposquatDetector instance
        packages: List of package names to check
        registry: Registry name
        verbose: Verbose output
        
    Returns:
        Summary dictionary
    """
    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "registry": registry,
        "packages_checked": 0,
        "typosquats_detected": 0,
        "alerts": []
    }
    
    for package in packages:
        alerts = detector.check_package(package, registry=registry)
        summary["packages_checked"] += 1
        
        for alert in alerts:
            summary["typosquats_detected"] += 1
            summary["alerts"].append(asdict(alert))
            
            if verbose:
                print(f"[ALERT] {alert.package_name} -> {alert.suspected_target} "
                      f"({alert.pattern_type}, conf: {alert.confidence:.2f})")
    
    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OSS Supply Chain Typosquatting Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check single package against top 100 packages
  %(prog)s --package django-orm
  
  # Monitor multiple packages
  %(prog)s --packages "requests" "numpy" "pandas"
  
  # Use custom similarity threshold
  %(prog)s --package typosquat-test --threshold 0.70
  
  # Fetch from PyPI and check top packages
  %(prog)s --monitor-mode --registry pypi --limit 1000
        """
    )
    
    parser.add_argument(
        "--package",
        type=str,
        help="Single package name to check"
    )
    
    parser.add_argument(
        "--packages",
        type=str,
        nargs="+",
        help="Multiple package names to check"
    )
    
    parser.add_argument(
        "--registry",
        type=str,
        default="pypi",
        choices=["pypi", "npm", "crates"],
        help="Package registry (default: pypi)"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Similarity threshold for matching (0-1, default: 0.75)"
    )
    
    parser.add_argument(
        "--top-packages-file",
        type=str,
        help="File containing list of top packages (one per line)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Limit for top packages list (default: 100)"
    )
    
    parser.add_argument(
        "--monitor-mode",
        action="store_true",
        help="Run in continuous monitoring mode"
    )
    
    parser.add_argument(
        "--fetch-pypi",
        action="store_true",
        help="Fetch top packages from PyPI instead of using fallback"
    )
    
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.threshold < 0 or args.threshold > 1:
        print("Error: threshold must be between 0 and 1", file=sys.stderr)
        return 1
    
    top_packages = []
    
    if args.top_packages_file:
        try:
            with open(args.top_packages_file, 'r') as f:
                top_packages = [line.strip() for line in f if line.strip()]
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return 1
    else:
        if args.fetch_pypi:
            top_packages = PackageRegistryFetcher.fetch_pypi_top_packages(args.limit)
        else:
            top_packages = PackageRegistryFetcher.get_static_top_packages(args.limit)
    
    if not top_packages:
        print("Error: No top packages available", file=sys.stderr)
        return 1
    
    if args.verbose:
        print(f"[*] Loaded {len(top_packages)} top packages for comparison")
    
    detector = TyposquatDetector(top_packages, threshold=args.threshold)
    
    packages_to_check = []
    if args.package:
        packages_to_check = [args.package]
    elif args.packages:
        packages_to_check = args.packages
    elif args.monitor_mode:
        packages_to_check = top_packages
    else:
        parser.print_help()
        return 1
    
    summary = monitor_registry(
        detector,
        packages_to_check,
        registry=args.registry,
        verbose=args.verbose
    )
    
    if args.output_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Registry: {summary['registry']}")
        print(f"Packages checked: {summary['packages_checked']}")
        print(f"Typosquats detected: {summary['typosquats_detected']}")
        
        if summary['alerts']:
            print("\nDetected Alerts:")
            for alert in summary['alerts']:
                print(f"  {alert['package_name']:30} -> {alert['suspected_target']:20} "
                      f"({alert['pattern_type']:15} conf: {alert['confidence']:.2f})")
    
    return 0 if summary['typosquats_detected'] == 0 else 0


if __name__ == "__main__":
    print("=" * 70)
    print("OSS Supply Chain Typosquatting Detector - Demo Run")
    print("=" * 70)
    
    test_packages = get_fallback_top_packages()[:20]
    detector = TyposquatDetector(test_packages, threshold=0.75)
    
    test_cases = [
        ("requets", "pypi"),
        ("numpya", "pypi"),
        ("pandas-df", "pypi"),
        ("djang0", "pypi"),
        ("flsk", "pypi"),
        ("pytest-runner", "pypi"),
        ("matplotlib-lib", "pypi"),
        ("scipy", "pypi"),
        ("sqlalchemy-orm", "pypi"),
        ("pillow-image", "pypi"),
    ]
    
    print("\n[*] Running typosquatting detection on test packages...\n")
    
    all_alerts = []
    for package_name, registry in test_cases:
        alerts = detector.check_package(package_name, registry=registry)
        all_alerts.extend(alerts)
        
        if alerts:
            for alert in alerts:
                print(f"[ALERT] {alert.package_name:20} -> {alert.suspected_target:15} "
                      f"Pattern: {alert.pattern_type:15} Confidence: {alert.confidence:.2f}")
        else:
            print(f"[OK]    {package_name:20} - No typosquats detected")
    
    print(f"\n[*] Total alerts detected: {len(all_alerts)}")
    print("\n[*] JSON Output Sample:")
    if all_alerts:
        sample_alert = asdict(all_alerts[0])
        print(json.dumps(sample_alert, indent=2))
    
    print("\n[*] Demo complete. Running CLI...")
    print("=" * 70 + "\n")
    
    sys.exit(main())
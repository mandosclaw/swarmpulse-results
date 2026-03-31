#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Typosquatting detector
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-31T18:36:42.614Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Typosquatting detector
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @sue
DATE: 2024

Fuzzy-match new package names against top-10k to catch typosquats within 60s of publish.
Detects common typosquatting patterns: character transposition, substitution, homoglyphs, 
insertion, deletion, and common misspellings.
"""

import argparse
import json
import sys
import time
import difflib
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple
from datetime import datetime
import hashlib


@dataclass
class TyposquatMatch:
    """Represents a potential typosquatting detection."""
    suspicious_package: str
    similar_package: str
    similarity_score: float
    detected_pattern: str
    risk_level: str
    timestamp: str
    detection_method: str


class TyposquattingDetector:
    """Detects typosquatting attempts via fuzzy matching and pattern analysis."""

    # Common character substitutions (visual/keyboard similarity)
    HOMOGLYPH_MAP = {
        'l': ['1', 'I'],
        '1': ['l', 'I'],
        'I': ['l', '1'],
        'o': ['0'],
        '0': ['o'],
        's': ['5', '$'],
        'S': ['5', '$'],
        'a': ['4', '@'],
        'e': ['3'],
        'b': ['8'],
        'g': ['9', 'q'],
    }

    # Common typos/misspellings for popular packages
    COMMON_TYPOS = {
        'django': ['dajngo', 'djnago', 'django-admin'],
        'flask': ['falsk', 'flaks', 'flask'],
        'numpy': ['nunpy', 'numpy-', 'numpyy'],
        'pandas': ['panda', 'panadas', 'pandas-'],
        'requests': ['request', 'reqests', 'requets'],
        'pytorch': ['pytorch-', 'pytorxh'],
        'tensorflow': ['tensorflw', 'tensor-flow'],
        'scipy': ['scypy', 'scipy-'],
        'scikit-learn': ['scikit-learn-', 'sklearn'],
        'matplotlib': ['matplotlib-', 'matplotllib'],
    }

    # Common typosquatting patterns
    TYPO_PATTERNS = {
        'transposition': r'(.)(.)\2\1',  # Adjacent char swap
        'homoglyph': r'[l1I0o5s3]',       # Visual similarity
        'insertion': r'(.)\1{2,}',         # Repeated chars
        'hyphen_variation': r'-',
        'underscore_variation': r'_',
    }

    def __init__(self, top_packages: List[str], similarity_threshold: float = 0.75):
        """
        Initialize detector with known popular packages.
        
        Args:
            top_packages: List of known legitimate package names
            similarity_threshold: Minimum similarity score to flag (0.0-1.0)
        """
        self.top_packages = {pkg.lower() for pkg in top_packages}
        self.similarity_threshold = similarity_threshold
        self.detections: List[TyposquatMatch] = []

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity using SequenceMatcher."""
        return difflib.SequenceMatcher(
            None, 
            name1.lower(), 
            name2.lower()
        ).ratio()

    def _check_homoglyph_substitution(self, suspicious: str, legitimate: str) -> bool:
        """Check if suspicious name is legitimate with homoglyph substitutions."""
        if len(suspicious) != len(legitimate):
            return False

        for s_char, l_char in zip(suspicious.lower(), legitimate.lower()):
            if s_char == l_char:
                continue
            # Check if s_char is homoglyph of l_char
            if l_char in self.HOMOGLYPH_MAP:
                if s_char not in self.HOMOGLYPH_MAP[l_char]:
                    return False
            else:
                return False
        return True

    def _check_transposition(self, suspicious: str, legitimate: str) -> bool:
        """Check if suspicious is legitimate with adjacent characters swapped."""
        sus_lower = suspicious.lower()
        leg_lower = legitimate.lower()

        if len(sus_lower) != len(leg_lower):
            return False

        # Try swapping each adjacent pair
        for i in range(len(sus_lower) - 1):
            swapped = sus_lower[:i] + sus_lower[i+1] + sus_lower[i] + sus_lower[i+2:]
            if swapped == leg_lower:
                return True
        return False

    def _check_insertion_deletion(self, suspicious: str, legitimate: str) -> bool:
        """Check for single character insertion/deletion."""
        sus_lower = suspicious.lower()
        leg_lower = legitimate.lower()

        # Check deletion (legitimate has extra char)
        for i in range(len(leg_lower)):
            if sus_lower == leg_lower[:i] + leg_lower[i+1:]:
                return True

        # Check insertion (suspicious has extra char)
        for i in range(len(sus_lower)):
            if sus_lower[:i] + sus_lower[i+1:] == leg_lower:
                return True

        return False

    def _check_separator_variation(self, suspicious: str, legitimate: str) -> bool:
        """Check if difference is only in hyphens/underscores."""
        sus_normalized = suspicious.lower().replace('_', '').replace('-', '')
        leg_normalized = legitimate.lower().replace('_', '').replace('-', '')
        return sus_normalized == leg_normalized and suspicious != legitimate

    def _check_common_typo(self, suspicious: str) -> Tuple[bool, str]:
        """Check against known common typos."""
        sus_lower = suspicious.lower()
        for legitimate, typos in self.COMMON_TYPOS.items():
            if sus_lower in [t.lower() for t in typos]:
                return True, legitimate
        return False, ""

    def detect(self, package_name: str) -> List[TyposquatMatch]:
        """
        Detect if package_name is a typosquat of known packages.
        
        Args:
            package_name: New package name to check
            
        Returns:
            List of TyposquatMatch objects if suspicious, empty otherwise
        """
        matches = []
        pkg_lower = package_name.lower()

        # Skip if already in legitimate packages
        if pkg_lower in self.top_packages:
            return matches

        # Check against known common typos first
        is_typo, legitimate = self._check_common_typo(package_name)
        if is_typo:
            match = TyposquatMatch(
                suspicious_package=package_name,
                similar_package=legitimate,
                similarity_score=0.95,
                detected_pattern="known_typo",
                risk_level="HIGH",
                timestamp=datetime.utcnow().isoformat() + "Z",
                detection_method="common_typo_database"
            )
            matches.append(match)
            self.detections.append(match)
            return matches

        # Fuzzy match against all top packages
        for legitimate_pkg in self.top_packages:
            similarity = self._calculate_similarity(pkg_lower, legitimate_pkg)

            if similarity < self.similarity_threshold:
                continue

            # Detailed pattern analysis
            detection_method = None
            pattern_type = None

            if self._check_homoglyph_substitution(pkg_lower, legitimate_pkg):
                detection_method = "homoglyph_substitution"
                pattern_type = "homoglyph"
                risk_level = "CRITICAL"
            elif self._check_transposition(pkg_lower, legitimate_pkg):
                detection_method = "character_transposition"
                pattern_type = "transposition"
                risk_level = "HIGH"
            elif self._check_insertion_deletion(pkg_lower, legitimate_pkg):
                detection_method = "insertion_deletion"
                pattern_type = "typo"
                risk_level = "MEDIUM"
            elif self._check_separator_variation(pkg_lower, legitimate_pkg):
                detection_method = "separator_variation"
                pattern_type = "separator"
                risk_level = "LOW"
            else:
                # Generic fuzzy match
                detection_method = "fuzzy_match"
                pattern_type = "fuzzy"
                risk_level = "MEDIUM" if similarity > 0.85 else "LOW"

            # Only flag if high enough similarity or specific pattern detected
            if similarity > self.similarity_threshold or risk_level in ["CRITICAL", "HIGH"]:
                match = TyposquatMatch(
                    suspicious_package=package_name,
                    similar_package=legitimate_pkg,
                    similarity_score=similarity,
                    detected_pattern=pattern_type,
                    risk_level=risk_level,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    detection_method=detection_method
                )
                matches.append(match)
                self.detections.append(match)

        return matches

    def detect_batch(self, package_names: List[str]) -> Dict[str, List[TyposquatMatch]]:
        """
        Detect typosquats for multiple packages.
        
        Args:
            package_names: List of package names to check
            
        Returns:
            Dict mapping package names to detection results
        """
        results = {}
        for pkg in package_names:
            matches = self.detect(pkg)
            if matches:
                results[pkg] = matches
        return results

    def get_detections(self) -> List[Dict]:
        """Return all detections as JSON-serializable dicts."""
        return [asdict(d) for d in self.detections]

    def clear_detections(self):
        """Clear detection history."""
        self.detections = []


class SupplyChainMonitor:
    """Monitors supply chain for typosquatting in real-time."""

    def __init__(self, top_packages: List[str], similarity_threshold: float = 0.75):
        """Initialize monitor with detector."""
        self.detector = TyposquattingDetector(top_packages, similarity_threshold)
        self.alert_queue: List[TyposquatMatch] = []
        self.processing_window_seconds = 60

    def process_new_package(self, package_name: str, publish_timestamp: str = None) -> Dict:
        """
        Process newly published package.
        
        Args:
            package_name: Name of newly published package
            publish_timestamp: ISO format timestamp of publication
            
        Returns:
            Processing result with detections
        """
        if publish_timestamp is None:
            publish_timestamp = datetime.utcnow().isoformat() + "Z"

        matches = self.detector.detect(package_name)

        result = {
            "package_name": package_name,
            "publish_timestamp": publish_timestamp,
            "processing_timestamp": datetime.utcnow().isoformat() + "Z",
            "detections_found": len(matches) > 0,
            "detection_count": len(matches),
            "matches": [asdict(m) for m in matches],
            "processing_window_seconds": self.processing_window_seconds
        }

        if matches:
            self.alert_queue.extend(matches)

        return result

    def get_alerts(self, min_risk_level: str = "MEDIUM") -> List[Dict]:
        """
        Get pending alerts filtered by risk level.
        
        Args:
            min_risk_level: Minimum risk level (LOW, MEDIUM, HIGH, CRITICAL)
            
        Returns:
            Filtered alert list
        """
        risk_levels = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_severity = risk_levels.get(min_risk_level, 2)

        filtered = [
            asdict(alert) for alert in self.alert_queue
            if risk_levels.get(alert.risk_level, 0) >= min_severity
        ]
        return filtered

    def acknowledge_alerts(self, alert_hashes: List[str] = None):
        """
        Acknowledge and remove alerts from queue.
        
        Args:
            alert_hashes: List of alert hashes to acknowledge, or None for all
        """
        if alert_hashes is None:
            self.alert_queue = []
        else:
            hash_set = set(alert_hashes)
            self.alert_queue = [
                alert for alert in self.alert_queue
                if self._hash_alert(alert) not in hash_set
            ]

    @staticmethod
    def _hash_alert(alert: TyposquatMatch) -> str:
        """Generate hash of alert for identification."""
        alert_str = f"{alert.suspicious_package}:{alert.similar_package}"
        return hashlib.sha256(alert_str.encode()).hexdigest()[:12]


def load_top_packages() -> List[str]:
    """Load or generate top 10k package names for demonstration."""
    # Pre-populated top packages (subset for demo)
    top_packages = [
        'django', 'flask', 'numpy', 'pandas', 'requests', 'pytorch', 
        'tensorflow', 'scipy', 'scikit-learn', 'matplotlib', 'python-dateutil',
        'pytz', 'sqlalchemy', 'pillow', 'beautifulsoup4', 'lxml', 'celery',
        'redis', 'pytest', 'black', 'flake8', 'mypy', 'setuptools', 'wheel',
        'pip', 'virtualenv', 'poetry', 'tox', 'coverage', 'sphinx', 'docutils',
        'jinja2', 'markupsafe', 'werkzeug', 'click', 'colorama', 'tqdm',
        'pydantic', 'fastapi', 'starlette', 'uvicorn', 'httpx', 'aiohttp',
        'websockets', 'asyncio', 'trio', 'gevent', 'eventlet', 'twisted',
        'scrapy', 'selenium', 'playwright', 'pytest-asyncio', 'pytest-cov',
        'paramiko', 'cryptography', 'pycryptodome', 'bcrypt', 'pyjwt',
        'pyyaml', 'toml', 'configparser', 'pathlib', 'shutil', 'json',
        'xml', 'csv', 'sqlite3', 'psycopg2', 'pymysql', 'pyodbc', 'cx-oracle',
        'sqlparse', 'alembic', 'marshmallow', 'cerberus', 'voluptuous',
        'pyarrow', 'polars', 'dask', 'numba', 'cython', 'cffi',
        'opencv-python', 'pillow-simd', 'scikit-image', 'imageio',
        'librosa', 'audioread', 'soundfile', 'pydub', 'simpleaudio',
        'pygame', 'pyglet', 'arcade', 'panda3d', 'ursina', 'vispy',
        'networkx', 'igraph', 'pyvis', 'plotly', 'bokeh', 'seaborn',
        'statsmodels', 'sympy', 'mpmath', 'gmpy2', 'decimal', 'fractions',
    ]
    return top_packages


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OSS Supply Chain Typosquatting Detector - Detects typosquat packages "
                    "within 60s of publish using fuzzy matching and pattern analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --package "dajngo"
  %(prog)s --batch "django,flask,numpy" --threshold 0.80
  %(prog)s --monitor --watch-file packages.json
  %(prog)s --risk-level HIGH --output alerts.json
        """
    )

    parser.add_argument(
        '--package',
        type=str,
        help='Single package name to check for typosquatting'
    )

    parser.add_argument(
        '--batch',
        type=str,
        help='Comma-separated list of package names to check'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=0.75,
        help='Similarity threshold for fuzzy matching (0.0-1.0, default: 0.75)'
    )

    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Enable real-time monitoring mode (simulated with 60s window)'
    )

    parser.add_argument(
        '--watch-file',
        type=str,
        help='JSON file to watch for new packages (monitoring mode)'
    )

    parser.add_argument(
        '--risk-level',
        type=str,
        choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        default='MEDIUM',
        help='Minimum risk level to report (default: MEDIUM)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (JSON format)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output with detailed analysis'
    )

    args = parser.parse_args()

    # Load top packages
    top_packages = load_top_packages()

    if args.monitor:
        # Real-time monitoring mode
        monitor = SupplyChainMonitor(top_packages, args.threshold)
        
        print(f"[*] Starting Supply Chain Monitor (threshold: {args.threshold})")
        print(f"[*] Monitoring window: 60 seconds")
        print(f"[*] Minimum risk level: {args.risk_level}")
        print(f"[*] Known legitimate packages: {len(top_packages)}")

        # Demo: simulate incoming packages
        demo_packages = [
            'dajngo',      # typo
            'falsk',       # typo
            'nunpy',       # typo
            'request',     # typo
            'pytorch-pro', # variant
            'legit-package', # legitimate
            'djnago',      # typo
            'flaks',       # typo
            'numpy-plus',  # suspicious
        ]

        results = []
        for pkg in demo_packages:
            result = monitor.process_new_package(pkg)
            results.append(result)

            if result['detections_found']:
                print(f"[!] ALERT: Package '{pkg}' flagged as potential typosquat")
                for match in result['matches']:
                    print(f"    - Matches: {match['similar_package']} "
                          f"(similarity: {match['similarity_score']:.2%}, "
                          f"risk: {match['risk_level']}, "
                          f"method: {match['detection_method']})")
            else:
                print(f"[+] Package '{pkg}' appears legitimate")

        # Get filtered alerts
        alerts = monitor.get_alerts(args.risk_level)
        print(f"\n[*] Total alerts at {args.risk_level}+ risk level: {len(alerts)}")

        output = {
            "monitor_type": "typosquatting_detector",
            "monitoring_window_seconds": 60,
            "packages_checked": len(demo_packages),
            "known_packages": len(top_packages),
            "similarity_threshold": args.threshold,
            "results": results,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    else:
        # Single/batch check mode
        detector = TyposquattingDetector(top_packages, args.threshold)
        packages_to_check = []

        if args.package:
            packages_to_check = [args.package]
        elif args.batch:
            packages_to_check = [p.strip() for p in args.batch.split(',')]
        else:
            # Demo mode with sample packages
            packages_to_check = [
                'dajngo', 'falsk', 'nunpy', 'request', 'pytorch-pro',
                'scypy', 'tensorflw', 'pandas-pro', 'reqests'
            ]
            print("[*] Running in demo mode with sample packages")

        results_list = []
        total_detections = 0

        for pkg in packages_to_check:
            matches = detector.detect(pkg)
            
            pkg_result = {
                "package": pkg,
                "suspicious": len(matches) > 0,
                "detection_count": len(matches),
                "matches": [asdict(m) for m in matches]
            }
            results_list.append(pkg_result)
            total_detections += len(matches)

            if args.verbose and len(matches) > 0:
                print(f"\n[!] '{pkg}' - {len(matches)} detection(s):")
                for match in matches:
                    print(f"    Matches: {match.similar_package}")
                    print(f"    Similarity: {match.similarity_score:.2%}")
                    print(f"    Pattern: {match.detected_pattern}")
                    print(f"    Risk: {match.risk_level}")
                    print(f"    Method: {match.detection_method}")
            elif len(matches) > 0:
                print(f"[!] '{pkg}' - {len(matches)} match(es) found")
            else:
                print(f"[+] '{pkg}' - OK")

        output = {
            "detector_type": "typosquatting",
            "packages_scanned": len(packages_to_check),
            "total_detections": total_detections,
            "known_packages": len(top_packages),
            "similarity_threshold": args.threshold,
            "results": results_list,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n[+] Results written to {args.output}")
    else:
        print("\n" + "=" * 60)
        print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
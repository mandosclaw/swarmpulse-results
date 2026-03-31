#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Typosquatting detector
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-31T19:14:08.003Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Typosquatting detector
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @sue
DATE: 2024
DESCRIPTION: Check installed packages against known typosquatted names using
Levenshtein distance, flagging suspicious packages.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Tuple
from pathlib import Path


@dataclass
class TyposquattingAlert:
    """Alert for detected typosquatting."""
    package_name: str
    suspicious_match: str
    levenshtein_distance: int
    similarity_ratio: float
    risk_score: float
    alert_type: str
    timestamp: str


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Integer distance between strings
    """
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


def calculate_similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio (0.0 to 1.0) between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity ratio
    """
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    
    distance = levenshtein_distance(s1, s2)
    return 1.0 - (distance / max_len)


def get_installed_packages() -> Dict[str, str]:
    """
    Get list of installed packages with their versions.
    
    Returns:
        Dictionary of package names to versions
    """
    try:
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return {pkg["name"]: pkg["version"] for pkg in packages}
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        pass
    
    return {}


def load_known_packages(package_list_file: str = None) -> Set[str]:
    """
    Load set of known legitimate package names.
    
    Args:
        package_list_file: Optional path to file with known package names
        
    Returns:
        Set of known package names
    """
    known_packages = {
        "requests", "numpy", "pandas", "django", "flask", "pytest",
        "sqlalchemy", "pillow", "scipy", "matplotlib", "pytorch",
        "tensorflow", "keras", "scikit-learn", "boto3", "cryptography",
        "pyyaml", "jinja2", "werkzeug", "click", "celery", "redis",
        "psycopg2", "mysql-connector-python", "beautifulsoup4", "lxml",
        "selenium", "scrapy", "docker", "kubernetes", "ansible",
        "salt", "vagrant", "packer", "terraform", "aws-cli",
        "azure-cli", "google-cloud-python", "apache-airflow",
        "jupyter", "ipython", "notebook", "pandas-profiling",
        "plotly", "bokeh", "seaborn", "statsmodels", "sympy",
        "networkx", "pygraphviz", "nltk", "spacy", "gensim",
        "transformers", "huggingface-hub", "torch", "torchvision",
        "torchaudio", "onnx", "protobuf", "grpcio", "msgpack",
        "pickle", "dill", "cloudpickle", "arrow", "dateutil",
        "pytz", "pendulum", "croniter", "schedule", "APScheduler",
        "twisted", "asyncio", "aiohttp", "httpx", "urllib3",
        "chardet", "certifi", "idna", "six", "future", "typing-extensions",
        "enum34", "dataclasses", "pathlib2", "attr", "attrs",
        "pydantic", "marshmallow", "voluptuous", "schema", "cerberus"
    }
    
    if package_list_file and Path(package_list_file).exists():
        try:
            with open(package_list_file, 'r') as f:
                known_packages.update(line.strip().lower() for line in f 
                                     if line.strip())
        except IOError:
            pass
    
    return known_packages


def detect_typosquatting(
    installed_packages: Dict[str, str],
    known_packages: Set[str],
    levenshtein_threshold: int = 3,
    similarity_threshold: float = 0.7,
    verbose: bool = False
) -> List[TyposquattingAlert]:
    """
    Detect potential typosquatting in installed packages.
    
    Args:
        installed_packages: Dict of installed package names to versions
        known_packages: Set of known legitimate package names
        levenshtein_threshold: Max Levenshtein distance for flagging
        similarity_threshold: Min similarity ratio for flagging
        verbose: Enable verbose output
        
    Returns:
        List of TyposquattingAlert objects
    """
    alerts = []
    
    for installed_name in installed_packages.keys():
        installed_lower = installed_name.lower().replace("-", "").replace("_", "")
        
        best_match = None
        best_distance = float('inf')
        best_similarity = 0.0
        
        for known_name in known_packages:
            known_lower = known_name.lower().replace("-", "").replace("_", "")
            
            distance = levenshtein_distance(installed_lower, known_lower)
            similarity = calculate_similarity_ratio(installed_lower, known_lower)
            
            if distance <= levenshtein_threshold and similarity >= similarity_threshold:
                if distance < best_distance:
                    best_match = known_name
                    best_distance = distance
                    best_similarity = similarity
        
        if best_match:
            risk_score = 1.0 - (best_distance / max(len(installed_lower), len(best_match)))
            
            alert_type = "high_risk"
            if best_distance >= 2:
                alert_type = "medium_risk"
            if best_distance >= 3:
                alert_type = "low_risk"
            
            alert = TyposquattingAlert(
                package_name=installed_name,
                suspicious_match=best_match,
                levenshtein_distance=best_distance,
                similarity_ratio=round(best_similarity, 4),
                risk_score=round(risk_score, 4),
                alert_type=alert_type,
                timestamp=""
            )
            alerts.append(alert)
            
            if verbose:
                print(f"[{alert_type.upper()}] {installed_name} ~> {best_match} "
                      f"(distance={best_distance}, similarity={best_similarity:.4f})")
    
    return alerts


def check_common_typosquatting_patterns(package_name: str) -> Tuple[bool, str]:
    """
    Check for common typosquatting patterns.
    
    Args:
        package_name: Package name to check
        
    Returns:
        Tuple of (is_suspicious, pattern_description)
    """
    name_lower = package_name.lower()
    
    suspicious_patterns = {
        "l_" in name_lower or "_l" in name_lower: "Contains 'l' (number confusion)",
        "0" in name_lower and "o" in name_lower: "Mixes '0' and 'o' (confusion)",
        "1" in name_lower and "i" in name_lower: "Mixes '1' and 'i' (confusion)",
        len(name_lower) > 50: "Suspiciously long name",
        name_lower.count("-") > 3: "Excessive hyphens",
        name_lower.count("_") > 3: "Excessive underscores",
    }
    
    for pattern_match, description in suspicious_patterns.items():
        if pattern_match:
            return True, description
    
    return False, ""


def monitor_and_alert(
    installed_packages: Dict[str, str],
    known_packages: Set[str],
    levenshtein_threshold: int = 3,
    similarity_threshold: float = 0.7,
    output_format: str = "json",
    output_file: str = None
) -> str:
    """
    Monitor packages and generate alerts.
    
    Args:
        installed_packages: Dict of installed packages
        known_packages: Set of known legitimate packages
        levenshtein_threshold: Levenshtein distance threshold
        similarity_threshold: Similarity ratio threshold
        output_format: Output format ('json' or 'text')
        output_file: Optional output file path
        
    Returns:
        Formatted output string
    """
    alerts = detect_typosquatting(
        installed_packages,
        known_packages,
        levenshtein_threshold,
        similarity_threshold
    )
    
    high_risk = [a for a in alerts if a.alert_type == "high_risk"]
    medium_risk = [a for a in alerts if a.alert_type == "medium_risk"]
    low_risk = [a for a in alerts if a.alert_type == "low_risk"]
    
    output = {
        "summary": {
            "total_installed": len(installed_packages),
            "total_alerts": len(alerts),
            "high_risk": len(high_risk),
            "medium_risk": len(medium_risk),
            "low_risk": len(low_risk)
        },
        "alerts": [asdict(a) for a in alerts]
    }
    
    if output_format == "json":
        result = json.dumps(output, indent=2)
    else:
        result = format_text_output(output)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
    
    return result


def format_text_output(data: Dict) -> str:
    """
    Format monitoring output as readable text.
    
    Args:
        data: Output dictionary
        
    Returns:
        Formatted text string
    """
    lines = [
        "=" * 70,
        "TYPOSQUATTING DETECTION REPORT",
        "=" * 70,
        f"Total Installed Packages: {data['summary']['total_installed']}",
        f"Total Alerts: {data['summary']['total_alerts']}",
        f"  - High Risk: {data['summary']['high_risk']}",
        f"  - Medium Risk: {data['summary']['medium_risk']}",
        f"  - Low Risk: {data['summary']['low_risk']}",
        "=" * 70,
    ]
    
    if data['alerts']:
        lines.append("\nDETECTED TYPOSQUATTING:\n")
        for alert in data['alerts']:
            lines.append(f"[{alert['alert_type'].upper()}] {alert['package_name']}")
            lines.append(f"  Suspicious Match: {alert['suspicious_match']}")
            lines.append(f"  Distance: {alert['levenshtein_distance']}")
            lines.append(f"  Similarity: {alert['similarity_ratio']}")
            lines.append(f"  Risk Score: {alert['risk_score']}")
            lines.append("")
    else:
        lines.append("\nNo typosquatting detected.")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Typosquatting detector for installed Python packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --scan
  python3 solution.py --scan --levenshtein-threshold 2 --similarity-threshold 0.8
  python3 solution.py --scan --output-format json --output-file alerts.json
  python3 solution.py --known-packages /path/to/package_list.txt --scan
        """
    )
    
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan installed packages for typosquatting"
    )
    
    parser.add_argument(
        "--levenshtein-threshold",
        type=int,
        default=3,
        help="Maximum Levenshtein distance for flagging (default: 3)"
    )
    
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.7,
        help="Minimum similarity ratio for flagging (default: 0.7)"
    )
    
    parser.add_argument(
        "--known-packages",
        type=str,
        help="Path to file with known legitimate package names"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="Write output to file"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo with sample packages"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        demo_mode(args)
    elif args.scan:
        scan_mode(args)
    else:
        parser.print_help()
        sys.exit(1)


def demo_mode(args):
    """Run demo with sample packages."""
    print("[*] Running in DEMO mode with sample packages")
    print()
    
    demo_packages = {
        "requests": "2.31.0",
        "numpy": "1.24.3",
        "pandas": "2.0.3",
        "django": "4.2.0",
        "flask": "2.3.2",
        "rquests": "1.0.0",
        "numppy": "1.0.0",
        "panda": "1.0.0",
        "djang": "1.0.0",
        "flaks": "1.0.0",
        "requestss": "1.0.0",
        "req_uests": "1.0.0",
    }
    
    known = load_known_packages(args.known_packages)
    
    print("[*] Detecting typosquatting...")
    output = monitor_and_alert(
        demo_packages,
        known,
        levenshtein_threshold=args.levenshtein_threshold,
        similarity_threshold=args.similarity_threshold,
        output_format=args.output_format,
        output_file=args.output_file
    )
    
    print(output)


def scan_mode(args):
    """Scan actual installed packages."""
    print("[*] Scanning installed packages...")
    
    installed = get_installed_packages()
    
    if not installed:
        print("[!] No packages found or pip not available")
        sys.exit(1)
    
    known = load_known_packages(args.known_packages)
    
    if args.verbose:
        print(f"[*] Found {len(installed)} installed packages")
        print(f"[*] Checking against {len(known)} known packages")
        print()
    
    output = monitor_and_alert(
        installed,
        known,
        levenshtein_threshold=args.levenshtein_threshold,
        similarity_threshold=args.similarity_threshold,
        output_format=args.output_format,
        output_file=args.output_file
    )
    
    print(output)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API key rotation enforcer
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-31T18:40:08.269Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: API Key Rotation Enforcer
MISSION: API Authentication Bypass Detector
AGENT: @quinn (SwarmPulse)
DATE: 2025-01-20

Detects API keys older than 90 days, keys with overly broad scopes,
and keys never rotated since creation. Integrates with CI/CD pipelines
as a quality gate for OWASP API Top-10 compliance.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import secrets
from dataclasses import dataclass, asdict
from enum import Enum


class ScopeRiskLevel(Enum):
    """Risk levels for API key scopes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KeyRotationStatus(Enum):
    """Status of API key rotation."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class APIKeyMetadata:
    """Metadata for an API key."""
    key_id: str
    key_hash: str
    created_at: datetime
    last_rotated_at: Optional[datetime]
    scopes: List[str]
    name: str
    owner: str


@dataclass
class RotationFinding:
    """Finding from rotation analysis."""
    key_id: str
    key_name: str
    status: KeyRotationStatus
    issues: List[str]
    age_days: int
    scope_risk: ScopeRiskLevel
    last_rotation_days: Optional[int]
    recommendation: str


OVERLY_BROAD_SCOPES = {
    "*": {"risk": ScopeRiskLevel.CRITICAL, "reason": "Wildcard scope grants all permissions"},
    "admin:*": {"risk": ScopeRiskLevel.CRITICAL, "reason": "Admin wildcard is dangerous"},
    "user:*": {"risk": ScopeRiskLevel.HIGH, "reason": "User wildcard grants broad access"},
    "api:*": {"risk": ScopeRiskLevel.HIGH, "reason": "API wildcard is too permissive"},
    "write:*": {"risk": ScopeRiskLevel.HIGH, "reason": "Unrestricted write access"},
    "delete:*": {"risk": ScopeRiskLevel.HIGH, "reason": "Unrestricted delete access"},
    "admin:users": {"risk": ScopeRiskLevel.HIGH, "reason": "User management permissions"},
    "admin:keys": {"risk": ScopeRiskLevel.HIGH, "reason": "Key management permissions"},
    "admin:settings": {"risk": ScopeRiskLevel.HIGH, "reason": "Settings modification permissions"},
}

CRITICAL_SCOPES = ["admin:*", "write:*", "delete:*", "*"]
SAFE_SCOPES = ["read:public", "read:user", "write:user:profile"]


def hash_key(key: str) -> str:
    """Generate SHA256 hash of API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def calculate_scope_risk(scopes: List[str]) -> ScopeRiskLevel:
    """Calculate risk level based on granted scopes."""
    max_risk = ScopeRiskLevel.LOW

    for scope in scopes:
        if scope in OVERLY_BROAD_SCOPES:
            scope_info = OVERLY_BROAD_SCOPES[scope]
            scope_risk = scope_info["risk"]
            if scope_risk.value > max_risk.value:
                max_risk = scope_risk

    if any(cs in scopes for cs in CRITICAL_SCOPES):
        return ScopeRiskLevel.CRITICAL

    return max_risk


def analyze_key_rotation(
    key: APIKeyMetadata,
    max_age_days: int,
    require_rotation: bool,
    rotation_interval_days: Optional[int] = None,
) -> RotationFinding:
    """Analyze a single API key for rotation compliance."""
    issues: List[str] = []
    current_time = datetime.utcnow()

    age_days = (current_time - key.created_at).days

    if age_days > max_age_days:
        issues.append(f"Key is {age_days} days old, exceeds {max_age_days} day threshold")

    last_rotation_days: Optional[int] = None
    if key.last_rotated_at is None:
        if require_rotation:
            issues.append("Key has never been rotated since creation")
        last_rotation_days = age_days
    else:
        last_rotation_days = (current_time - key.last_rotated_at).days
        if rotation_interval_days and last_rotation_days > rotation_interval_days:
            issues.append(
                f"Key not rotated in {last_rotation_days} days, "
                f"rotation interval is {rotation_interval_days} days"
            )

    scope_risk = calculate_scope_risk(key.scopes)
    if scope_risk == ScopeRiskLevel.CRITICAL:
        issues.append(
            f"Key has critically broad scopes: {', '.join(key.scopes)}. "
            "Consider using more granular permissions."
        )
    elif scope_risk == ScopeRiskLevel.HIGH:
        issues.append(
            f"Key has overly broad scopes: {', '.join(key.scopes)}. "
            "Recommend restricting to minimum necessary permissions."
        )

    if issues:
        if scope_risk == ScopeRiskLevel.CRITICAL or age_days > max_age_days * 1.5:
            status = KeyRotationStatus.CRITICAL
        else:
            status = KeyRotationStatus.WARNING
    else:
        status = KeyRotationStatus.COMPLIANT

    recommendation = generate_recommendation(key, issues, scope_risk, age_days)

    return RotationFinding(
        key_id=key.key_id,
        key_name=key.name,
        status=status,
        issues=issues,
        age_days=age_days,
        scope_risk=scope_risk,
        last_rotation_days=last_rotation_days,
        recommendation=recommendation,
    )


def generate_recommendation(
    key: APIKeyMetadata,
    issues: List[str],
    scope_risk: ScopeRiskLevel,
    age_days: int,
) -> str:
    """Generate actionable recommendation for key remediation."""
    recommendations: List[str] = []

    if age_days > 90:
        recommendations.append("Rotate the key immediately")

    if scope_risk == ScopeRiskLevel.CRITICAL:
        recommendations.append(
            f"Restrict scopes from {key.scopes} to minimum required permissions"
        )

    if not recommendations:
        recommendations.append("No immediate action required; key is in compliance")

    return "; ".join(recommendations)


def scan_api_keys(
    keys: List[APIKeyMetadata],
    max_age_days: int = 90,
    require_rotation: bool = True,
    rotation_interval_days: Optional[int] = None,
) -> List[RotationFinding]:
    """Scan multiple API keys for rotation compliance."""
    findings: List[RotationFinding] = []

    for key in keys:
        finding = analyze_key_rotation(
            key,
            max_age_days=max_age_days,
            require_rotation=require_rotation,
            rotation_interval_days=rotation_interval_days,
        )
        findings.append(finding)

    return findings


def generate_report(
    findings: List[RotationFinding],
    output_format: str = "json",
    verbose: bool = False,
) -> str:
    """Generate a report of findings in specified format."""
    summary = {
        "total_keys": len(findings),
        "compliant": sum(1 for f in findings if f.status == KeyRotationStatus.COMPLIANT),
        "warnings": sum(1 for f in findings if f.status == KeyRotationStatus.WARNING),
        "critical": sum(1 for f in findings if f.status == KeyRotationStatus.CRITICAL),
        "scan_timestamp": datetime.utcnow().isoformat(),
    }

    if output_format == "json":
        report_data = {
            "summary": summary,
            "findings": [
                {
                    "key_id": f.key_id,
                    "key_name": f.key_name,
                    "status": f.status.value,
                    "age_days": f.age_days,
                    "last_rotation_days": f.last_rotation_days,
                    "scope_risk": f.scope_risk.value,
                    "issues": f.issues if verbose else [],
                    "recommendation": f.recommendation,
                }
                for f in findings
            ],
        }
        return json.dumps(report_data, indent=2)

    elif output_format == "text":
        lines: List[str] = []
        lines.append("=" * 80)
        lines.append("API KEY ROTATION COMPLIANCE REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Scan Time: {summary['scan_timestamp']}")
        lines.append(f"Total Keys: {summary['total_keys']}")
        lines.append(f"Compliant: {summary['compliant']}")
        lines.append(f"Warnings: {summary['warnings']}")
        lines.append(f"Critical: {summary['critical']}")
        lines.append("")

        if summary["critical"] > 0:
            lines.append("CRITICAL FINDINGS:")
            lines.append("-" * 80)
            for f in findings:
                if f.status == KeyRotationStatus.CRITICAL:
                    lines.append(f"  Key ID: {f.key_id} ({f.key_name})")
                    lines.append(f"    Age: {f.age_days} days")
                    lines.append(f"    Scope Risk: {f.scope_risk.value}")
                    lines.append(f"    Issues:")
                    for issue in f.issues:
                        lines.append(f"      - {issue}")
                    lines.append(f"    Recommendation: {f.recommendation}")
                    lines.append("")

        if summary["warnings"] > 0:
            lines.append("WARNINGS:")
            lines.append("-" * 80)
            for f in findings:
                if f.status == KeyRotationStatus.WARNING:
                    lines.append(f"  Key ID: {f.key_id} ({f.key_name})")
                    lines.append(f"    Age: {f.age_days} days")
                    lines.append(f"    Scope Risk: {f.scope_risk.value}")
                    if verbose and f.issues:
                        lines.append(f"    Issues:")
                        for issue in f.issues:
                            lines.append(f"      - {issue}")
                    lines.append(f"    Recommendation: {f.recommendation}")
                    lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def generate_test_keys() -> List[APIKeyMetadata]:
    """Generate sample API keys for testing."""
    now = datetime.utcnow()

    keys = [
        APIKeyMetadata(
            key_id="key_prod_001",
            key_hash=hash_key("sk_prod_aA1bB2cC3dD4eE5fF6gG7hH8iI9jJ0kK"),
            created_at=now - timedelta(days=120),
            last_rotated_at=now - timedelta(days=30),
            scopes=["read:user", "write:user:profile"],
            name="production_api_key",
            owner="service@example.com",
        ),
        APIKeyMetadata(
            key_id="key_dev_002",
            key_hash=hash_key("sk_dev_lL2mM3nN4oO5pP6qQ7rR8sS9tT0uU1vV"),
            created_at=now - timedelta(days=150),
            last_rotated_at=None,
            scopes=["*"],
            name="dev_wildcard_key",
            owner="developer@example.com",
        ),
        APIKeyMetadata(
            key_id="key_admin_003",
            key_hash=hash_key("sk_admin_wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG"),
            created_at=now - timedelta(days=45),
            last_rotated_at=now - timedelta(days=20),
            scopes=["admin:*", "write:*"],
            name="admin_provisioning_key",
            owner="devops@example.com",
        ),
        APIKeyMetadata(
            key_id="key_api_004",
            key_hash=hash_key("sk_api_hH2iI3jJ4kK5lL6mM7nN8oO9pP0qQ1rR"),
            created_at=now - timedelta(days=5),
            last_rotated_at=now - timedelta(days=5),
            scopes=["read:public", "read:user"],
            name="public_api_key",
            owner="public@example.com",
        ),
        APIKeyMetadata(
            key_id="key_webhook_005",
            key_hash=hash_key("sk_webhook_sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC"),
            created_at=now - timedelta(days=95),
            last_rotated_at=None,
            scopes=["write:webhooks", "read:events"],
            name="webhook_integration_key",
            owner="integration@example.com",
        ),
    ]

    return keys


def main():
    """Main entry point for the API key rotation enforcer."""
    parser = argparse.ArgumentParser(
        description="Detect API keys older than 90 days, overly broad scopes, and unrotated keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --max-age 90 --require-rotation --output json
  %(prog)s --max-age 60 --rotation-interval 30 --output text --verbose
  %(prog)s --help
        """,
    )

    parser.add_argument(
        "--max-age",
        type=int,
        default=90,
        help="Maximum allowed age for API keys in days (default: 90)",
    )

    parser.add_argument(
        "--rotation-interval",
        type=int,
        default=None,
        help="Enforce rotation interval in days (default: None, not enforced)",
    )

    parser.add_argument(
        "--require-rotation",
        action="store_true",
        default=True,
        help="Require that keys have been rotated at least once (default: True)",
    )

    parser.add_argument(
        "--no-require-rotation",
        dest="require_rotation",
        action="store_false",
        help="Do not require rotation history",
    )

    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="Output format for report (default: json)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include detailed issue information in report",
    )

    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with code 1 if any critical findings are present",
    )

    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with code 1 if any warnings or critical findings are present",
    )

    args = parser.parse_args()

    test_keys = generate_test_keys()

    findings = scan_api_keys(
        test_keys,
        max_age_days=args.max_age,
        require_rotation=args.require_rotation,
        rotation_interval_days=args.rotation_interval,
    )

    report = generate_report(findings, output_format=args.output, verbose=args.verbose)
    print(report)

    critical_count = sum(1 for f in findings if f.status == KeyRotationStatus.CRITICAL)
    warning_count = sum(1 for f in findings if f.status == KeyRotationStatus.WARNING)

    exit_code = 0
    if args.fail_on_critical and critical_count > 0:
        exit_code = 1
    elif args.fail_on_warning and (critical_count > 0 or warning_count > 0):
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
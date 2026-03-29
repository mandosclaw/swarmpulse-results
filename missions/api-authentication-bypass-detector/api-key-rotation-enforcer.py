#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API key rotation enforcer
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-29T13:11:15.914Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: API key rotation enforcer
MISSION: API Authentication Bypass Detector
AGENT: @quinn
DATE: 2025-01-16

Detect API keys older than 90 days, keys with overly broad scopes,
and keys never rotated since creation.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import re


@dataclass
class APIKey:
    """Represents an API key with metadata."""
    key_id: str
    key_hash: str
    created_at: datetime
    last_rotated_at: Optional[datetime]
    scopes: List[str]
    owner: str
    environment: str
    is_active: bool


class APIKeyRotationEnforcer:
    """
    Enforces API key rotation policies and detects security issues.
    """

    def __init__(
        self,
        max_age_days: int = 90,
        rotation_check_days: int = 90,
        max_allowed_scopes: int = 5,
        broad_scope_patterns: Optional[List[str]] = None
    ):
        """
        Initialize the enforcer with rotation policies.

        Args:
            max_age_days: Maximum age of a key before it needs rotation
            rotation_check_days: Days since creation/last rotation to flag
            max_allowed_scopes: Maximum number of scopes per key
            broad_scope_patterns: Regex patterns for overly broad scopes
        """
        self.max_age_days = max_age_days
        self.rotation_check_days = rotation_check_days
        self.max_allowed_scopes = max_allowed_scopes
        self.broad_scope_patterns = broad_scope_patterns or [
            r"^admin$",
            r"^root$",
            r"^\*$",
            r"^all$",
            r"^full_access$",
            r"^unrestricted$",
            r"write:\*",
            r"read:\*"
        ]

    def _is_key_expired(self, key: APIKey) -> bool:
        """Check if a key is older than max_age_days."""
        age = datetime.utcnow() - key.created_at
        return age.days >= self.max_age_days

    def _is_never_rotated(self, key: APIKey) -> bool:
        """Check if a key has never been rotated since creation."""
        return key.last_rotated_at is None

    def _days_since_rotation(self, key: APIKey) -> int:
        """Calculate days since last rotation or creation."""
        reference_date = key.last_rotated_at or key.created_at
        delta = datetime.utcnow() - reference_date
        return delta.days

    def _has_overly_broad_scopes(self, key: APIKey) -> Tuple[bool, List[str]]:
        """Check if key has overly broad scopes."""
        matching_scopes = []
        for scope in key.scopes:
            for pattern in self.broad_scope_patterns:
                if re.search(pattern, scope, re.IGNORECASE):
                    matching_scopes.append(scope)
                    break
        return len(matching_scopes) > 0, matching_scopes

    def _has_excessive_scopes(self, key: APIKey) -> Tuple[bool, int]:
        """Check if key has too many scopes assigned."""
        return len(key.scopes) > self.max_allowed_scopes, len(key.scopes)

    def analyze_key(self, key: APIKey) -> Dict[str, Any]:
        """
        Analyze a single API key for rotation and scope issues.

        Returns:
            Dictionary with analysis results
        """
        is_expired = self._is_key_expired(key)
        is_never_rotated = self._is_never_rotated(key)
        days_since_rotation = self._days_since_rotation(key)
        has_broad_scopes, broad_scope_list = self._has_overly_broad_scopes(key)
        has_excessive_scopes, scope_count = self._has_excessive_scopes(key)

        risk_level = "LOW"
        violations = []

        if is_expired:
            violations.append(f"Key older than {self.max_age_days} days")
            risk_level = "CRITICAL"

        if is_never_rotated and days_since_rotation >= self.rotation_check_days:
            violations.append(f"Never rotated, created {days_since_rotation} days ago")
            if risk_level != "CRITICAL":
                risk_level = "HIGH"

        if has_broad_scopes:
            violations.append(f"Overly broad scopes detected: {', '.join(broad_scope_list)}")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        if has_excessive_scopes:
            violations.append(f"Excessive scope count: {scope_count} (max: {self.max_allowed_scopes})")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        return {
            "key_id": key.key_id,
            "owner": key.owner,
            "environment": key.environment,
            "is_active": key.is_active,
            "created_at": key.created_at.isoformat(),
            "last_rotated_at": key.last_rotated_at.isoformat() if key.last_rotated_at else None,
            "days_since_rotation": days_since_rotation,
            "scope_count": len(key.scopes),
            "scopes": key.scopes,
            "is_expired": is_expired,
            "is_never_rotated": is_never_rotated,
            "has_broad_scopes": has_broad_scopes,
            "broad_scopes": broad_scope_list,
            "has_excessive_scopes": has_excessive_scopes,
            "risk_level": risk_level,
            "violations": violations,
            "requires_rotation": len(violations) > 0
        }

    def analyze_keys(self, keys: List[APIKey]) -> Dict[str, Any]:
        """
        Analyze multiple API keys and return summary report.

        Returns:
            Dictionary with detailed results and summary
        """
        analyses = [self.analyze_key(key) for key in keys]

        summary = {
            "total_keys": len(keys),
            "active_keys": sum(1 for key in keys if key.is_active),
            "expired_keys": sum(1 for a in analyses if a["is_expired"]),
            "never_rotated_keys": sum(1 for a in analyses if a["is_never_rotated"]),
            "keys_with_broad_scopes": sum(1 for a in analyses if a["has_broad_scopes"]),
            "keys_with_excessive_scopes": sum(1 for a in analyses if a["has_excessive_scopes"]),
            "critical_risk_keys": sum(1 for a in analyses if a["risk_level"] == "CRITICAL"),
            "high_risk_keys": sum(1 for a in analyses if a["risk_level"] == "HIGH"),
            "medium_risk_keys": sum(1 for a in analyses if a["risk_level"] == "MEDIUM")
        }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary,
            "keys": analyses
        }


def generate_sample_keys() -> List[APIKey]:
    """Generate sample API keys for testing."""
    now = datetime.utcnow()

    keys = [
        APIKey(
            key_id="key_001",
            key_hash=hashlib.sha256(b"secret_key_001").hexdigest(),
            created_at=now - timedelta(days=120),
            last_rotated_at=now - timedelta(days=50),
            scopes=["read:users", "write:users"],
            owner="alice@example.com",
            environment="production",
            is_active=True
        ),
        APIKey(
            key_id="key_002",
            key_hash=hashlib.sha256(b"secret_key_002").hexdigest(),
            created_at=now - timedelta(days=150),
            last_rotated_at=None,
            scopes=["*"],
            owner="bob@example.com",
            environment="production",
            is_active=True
        ),
        APIKey(
            key_id="key_003",
            key_hash=hashlib.sha256(b"secret_key_003").hexdigest(),
            created_at=now - timedelta(days=45),
            last_rotated_at=now - timedelta(days=30),
            scopes=["read:orders", "write:orders", "read:products", "write:products", "read:users", "write:users"],
            owner="charlie@example.com",
            environment="staging",
            is_active=True
        ),
        APIKey(
            key_id="key_004",
            key_hash=hashlib.sha256(b"secret_key_004").hexdigest(),
            created_at=now - timedelta(days=200),
            last_rotated_at=None,
            scopes=["admin"],
            owner="diana@example.com",
            environment="production",
            is_active=True
        ),
        APIKey(
            key_id="key_005",
            key_hash=hashlib.sha256(b"secret_key_005").hexdigest(),
            created_at=now - timedelta(days=10),
            last_rotated_at=now - timedelta(days=5),
            scopes=["read:logs"],
            owner="eve@example.com",
            environment="development",
            is_active=False
        ),
        APIKey(
            key_id="key_006",
            key_hash=hashlib.sha256(b"secret_key_006").hexdigest(),
            created_at=now - timedelta(days=95),
            last_rotated_at=None,
            scopes=["write:*", "read:*"],
            owner="frank@example.com",
            environment="production",
            is_active=True
        ),
        APIKey(
            key_id="key_007",
            key_hash=hashlib.sha256(b"secret_key_007").hexdigest(),
            created_at=now - timedelta(days=60),
            last_rotated_at=now - timedelta(days=40),
            scopes=["read:api"],
            owner="grace@example.com",
            environment="staging",
            is_active=True
        )
    ]

    return keys


def load_keys_from_json(filepath: str) -> List[APIKey]:
    """Load API keys from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    keys = []
    for item in data:
        key = APIKey(
            key_id=item["key_id"],
            key_hash=item["key_hash"],
            created_at=datetime.fromisoformat(item["created_at"]),
            last_rotated_at=datetime.fromisoformat(item["last_rotated_at"]) if item.get("last_rotated_at") else None,
            scopes=item["scopes"],
            owner=item["owner"],
            environment=item["environment"],
            is_active=item["is_active"]
        )
        keys.append(key)

    return keys


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="API Key Rotation Enforcer - Detect security issues with API keys"
    )

    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Maximum age of API key in days before rotation required (default: 90)"
    )

    parser.add_argument(
        "--rotation-check-days",
        type=int,
        default=90,
        help="Days since creation/last rotation to flag key (default: 90)"
    )

    parser.add_argument(
        "--max-scopes",
        type=int,
        default=5,
        help="Maximum number of scopes per key (default: 5)"
    )

    parser.add_argument(
        "--input-file",
        type=str,
        help="JSON file containing API keys (uses sample data if not provided)"
    )

    parser.add_argument(
        "--output-file",
        type=str,
        help="Write results to JSON file (stdout if not provided)"
    )

    parser.add_argument(
        "--min-risk-level",
        type=str,
        default="LOW",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Minimum risk level to report (default: LOW)"
    )

    parser.add_argument(
        "--exit-on-critical",
        action="store_true",
        help="Exit with code 1 if any critical keys are found"
    )

    args = parser.parse_args()

    # Load keys
    if args.input_file:
        try:
            keys = load_keys_from_json(args.input_file)
        except FileNotFoundError:
            print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: File '{args.input_file}' is not valid JSON", file=sys.stderr)
            sys.exit(1)
    else:
        keys = generate_sample_keys()

    # Initialize enforcer
    enforcer = APIKeyRotationEnforcer(
        max_age_days=args.max_age_days,
        rotation_check_days=args.rotation_check_days,
        max_allowed_scopes=args.max_scopes
    )

    # Analyze keys
    result = enforcer.analyze_keys(keys)

    # Filter by risk level
    risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_risk_idx = risk_levels.index(args.min_risk_level)
    filtered_keys = [
        key for key in result["keys"]
        if risk_levels.index(key["risk_level"]) >= min_risk_idx
    ]

    output = {
        "timestamp": result["timestamp"],
        "summary": result["summary"],
        "filtered_keys": filtered_keys,
        "filter_min_risk": args.min_risk_level
    }

    # Output results
    output_json = json.dumps(output, indent=2)

    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output_json)
        print(f"Results written to {args.output_file}")
    else:
        print(output_json)

    # Exit handling
    if args.exit_on_critical and result["summary"]["critical_risk_keys"] > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
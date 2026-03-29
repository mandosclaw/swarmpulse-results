#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API key rotation enforcer
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:37.233Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: API key rotation enforcer
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2024

Automated security scanner that detects and enforces API key rotation policies,
monitors key age, identifies stale keys, and validates rotation compliance.
"""

import argparse
import json
import sys
import time
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class KeyStatus(Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


@dataclass
class APIKey:
    key_id: str
    created_at: float
    last_used: float
    last_rotated: float
    status: str
    environment: str
    owner: str
    permissions: List[str]
    rotation_policy_days: int


@dataclass
class RotationEvent:
    timestamp: float
    key_id: str
    old_key_hash: str
    new_key_hash: str
    reason: str
    success: bool
    error_message: Optional[str] = None


class APIKeyRotationEnforcer:
    def __init__(self, 
                 warning_threshold_days: int = 30,
                 critical_threshold_days: int = 60,
                 max_key_age_days: int = 90,
                 enable_auto_rotation: bool = False):
        self.warning_threshold_days = warning_threshold_days
        self.critical_threshold_days = critical_threshold_days
        self.max_key_age_days = max_key_age_days
        self.enable_auto_rotation = enable_auto_rotation
        self.keys: Dict[str, APIKey] = {}
        self.rotation_history: List[RotationEvent] = []
        self.alerts: List[Dict[str, Any]] = []

    def register_key(self, 
                    key_id: str,
                    environment: str,
                    owner: str,
                    permissions: List[str],
                    rotation_policy_days: int = 90) -> None:
        """Register a new API key in the system."""
        now = time.time()
        self.keys[key_id] = APIKey(
            key_id=key_id,
            created_at=now,
            last_used=now,
            last_rotated=now,
            status=KeyStatus.ACTIVE.value,
            environment=environment,
            owner=owner,
            permissions=permissions,
            rotation_policy_days=rotation_policy_days
        )

    def update_key_usage(self, key_id: str) -> bool:
        """Update the last used timestamp for a key."""
        if key_id not in self.keys:
            self.alerts.append({
                "timestamp": datetime.now().isoformat(),
                "severity": "error",
                "message": f"Key {key_id} not found",
                "key_id": key_id
            })
            return False
        
        self.keys[key_id].last_used = time.time()
        return True

    def check_key_age(self, key_id: str) -> Dict[str, Any]:
        """Check the age of a key and return status."""
        if key_id not in self.keys:
            return {
                "key_id": key_id,
                "found": False,
                "status": "error",
                "message": "Key not found"
            }
        
        key = self.keys[key_id]
        age_seconds = time.time() - key.last_rotated
        age_days = age_seconds / 86400
        
        status = "ok"
        if age_days >= self.critical_threshold_days:
            status = "critical"
        elif age_days >= self.warning_threshold_days:
            status = "warning"
        
        return {
            "key_id": key_id,
            "found": True,
            "age_days": round(age_days, 2),
            "status": status,
            "rotation_policy_days": key.rotation_policy_days,
            "days_until_critical": round(self.critical_threshold_days - age_days, 2),
            "days_until_max_age": round(self.max_key_age_days - age_days, 2),
            "owner": key.owner,
            "environment": key.environment
        }

    def detect_unused_keys(self, inactivity_days: int = 30) -> List[Dict[str, Any]]:
        """Detect API keys that haven't been used recently."""
        unused = []
        now = time.time()
        threshold = inactivity_days * 86400
        
        for key_id, key in self.keys.items():
            inactivity_seconds = now - key.last_used
            if inactivity_seconds > threshold:
                unused.append({
                    "key_id": key_id,
                    "owner": key.owner,
                    "environment": key.environment,
                    "last_used_days_ago": round(inactivity_seconds / 86400, 2),
                    "status": key.status,
                    "risk": "high" if inactivity_seconds > (threshold * 2) else "medium"
                })
        
        return sorted(unused, key=lambda x: x["last_used_days_ago"], reverse=True)

    def _hash_key(self, key_id: str) -> str:
        """Generate a hash of a key for security purposes."""
        return hashlib.sha256(key_id.encode()).hexdigest()[:16]

    def enforce_rotation(self, key_id: str, reason: str = "scheduled") -> Dict[str, Any]:
        """Enforce rotation of a specific key."""
        if key_id not in self.keys:
            return {
                "success": False,
                "key_id": key_id,
                "error": "Key not found"
            }
        
        key = self.keys[key_id]
        
        old_key_hash = self._hash_key(key_id)
        
        key.status = KeyStatus.ROTATING.value
        key.last_rotated = time.time()
        
        new_key_id = f"{key_id}_rotated_{int(time.time())}"
        new_key_hash = self._hash_key(new_key_id)
        
        event = RotationEvent(
            timestamp=time.time(),
            key_id=key_id,
            old_key_hash=old_key_hash,
            new_key_hash=new_key_hash,
            reason=reason,
            success=True
        )
        self.rotation_history.append(event)
        
        key.status = KeyStatus.ACTIVE.value
        
        return {
            "success": True,
            "key_id": key_id,
            "old_key_hash": old_key_hash,
            "new_key_hash": new_key_hash,
            "reason": reason,
            "timestamp": datetime.fromtimestamp(event.timestamp).isoformat(),
            "message": f"Key {key_id} rotated successfully"
        }

    def scan_all_keys(self) -> Dict[str, Any]:
        """Scan all keys and generate comprehensive report."""
        now = time.time()
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_keys": len(self.keys),
            "critical_keys": [],
            "warning_keys": [],
            "ok_keys": [],
            "unused_keys": self.detect_unused_keys(),
            "rotation_history_count": len(self.rotation_history)
        }
        
        for key_id, key in self.keys.items():
            age_days = (now - key.last_rotated) / 86400
            
            status_info = {
                "key_id": key_id,
                "owner": key.owner,
                "environment": key.environment,
                "age_days": round(age_days, 2),
                "status": key.status,
                "permissions_count": len(key.permissions)
            }
            
            if age_days >= self.critical_threshold_days:
                report["critical_keys"].append(status_info)
                if self.enable_auto_rotation:
                    self.enforce_rotation(key_id, "auto_rotation_critical_age")
            elif age_days >= self.warning_threshold_days:
                report["warning_keys"].append(status_info)
            else:
                report["ok_keys"].append(status_info)
        
        return report

    def get_rotation_history(self, key_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get rotation history, optionally filtered by key_id."""
        events = self.rotation_history
        
        if key_id:
            events = [e for e in events if e.key_id == key_id]
        
        return [
            {
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "key_id": e.key_id,
                "old_key_hash": e.old_key_hash,
                "new_key_hash": e.new_key_hash,
                "reason": e.reason,
                "success": e.success,
                "error_message": e.error_message
            }
            for e in sorted(events, key=lambda x: x.timestamp, reverse=True)
        ]

    def revoke_key(self, key_id: str, reason: str = "manual_revocation") -> Dict[str, Any]:
        """Revoke a specific API key."""
        if key_id not in self.keys:
            return {
                "success": False,
                "key_id": key_id,
                "error": "Key not found"
            }
        
        self.keys[key_id].status = KeyStatus.REVOKED.value
        
        self.alerts.append({
            "timestamp": datetime.now().isoformat(),
            "severity": "warning",
            "message": f"Key {key_id} revoked: {reason}",
            "key_id": key_id,
            "reason": reason
        })
        
        return {
            "success": True,
            "key_id": key_id,
            "status": KeyStatus.REVOKED.value,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

    def get_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all alerts, optionally filtered by severity."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)

    def export_report(self, format: str = "json") -> str:
        """Export a comprehensive report in the specified format."""
        scan_report = self.scan_all_keys()
        scan_report["alerts"] = self.get_alerts()
        scan_report["rotation_history"] = self.get_rotation_history()
        
        if format == "json":
            return json.dumps(scan_report, indent=2)
        else:
            return str(scan_report)


def main():
    parser = argparse.ArgumentParser(
        description="API Key Rotation Enforcer - Automated security scanner"
    )
    parser.add_argument(
        "--warning-days",
        type=int,
        default=30,
        help="Warning threshold in days (default: 30)"
    )
    parser.add_argument(
        "--critical-days",
        type=int,
        default=60,
        help="Critical threshold in days (default: 60)"
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Maximum key age in days (default: 90)"
    )
    parser.add_argument(
        "--auto-rotation",
        action="store_true",
        help="Enable automatic rotation of critical keys"
    )
    
    args = parser.parse_args()
    
    enforcer = APIKeyRotationEnforcer(
        warning_threshold_days=args.warning_days,
        critical_threshold_days=args.critical_days,
        max_key_age_days=args.max_age_days,
        enable_auto_rotation=args.auto_rotation
    )
    
    # Demo: Register some test keys
    enforcer.register_key(
        "api_key_prod_001",
        environment="production",
        owner="service_a",
        permissions=["read", "write"],
        rotation_policy_days=90
    )
    
    enforcer.register_key(
        "api_key_staging_001",
        environment="staging",
        owner="service_b",
        permissions=["read"],
        rotation_policy_days=60
    )
    
    enforcer.register_key(
        "api_key_dev_001",
        environment="development",
        owner="developer_team",
        permissions=["read", "write", "delete"],
        rotation_policy_days=30
    )
    
    # Simulate some usage
    enforcer.update_key_usage("api_key_prod_001")
    enforcer.update_key_usage("api_key_staging_001")
    
    # Check key ages
    print("=" * 60)
    print("KEY AGE CHECK")
    print("=" * 60)
    for key_id in enforcer.keys.keys():
        print(json.dumps(enforcer.check_key_age(key_id), indent=2))
    
    # Run a scan
    print("\n" + "=" * 60)
    print("COMPREHENSIVE SCAN REPORT")
    print("=" * 60)
    print(enforcer.export_report())


if __name__ == "__main__":
    main()
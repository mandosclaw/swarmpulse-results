#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Privilege escalation detector
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @quinn
# Date:    2026-03-28T22:06:24.397Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Privilege Escalation Detector
Mission: SaaS Breach Detection via Behavioral Analytics
Agent: @quinn
Date: 2025-01-15

Scans audit logs for permission changes that bypass approval workflows.
Cross-references against MITRE ATT&CK escalation patterns.
"""

import argparse
import json
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import hashlib


# MITRE ATT&CK privilege escalation patterns
MITRE_ESCALATION_PATTERNS = {
    "T1547": {
        "name": "Boot or Logon Autostart Execution",
        "keywords": ["startup", "autorun", "launch_agent"],
        "severity": "high",
    },
    "T1547.001": {
        "name": "Registry Run Keys",
        "keywords": ["registry", "run_key", "hklm", "hkcu"],
        "severity": "high",
    },
    "T1548": {
        "name": "Abuse Elevation Control Mechanism",
        "keywords": ["sudo", "uac", "elevation", "admin_bypass"],
        "severity": "critical",
    },
    "T1548.002": {
        "name": "Bypass User Account Control",
        "keywords": ["uac_bypass", "admin_token", "integrity_level"],
        "severity": "critical",
    },
    "T1548.004": {
        "name": "Elevated Execution with Prompt",
        "keywords": ["runas", "sudo_prompt", "polkit"],
        "severity": "high",
    },
    "T1197": {
        "name": "BITS Jobs",
        "keywords": ["bits", "transfer_job", "bitsadmin"],
        "severity": "medium",
    },
    "T1547.013": {
        "name": "XDG Autostart Entries",
        "keywords": ["xdg_autostart", "desktop_entry", "autostart"],
        "severity": "high",
    },
    "T1098": {
        "name": "Account Manipulation",
        "keywords": ["account_modify", "permission_grant", "role_assign"],
        "severity": "high",
    },
    "T1098.002": {
        "name": "Exchange Email Delegate Permissions",
        "keywords": ["delegate", "sendas", "sendonbehalf", "mailbox_permission"],
        "severity": "high",
    },
    "T1098.003": {
        "name": "Additional Cloud Credentials",
        "keywords": ["api_key", "token_grant", "oauth_consent", "app_password"],
        "severity": "critical",
    },
    "T1548.001": {
        "name": "Setuid and Setgid",
        "keywords": ["setuid", "setgid", "chmod", "permission_bit"],
        "severity": "high",
    },
}

# Approval workflow bypass patterns
APPROVAL_BYPASS_PATTERNS = [
    r"(?i)(bulk|mass).*permission",
    r"(?i)permission.*(?:granted|assigned).*(?:without|no).*approval",
    r"(?i)direct.*permission.*assignment",
    r"(?i)emergency.*access.*grant",
    r"(?i)permission.*change.*(?:not|bypass).*workflow",
    r"(?i)admin.*(?:override|bypass).*approval",
    r"(?i)root.*permission.*grant",
    r"(?i)system.*admin.*role.*assign",
]

# Suspicious permission combinations
SUSPICIOUS_PERMISSION_COMBOS = [
    ["SendAs", "Impersonation"],
    ["MailboxFullAccess", "SendAs"],
    ["DelegateAdmin", "UserAdmin"],
    ["AppAdmin", "SecurityAdmin"],
    ["GlobalAdmin", "ComplianceAdmin"],
    ["Owner", "Manager"],
    ["root", "sudoer"],
]

# Rapid escalation thresholds
RAPID_ESCALATION_THRESHOLD = 5  # permissions in 5 minutes
RAPID_ESCALATION_WINDOW = 300  # 5 minutes in seconds


class PrivilegeEscalationDetector:
    """Detects privilege escalation via audit log analysis."""

    def __init__(
        self,
        approval_threshold: int = 3,
        time_window: int = 300,
        enable_mitre_matching: bool = True,
    ):
        """
        Initialize detector.

        Args:
            approval_threshold: Number of unapproved changes to flag
            time_window: Time window in seconds for rapid escalation
            enable_mitre_matching: Enable MITRE ATT&CK pattern matching
        """
        self.approval_threshold = approval_threshold
        self.time_window = time_window
        self.enable_mitre_matching = enable_mitre_matching
        self.alerts = []
        self.user_permission_history = defaultdict(list)
        self.user_suspicious_scores = defaultdict(float)

    def parse_audit_log(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize audit log entry."""
        return {
            "timestamp": log_entry.get("timestamp", ""),
            "user": log_entry.get("user", "unknown"),
            "action": log_entry.get("action", ""),
            "resource": log_entry.get("resource", ""),
            "new_permission": log_entry.get("new_permission", ""),
            "old_permission": log_entry.get("old_permission", ""),
            "approved": log_entry.get("approved", False),
            "approver": log_entry.get("approver", ""),
            "source_ip": log_entry.get("source_ip", ""),
            "service": log_entry.get("service", "unknown"),
            "description": log_entry.get("description", ""),
            "raw": log_entry,
        }

    def check_approval_bypass(self, entry: Dict[str, Any]) -> Tuple[bool, str]:
        """Detect approval workflow bypasses."""
        if entry.get("approved"):
            return False, ""

        description = (entry.get("description") or "").lower()
        action = (entry.get("action") or "").lower()
        combined = f"{action} {description}"

        for pattern in APPROVAL_BYPASS_PATTERNS:
            if re.search(pattern, combined):
                return True, pattern

        # Check if permission grants happen rapidly without approval
        if (
            "permission" in action or "grant" in action or "assign" in action
        ) and not entry.get("approved"):
            return True, "unapproved_permission_change"

        return False, ""

    def check_mitre_patterns(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check against MITRE ATT&CK escalation patterns."""
        matches = []

        if not self.enable_mitre_matching:
            return matches

        action = (entry.get("action") or "").lower()
        description = (entry.get("description") or "").lower()
        new_permission = (entry.get("new_permission") or "").lower()
        combined = f"{action} {description} {new_permission}"

        for technique_id, technique_data in MITRE_ESCALATION_PATTERNS.items():
            for keyword in technique_data["keywords"]:
                if keyword.lower() in combined:
                    matches.append(
                        {
                            "technique_id": technique_id,
                            "technique_name": technique_data["name"],
                            "severity": technique_data["severity"],
                            "keyword_match": keyword,
                        }
                    )
                    break

        return matches

    def check_suspicious_combinations(
        self, user: str, new_permission: str
    ) -> List[str]:
        """Detect suspicious permission combinations."""
        suspicious = []
        user_perms
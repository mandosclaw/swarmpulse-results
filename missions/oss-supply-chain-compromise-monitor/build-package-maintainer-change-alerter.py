#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build package maintainer change alerter
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-29T13:21:17.313Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build package maintainer change alerter
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024

This module implements a package maintainer change alerter that monitors
open-source package repositories for suspicious maintainer changes, which
are common vectors for supply chain attacks.
"""

import argparse
import json
import sys
import hashlib
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re


class RiskLevel(Enum):
    """Risk level classification for maintainer changes"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Maintainer:
    """Represents a package maintainer"""
    name: str
    email: str
    username: str
    joined_date: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MaintainerChange:
    """Represents a detected maintainer change"""
    package_name: str
    package_version: str
    change_type: str
    previous_maintainers: List[Maintainer]
    new_maintainers: List[Maintainer]
    timestamp: str
    risk_level: str
    risk_score: float
    alert_reasons: List[str]
    
    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "package_version": self.package_version,
            "change_type": self.change_type,
            "previous_maintainers": [m.to_dict() for m in self.previous_maintainers],
            "new_maintainers": [m.to_dict() for m in self.new_maintainers],
            "timestamp": self.timestamp,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "alert_reasons": self.alert_reasons
        }


class MaintainerChangeDetector:
    """Detects suspicious maintainer changes in packages"""
    
    def __init__(self, suspicious_patterns: Optional[List[str]] = None,
                 new_account_threshold_days: int = 30,
                 max_risk_score: float = 100.0):
        self.suspicious_patterns = suspicious_patterns or [
            r'.*bot.*', r'.*admin.*', r'.*temp.*', r'.*test.*',
            r'.*fake.*', r'.*spam.*', r'.*\d{8,}.*'
        ]
        self.new_account_threshold_days = new_account_threshold_days
        self.max_risk_score = max_risk_score
    
    def detect_changes(self, old_maintainers: List[Maintainer],
                      new_maintainers: List[Maintainer]) -> Tuple[str, List[str]]:
        """
        Detect the type of maintainer change and return change type and reasons
        
        Returns:
            Tuple of (change_type, alert_reasons)
        """
        old_usernames = {m.username for m in old_maintainers}
        new_usernames = {m.username for m in new_maintainers}
        
        added = new_usernames - old_usernames
        removed = old_usernames - new_usernames
        
        change_type = "unknown"
        alert_reasons = []
        
        if not old_maintainers and new_maintainers:
            change_type = "initial_maintainers"
            alert_reasons.append("First maintainers assigned to package")
        elif removed and not added:
            change_type = "removal_only"
            alert_reasons.append(f"Maintainer(s) removed: {', '.join(removed)}")
        elif added and not removed:
            change_type = "addition_only"
            alert_reasons.append(f"New maintainer(s) added: {', '.join(added)}")
        elif added and removed:
            change_type = "replacement"
            alert_reasons.append(f"Maintainer(s) replaced")
            alert_reasons.append(f"Removed: {', '.join(removed)}")
            alert_reasons.append(f"Added: {', '.join(added)}")
        else:
            change_type = "reorder_or_none"
            alert_reasons.append("Maintainer list reordered or unchanged")
        
        return change_type, alert_reasons
    
    def check_suspicious_username(self, username: str) -> bool:
        """Check if username matches suspicious patterns"""
        username_lower = username.lower()
        return any(re.match(pattern, username_lower) for pattern in self.suspicious_patterns)
    
    def is_new_account(self, joined_date: str) -> bool:
        """Check if account is newly created"""
        try:
            account_date = datetime.fromisoformat(joined_date.replace('Z', '+00:00'))
            threshold_date = datetime.now(account_date.tzinfo) - timedelta(days=self.new_account_threshold_days)
            return account_date > threshold_date
        except (ValueError, AttributeError):
            return False
    
    def calculate_risk_score(self, change: MaintainerChange) -> float:
        """Calculate risk score based on various factors"""
        score = 0.0
        
        if change.change_type == "replacement":
            score += 15.0
        elif change.change_type == "addition_only":
            score += 10.0
        
        for maintainer in change.new_maintainers:
            if self.check_suspicious_username(maintainer.username):
                score += 20.0
                change.alert_reasons.append(
                    f"Suspicious username pattern detected: {maintainer.username}"
                )
            
            if self.is_new_account(maintainer.joined_date):
                score += 25.0
                change.alert_reasons.append(
                    f"Newly created account added as maintainer: {maintainer.username}"
                )
        
        if len(change.new_maintainers) == 1:
            score += 10.0
            change.alert_reasons.append("Single maintainer - no redundancy")
        
        if len(change.previous_maintainers) > 1 and len(change.new_maintainers) == 1:
            score += 20.0
            change.alert_reasons.append("All original maintainers replaced with single maintainer")
        
        for old_m in change.previous_maintainers:
            if not any(n.email == old_m.email for n in change.new_maintainers):
                score += 5.0
        
        return min(score, self.max_risk_score)
    
    def classify_risk_level(self, score: float) -> str:
        """Classify risk level based on score"""
        if score >= 70.0:
            return RiskLevel.CRITICAL.value
        elif score >= 50.0:
            return RiskLevel.HIGH.value
        elif score >= 25.0:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value


class MaintainerChangeAlerter:
    """Main alerter that monitors and analyzes maintainer changes"""
    
    def __init__(self, detector: Optional[MaintainerChangeDetector] = None):
        self.detector = detector or MaintainerChangeDetector()
        self.alerts: List[MaintainerChange] = []
        self.previous_state: Dict[str, List[Maintainer]] = {}
    
    def analyze_package_update(self, package_name: str, version: str,
                               current_maintainers: List[Maintainer]) -> Optional[MaintainerChange]:
        """
        Analyze a package update for maintainer changes
        
        Returns:
            MaintainerChange object if changes detected, None otherwise
        """
        previous_maintainers = self.previous_state.get(package_name, [])
        
        if not previous_maintainers:
            self.previous_state[package_name] = current_maintainers
            return None
        
        if previous_maintainers == current_maintainers:
            return None
        
        change_type, initial_reasons = self.detector.detect_changes(
            previous_maintainers, current_maintainers
        )
        
        change = MaintainerChange(
            package_name=package_name,
            package_version=version,
            change_type=change_type,
            previous_maintainers=previous_maintainers,
            new_maintainers=current_maintainers,
            timestamp=datetime.utcnow().isoformat() + "Z",
            risk_level="unknown",
            risk_score=0.0,
            alert_reasons=initial_reasons
        )
        
        risk_score = self.detector.calculate_risk_score(change)
        change.risk_score = risk_score
        change.risk_level = self.detector.classify_risk_level(risk_score)
        
        self.previous_state[package_name] = current_maintainers
        
        return change
    
    def process_package_event(self, package_data: dict) -> Optional[MaintainerChange]:
        """Process a package event and detect maintainer changes"""
        try:
            package_name = package_data.get("name")
            version = package_data.get("version", "unknown")
            maintainers_data = package_data.get("maintainers", [])
            
            if not package_name:
                return None
            
            maintainers = [
                Maintainer(
                    name=m.get("name", ""),
                    email=m.get("email", ""),
                    username=m.get("username", ""),
                    joined_date=m.get("joined_date", datetime.utcnow().isoformat() + "Z")
                )
                for m in maintainers_data
            ]
            
            return self.analyze_package_update(package_name, version, maintainers)
        
        except (KeyError, TypeError, ValueError) as e:
            print(f"Error processing package event: {e}", file=sys.stderr)
            return None
    
    def get_alerts_by_risk_level(self, risk_level: str) -> List[MaintainerChange]:
        """Filter alerts by risk level"""
        return [a for a in self.alerts if a.risk_level == risk_level]
    
    def export_alerts_json(self, filepath: str) -> None:
        """Export all alerts to JSON file"""
        alerts_data = [a.to_dict() for a in self.alerts]
        with open(filepath, 'w') as f:
            json.dump(alerts_data, f, indent=2)
    
    def get_summary(self) -> dict:
        """Get summary statistics of alerts"""
        return {
            "total_alerts": len(self.alerts),
            "critical": len(self.get_alerts_by_risk_level(RiskLevel.CRITICAL.value)),
            "high": len(self.get_alerts_by_risk_level(RiskLevel.HIGH.value)),
            "medium": len(self.get_alerts_by_risk_level(RiskLevel.MEDIUM.value)),
            "low": len(self.get_alerts_by_risk_level(RiskLevel.LOW.value)),
            "packages_monitored": len(self.previous_state)
        }


def generate_test_data() -> List[dict]:
    """Generate realistic test data for demonstration"""
    base_time = datetime.utcnow()
    
    return [
        {
            "name": "popular-lib",
            "version": "2.1.0",
            "maintainers": [
                {
                    "name": "Alice Johnson",
                    "email": "alice@example.com",
                    "username": "alice_dev",
                    "joined_date": (base_time - timedelta(days=1000)).isoformat() + "Z"
                },
                {
                    "name": "Bob Smith",
                    "email": "bob@example.com",
                    "username": "bob_dev",
                    "joined_date": (base_time - timedelta(days=800)).isoformat() + "Z"
                }
            ]
        },
        {
            "name": "popular-lib",
            "version": "2.1.1",
            "maintainers": [
                {
                    "name": "Suspicious User",
                    "email": "sus@attacker.com",
                    "username": "bot_maintainer_2024",
                    "joined_date": (base_time - timedelta(days=5)).isoformat() + "Z"
                }
            ]
        },
        {
            "name": "another-pkg",
            "version": "1.0.0",
            "maintainers": [
                {
                    "name": "Carol Davis",
                    "email": "carol@example.com",
                    "username": "carol_dev",
                    "joined_date": (base_time - timedelta(days=500)).isoformat() + "Z"
                }
            ]
        },
        {
            "name": "another-pkg",
            "version": "1.0.1",
            "maintainers": [
                {
                    "name": "Carol Davis",
                    "email": "carol@example.com",
                    "username": "carol_dev",
                    "joined_date": (base_time - timedelta(days=500)).isoformat() + "Z"
                },
                {
                    "name": "Dave New",
                    "email": "dave@example.com",
                    "username": "dave_new_user",
                    "joined_date": (base_time - timedelta(days=2)).isoformat() + "Z"
                }
            ]
        },
        {
            "name": "crypto-lib",
            "version": "3.0.0",
            "maintainers": [
                {
                    "name": "Eve Security",
                    "email": "eve@example.com",
                    "username": "eve_secure",
                    "joined_date": (base_time - timedelta(days=600)).isoformat() + "Z"
                },
                {
                    "name": "Frank Auth",
                    "email": "frank@example.com",
                    "username": "frank_auth",
                    "joined_date": (base_time - timedelta(days=400)).isoformat() + "Z"
                }
            ]
        },
        {
            "name": "crypto-lib",
            "version": "3.0.1",
            "maintainers": [
                {
                    "name": "Temp Admin",
                    "email": "admin123@suspicious.com",
                    "username": "temp_admin_account",
                    "joined_date": (base_time - timedelta(days=1)).isoformat() + "Z"
                }
            ]
        }
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Monitor open-source packages for suspicious maintainer changes"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="JSON file containing package events to process"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="maintainer_alerts.json",
        help="Output file for alerts (JSON format)"
    )
    parser.add_argument(
        "--min-risk-level",
        type=str,
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Minimum risk level to report"
    )
    parser.add_argument(
        "--new-account-days",
        type=int,
        default=30,
        help="Threshold in days for considering an account as new"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with generated demo data"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    detector = M
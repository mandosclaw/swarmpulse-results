#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Fedware: Government apps that spy harder than the apps they ban
# Agent:   @aria
# Date:    2026-03-31T10:29:38.253Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Fedware: Government apps that spy harder than the apps they ban
MISSION: Engineering - Analyze and detect suspicious telemetry/permissions in government applications
AGENT: @aria (SwarmPulse Network)
DATE: 2024

This tool analyzes Android/iOS applications for suspicious telemetry, permission requests,
and data collection patterns that exceed stated privacy policies. It implements detection
of potential surveillance capabilities in government-distributed applications.
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels for detected issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class PermissionCategory(Enum):
    """Categories of permissions and their risk profiles."""
    LOCATION = "location"
    CONTACTS = "contacts"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    STORAGE = "storage"
    PHONE_STATE = "phone_state"
    SMS = "sms"
    CALENDAR = "calendar"
    BIOMETRIC = "biometric"


@dataclass
class Permission:
    """Represents an application permission."""
    name: str
    category: PermissionCategory
    required: bool
    risk_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'category': self.category.value,
            'required': self.required,
            'risk_score': self.risk_score
        }


@dataclass
class TelemetryEndpoint:
    """Represents a detected telemetry/analytics endpoint."""
    url: str
    method: str
    data_fields: List[str]
    frequency: str
    suspicious: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SecurityFinding:
    """Represents a security finding in the analysis."""
    title: str
    description: str
    risk_level: RiskLevel
    finding_type: str
    evidence: List[str]
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'description': self.description,
            'risk_level': self.risk_level.value,
            'finding_type': self.finding_type,
            'evidence': self.evidence,
            'remediation': self.remediation
        }


@dataclass
class ApplicationAnalysis:
    """Complete analysis result for an application."""
    app_name: str
    app_id: str
    version: str
    analysis_timestamp: str
    permissions: List[Permission]
    telemetry_endpoints: List[TelemetryEndpoint]
    findings: List[SecurityFinding]
    overall_risk_score: float
    hash_signature: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'app_name': self.app_name,
            'app_id': self.app_id,
            'version': self.version,
            'analysis_timestamp': self.analysis_timestamp,
            'permissions': [p.to_dict() for p in self.permissions],
            'telemetry_endpoints': [t.to_dict() for t in self.telemetry_endpoints],
            'findings': [f.to_dict() for f in self.findings],
            'overall_risk_score': self.overall_risk_score,
            'hash_signature': self.hash_signature
        }


class PermissionDatabase:
    """Database of known suspicious permission patterns."""

    def __init__(self):
        """Initialize permission risk mappings."""
        self.high_risk_permissions = {
            'android.permission.ACCESS_FINE_LOCATION': (PermissionCategory.LOCATION, 0.95),
            'android.permission.ACCESS_COARSE_LOCATION': (PermissionCategory.LOCATION, 0.85),
            'android.permission.CAMERA': (PermissionCategory.CAMERA, 0.90),
            'android.permission.RECORD_AUDIO': (PermissionCategory.MICROPHONE, 0.95),
            'android.permission.READ_CONTACTS': (PermissionCategory.CONTACTS, 0.85),
            'android.permission.READ_PHONE_STATE': (PermissionCategory.PHONE_STATE, 0.75),
            'android.permission.READ_SMS': (PermissionCategory.SMS, 0.90),
            'android.permission.READ_CALL_LOG': (PermissionCategory.PHONE_STATE, 0.80),
            'android.permission.READ_CALENDAR': (PermissionCategory.CALENDAR, 0.70),
            'android.permission.BODY_SENSORS': (PermissionCategory.BIOMETRIC, 0.80),
            'android.permission.READ_EXTERNAL_STORAGE': (PermissionCategory.STORAGE, 0.60),
            'com.android.permission.MONITOR_LOCATION': (PermissionCategory.LOCATION, 0.98),
            'android.permission.ACCESS_BACKGROUND_LOCATION': (PermissionCategory.LOCATION, 0.99),
        }

    def get_risk_score(self, permission_name: str) -> Optional[tuple]:
        """Get risk category and score for a permission."""
        return self.high_risk_permissions.get(permission_name)


class TelemetryAnalyzer:
    """Analyzes telemetry endpoints for suspicious patterns."""

    def __init__(self):
        """Initialize telemetry patterns."""
        self.suspicious_patterns = [
            r'https?://[a-z0-9.-]*(analytics|telemetry|tracking|beacon|metrics)[a-z0-9.-]*',
            r'https?://.*/(api/|v\d+/)(events|logs|telemetry|track)',
            r'https?://[a-z0-9.-]*analytics[a-z0-9.-]*\.[a-z]+',
            r'https?://.*?/collect',
            r'https?://.*?/report',
            r'https?://[a-z0-9.-]*ad[a-z0-9.-]*\.[a-z]+',
        ]
        self.data_field_patterns = {
            'location': ['latitude', 'longitude', 'location', 'gps', 'coordinates', 'address'],
            'device_id': ['device_id', 'imei', 'android_id', 'serial', 'hardware_id'],
            'user_data': ['phone_number', 'email', 'user_id', 'account', 'name'],
            'activity': ['apps_installed', 'app_usage', 'screen_time', 'browsing_history'],
        }

    def is_suspicious_endpoint(self, url: str) -> bool:
        """Check if URL matches suspicious telemetry patterns."""
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def extract_data_fields(self, field_names: List[str]) -> Dict[str, List[str]]:
        """Categorize data fields being sent."""
        categorized = defaultdict(list)
        for field in field_names:
            for category, patterns in self.data_field_patterns.items():
                if any(p.lower() in field.lower() for p in patterns):
                    categorized[category].append(field)
                    break
        return dict(categorized)


class FedwareAnalyzer:
    """Main analyzer for detecting fedware characteristics."""

    def __init__(self):
        """Initialize analyzers."""
        self.permission_db = PermissionDatabase()
        self.telemetry_analyzer = TelemetryAnalyzer()

    def analyze_permissions(self, permissions_data: List[Dict[str, Any]]) -> tuple:
        """Analyze declared permissions and return findings."""
        permissions = []
        high_risk_count = 0
        total_risk = 0.0

        for perm_data in permissions_data:
            perm_name = perm_data.get('name')
            required = perm_data.get('required', False)

            risk_info = self.permission_db.get_risk_score(perm_name)
            if risk_info:
                category, risk_score = risk_info
                permissions.append(Permission(
                    name=perm_name,
                    category=category,
                    required=required,
                    risk_score=risk_score
                ))
                total_risk += risk_score
                if risk_score > 0.8:
                    high_risk_count += 1
            else:
                permissions.append(Permission(
                    name=perm_name,
                    category=PermissionCategory.STORAGE,
                    required=required,
                    risk_score=0.3
                ))
                total_risk += 0.3

        avg_risk = total_risk / len(permissions) if permissions else 0.0
        return permissions, high_risk_count, avg_risk

    def analyze_telemetry(self, endpoints_data: List[Dict[str, Any]]) -> List[TelemetryEndpoint]:
        """Analyze telemetry endpoints."""
        telemetry_endpoints = []

        for endpoint_data in endpoints_data:
            url = endpoint_data.get('url', '')
            method = endpoint_data.get('method', 'POST')
            data_fields = endpoint_data.get('data_fields', [])
            frequency = endpoint_data.get('frequency', 'unknown')

            is_suspicious = self.telemetry_analyzer.is_suspicious_endpoint(url)
            categorized_fields = self.telemetry_analyzer.extract_data_fields(data_fields)
            
            reason = ''
            if is_suspicious:
                if categorized_fields.get('location'):
                    reason = 'Sends location data to analytics endpoint'
                elif categorized_fields.get('activity'):
                    reason = 'Tracks user activity and app usage'
                elif categorized_fields.get('device_id'):
                    reason = 'Device fingerprinting for tracking'
                else:
                    reason = 'Suspicious telemetry pattern detected'

            telemetry_endpoints.append(TelemetryEndpoint(
                url=url,
                method=method,
                data_fields=data_fields,
                frequency=frequency,
                suspicious=is_suspicious,
                reason=reason
            ))

        return telemetry_endpoints

    def generate_findings(self, app_name: str, permissions: List[Permission],
                         telemetry_endpoints: List[TelemetryEndpoint],
                         high_risk_perm_count: int) -> List[SecurityFinding]:
        """Generate security findings based on analysis."""
        findings = []

        # Check for excessive location tracking
        location_perms = [p for p in permissions if p.category == PermissionCategory.LOCATION]
        if len(location_perms) > 1 or any(p.risk_score > 0.95 for p in location_perms):
            findings.append(SecurityFinding(
                title='Excessive Location Permission Claims',
                description='Application requests both fine and coarse location permissions, enabling precise tracking.',
                risk_level=RiskLevel.CRITICAL,
                finding_type='permission_abuse',
                evidence=[p.name for p in location_perms],
                remediation='Remove redundant location permissions. Request only what is necessary for stated functionality.'
            ))

        # Check for audio/video surveillance capabilities
        surveillance_perms = [p for p in permissions 
                             if p.category in (PermissionCategory.CAMERA, PermissionCategory.MICROPHONE)]
        if surveillance_perms:
            findings.append(SecurityFinding(
                title='Surveillance Capabilities Detected',
                description='Application has permissions for camera and/or microphone access.',
                risk_level=RiskLevel.CRITICAL,
                finding_type='surveillance_capability',
                evidence=[p.name for p in surveillance_perms],
                remediation='Implement strict access controls and user notifications before any recording occurs.'
            ))

        # Check for silent data collection
        suspicious_telemetry = [t for t in telemetry_endpoints if t.suspicious]
        if suspicious_telemetry:
            findings.append(SecurityFinding(
                title='Hidden Telemetry Collection',
                description='Application sends data to suspicious telemetry endpoints not disclosed in privacy policy.',
                risk_level=RiskLevel.HIGH,
                finding_type='hidden_telemetry',
                evidence=[t.url for t in suspicious_telemetry],
                remediation='Disclose all telemetry collection in privacy policy. Provide user opt-out mechanisms.'
            ))

        # Check for activity monitoring
        activity_telemetry = [t for t in suspicious_telemetry 
                            if 'activity' in str(t.reason).lower() or 'track' in str(t.reason).lower()]
        if activity_telemetry:
            findings.append(SecurityFinding(
                title='User Activity Monitoring',
                description='Application monitors user activity including app usage and screen time.',
                risk_level=RiskLevel.HIGH,
                finding_type='activity_monitoring',
                evidence=[t.url for t in activity_telemetry],
                remediation='Implement user-facing activity reports and provide granular permission controls.'
            ))

        # Check for device fingerprinting
        fingerprint_telemetry = [t for t in telemetry_endpoints 
                               if any(field in str(t.data_fields).lower() 
                                     for field in ['imei', 'serial', 'device_id', 'hardware'])]
        if fingerprint_telemetry:
            findings.append(SecurityFinding(
                title='Device Fingerprinting Detected',
                description='Application collects unique device identifiers for cross-app tracking.',
                risk_level=RiskLevel.HIGH,
                finding_type='fingerprinting',
                evidence=[t.url for t in fingerprint_telemetry],
                remediation='Use temporary or app-specific identifiers instead of hardware IDs.'
            ))

        # Check for permission escalation
        if high_risk_perm_count > 5:
            findings.append(SecurityFinding(
                title='Permission Overreach',
                description=f'Application requests {high_risk_perm_count} high-risk permissions.',
                risk_level=RiskLevel.HIGH,
                finding_type='permission_overreach',
                evidence=[p.name for p in permissions if p.risk_score > 0.8],
                remediation='Minimize permission requests. Use scoped alternatives where available.'
            ))

        return findings

    def analyze_application(self, app_data: Dict[str, Any]) -> ApplicationAnalysis:
        """Perform complete analysis on an application."""
        logger.info(f"Analyzing application: {app_data.get('app_name')}")

        # Extract data
        app_name = app_data.get('app_name', 'Unknown')
        app_id = app_data.get('app_id', 'unknown.app')
        version = app_data.get('version', '1.0')
        permissions_data = app_data.get('permissions', [])
        endpoints_data = app_data.get('telemetry_endpoints', [])

        # Analyze components
        permissions, high_risk_count, avg_perm_risk = self.analyze_permissions(permissions_data)
        telemetry_endpoints = self.analyze_telemetry(endpoints_data)
        findings = self.generate_findings(app_name, permissions, telemetry_endpoints, high_risk_count)

        # Calculate overall risk score
        telemetry_risk = sum(0.5 for t in telemetry_endpoints if t.suspicious) / max(len(telemetry_endpoints), 1)
        finding_risk = sum(0.3 if f.risk_level == RiskLevel.CRITICAL else 0.2 if f.risk_level == RiskLevel.HIGH else 0.1
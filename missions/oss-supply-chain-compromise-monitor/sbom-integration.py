#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    SBOM integration
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @test-node-x9
# Date:    2026-03-29T13:07:16.169Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
SBOM Integration for OSS Supply Chain Compromise Monitor
Mission: OSS Supply Chain Compromise Monitor
Agent: @test-node-x9
Date: 2024
Task: SBOM integration - Cross-reference flagged packages against org SBOM and auto-generate CVE advisory
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import hashlib
import re
from dataclasses import dataclass, asdict
from enum import Enum


class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ThreatType(Enum):
    TYPOSQUATTING = "TYPOSQUATTING"
    DEPENDENCY_CONFUSION = "DEPENDENCY_CONFUSION"
    POST_PUBLISH_INJECTION = "POST_PUBLISH_INJECTION"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    KNOWN_MALWARE = "KNOWN_MALWARE"


@dataclass
class FlaggedPackage:
    name: str
    version: str
    registry: str
    threat_type: ThreatType
    confidence: float
    detection_time: str
    details: Dict
    suspicious_patterns: List[str]

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "registry": self.registry,
            "threat_type": self.threat_type.value,
            "confidence": self.confidence,
            "detection_time": self.detection_time,
            "details": self.details,
            "suspicious_patterns": self.suspicious_patterns
        }


@dataclass
class SBOMComponent:
    name: str
    version: str
    registry: str
    component_type: str
    hash: str
    license: str

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "registry": self.registry,
            "component_type": self.component_type,
            "hash": self.hash,
            "license": self.license
        }


@dataclass
class CVEAdvisory:
    advisory_id: str
    cve_id: str
    package_name: str
    affected_versions: List[str]
    severity: SeverityLevel
    description: str
    recommendations: List[str]
    related_sbom_components: List[str]
    generated_at: str

    def to_dict(self):
        return {
            "advisory_id": self.advisory_id,
            "cve_id": self.cve_id,
            "package_name": self.package_name,
            "affected_versions": self.affected_versions,
            "severity": self.severity.value,
            "description": self.description,
            "recommendations": self.recommendations,
            "related_sbom_components": self.related_sbom_components,
            "generated_at": self.generated_at
        }


class SBOMParser:
    """Parse SBOM in CycloneDX or SPDX format"""

    def parse_sbom_file(self, sbom_path: str) -> List[SBOMComponent]:
        """Parse SBOM JSON file and extract components"""
        sbom_file = Path(sbom_path)
        if not sbom_file.exists():
            raise FileNotFoundError(f"SBOM file not found: {sbom_path}")

        with open(sbom_file, 'r') as f:
            sbom_data = json.load(f)

        components = []

        if self._is_cyclonedx(sbom_data):
            components = self._parse_cyclonedx(sbom_data)
        elif self._is_spdx(sbom_data):
            components = self._parse_spdx(sbom_data)
        else:
            raise ValueError("Unrecognized SBOM format")

        return components

    def _is_cyclonedx(self, data: Dict) -> bool:
        return "bomFormat" in data and data.get("bomFormat") == "CycloneDX"

    def _is_spdx(self, data: Dict) -> bool:
        return "SPDXID" in data or "spdxVersion" in data

    def _parse_cyclonedx(self, data: Dict) -> List[SBOMComponent]:
        """Parse CycloneDX format SBOM"""
        components = []
        component_list = data.get("components", [])

        for comp in component_list:
            name = comp.get("name", "unknown")
            version = comp.get("version", "unknown")
            component_type = comp.get("type", "library")
            license_info = comp.get("licenses", [{}])[0].get("license", {})
            license_name = license_info.get("name", "UNKNOWN") if isinstance(license_info, dict) else str(license_info)
            
            purl = comp.get("purl", "")
            registry = self._extract_registry_from_purl(purl)
            
            hash_value = self._extract_hash(comp)

            components.append(SBOMComponent(
                name=name,
                version=version,
                registry=registry,
                component_type=component_type,
                hash=hash_value,
                license=license_name
            ))

        return components

    def _parse_spdx(self, data: Dict) -> List[SBOMComponent]:
        """Parse SPDX format SBOM"""
        components = []
        packages = data.get("packages", [])

        for pkg in packages:
            name = pkg.get("name", "unknown")
            version = pkg.get("versionInfo", "unknown")
            component_type = "library"
            license_list = pkg.get("licenseDeclared", "UNKNOWN")
            
            external_refs = pkg.get("externalRefs", [])
            registry = "unknown"
            for ext_ref in external_refs:
                if ext_ref.get("referenceCategory") == "PACKAGE-MANAGER":
                    ref_type = ext_ref.get("referenceType", "")
                    if "npm" in ref_type.lower():
                        registry = "npm"
                    elif "pypi" in ref_type.lower():
                        registry = "pypi"
                    elif "cargo" in ref_type.lower():
                        registry = "crates.io"

            hash_value = ""
            checksums = pkg.get("checksums", [])
            if checksums:
                hash_value = checksums[0].get("checksumValue", "")

            components.append(SBOMComponent(
                name=name,
                version=version,
                registry=registry,
                component_type=component_type,
                hash=hash_value,
                license=license_list
            ))

        return components

    def _extract_registry_from_purl(self, purl: str) -> str:
        """Extract registry type from Package URL"""
        if not purl:
            return "unknown"
        if purl.startswith("pkg:npm/"):
            return "npm"
        elif purl.startswith("pkg:pypi/"):
            return "pypi"
        elif purl.startswith("pkg:cargo/"):
            return "crates.io"
        else:
            return "unknown"

    def _extract_hash(self, component: Dict) -> str:
        """Extract hash from component"""
        hashes = component.get("hashes", [])
        if hashes:
            return hashes[0].get("value", "")
        return ""


class PackageMatcher:
    """Match flagged packages against SBOM components"""

    def find_matches(self, flagged_packages: List[FlaggedPackage], 
                    sbom_components: List[SBOMComponent]) -> Dict[FlaggedPackage, List[SBOMComponent]]:
        """Find SBOM components matching flagged packages"""
        matches = {}

        for flagged in flagged_packages:
            matched_components = self._match_package(flagged, sbom_components)
            if matched_components:
                matches[flagged] = matched_components

        return matches

    def _match_package(self, flagged: FlaggedPackage, 
                      sbom_components: List[SBOMComponent]) -> List[SBOMComponent]:
        """Find SBOM components matching a flagged package"""
        matched = []

        for component in sbom_components:
            if self._is_match(flagged, component):
                matched.append(component)

        return matched

    def _is_match(self, flagged: FlaggedPackage, component: SBOMComponent) -> bool:
        """Determine if a component matches a flagged package"""
        name_match = self._normalize_name(flagged.name) == self._normalize_name(component.name)
        registry_match = flagged.registry == component.registry or component.registry == "unknown"
        version_match = self._version_matches(flagged.version, component.version)

        return name_match and registry_match and version_match

    def _normalize_name(self, name: str) -> str:
        """Normalize package name for comparison"""
        return name.lower().replace("_", "-").replace(" ", "")

    def _version_matches(self, flagged_version: str, component_version: str) -> bool:
        """Check if versions match"""
        if flagged_version == component_version:
            return True
        
        flagged_base = flagged_version.split("+")[0]
        component_base = component_version.split("+")[0]
        return flagged_base == component_base


class CVEAdvisoryGenerator:
    """Generate CVE advisories for matched threats"""

    def __init__(self):
        self.advisory_counter = 0

    def generate_advisories(self, matches: Dict[FlaggedPackage, List[SBOMComponent]],
                           flagged_packages: List[FlaggedPackage]) -> List[CVEAdvisory]:
        """Generate CVE advisories for flagged packages"""
        advisories = []

        for flagged, components in matches.items():
            advisory = self._create_advisory(flagged, components)
            advisories.append(advisory)

        for flagged in flagged_packages:
            if flagged not in matches:
                advisory = self._create_advisory(flagged, [])
                advisories.append(advisory)

        return advisories

    def _create_advisory(self, flagged: FlaggedPackage, 
                        components: List[SBOMComponent]) -> CVEAdvisory:
        """Create a CVE advisory for a flagged package"""
        self.advisory_counter += 1
        advisory_id = f"SWARM-CVE-{datetime.now().year}-{self.advisory_counter:05d}"
        cve_id = self._generate_cve_id(flagged)
        
        severity = self._determine_severity(flagged)
        description = self._generate_description(flagged)
        recommendations = self._generate_recommendations(flagged, severity)
        related_components = [f"{c.name}@{c.version}" for c in components]

        return CVEAdvisory(
            advisory_id=advisory_id,
            cve_id=cve_id,
            package_name=flagged.name,
            affected_versions=[flagged.version],
            severity=severity,
            description=description,
            recommendations=recommendations,
            related_sbom_components=related_components,
            generated_at=datetime.now().isoformat()
        )

    def _generate_cve_id(self, flagged: FlaggedPackage) -> str:
        """Generate a CVE-style ID for the threat"""
        year = datetime.now().year
        hash_input = f"{flagged.name}{flagged.version}{flagged.threat_type.value}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:4].upper()
        return f"CVE-{year}-{hash_value}"

    def _determine_severity(self, flagged: FlaggedPackage) -> SeverityLevel:
        """Determine severity based on threat type and confidence"""
        if flagged.threat_type == ThreatType.KNOWN_MALWARE:
            return SeverityLevel.CRITICAL
        elif flagged.threat_type == ThreatType.POST_PUBLISH_INJECTION:
            if flagged.confidence >= 0.9:
                return SeverityLevel.CRITICAL
            elif flagged.confidence >= 0.7:
                return SeverityLevel.HIGH
            else:
                return SeverityLevel.MEDIUM
        elif flagged.threat_type == ThreatType.DEPENDENCY_CONFUSION:
            return SeverityLevel.HIGH
        elif flagged.threat_type == ThreatType.TYPOSQUATTING:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _generate_description(self, flagged: FlaggedPackage) -> str:
        """Generate threat description"""
        threat_descriptions = {
            ThreatType.TYPOSQUATTING: f"Package '{flagged.name}' is suspected of typosquatting. Similar to legitimate package names, this could lead to accidental installation of malicious code.",
            ThreatType.DEPENDENCY_CONFUSION: f"Package '{flagged.name}' version {flagged.version} detected as potential dependency confusion attack targeting private namespace.",
            ThreatType.POST_PUBLISH_INJECTION: f"Package '{flagged.name}' version {flagged.version} shows signs of post-publish code injection similar to XZ backdoor patterns.",
            ThreatType.KNOWN_MALWARE: f"Package '{flagged.name}' version {flagged.version} matches known malware signatures in threat intelligence database.",
            ThreatType.SUSPICIOUS_ACTIVITY: f"Package '{flagged.name}' version {flagged.version} exhibits suspicious activity patterns."
        }
        return threat_descriptions.get(flagged.threat_type, "Unknown threat detected")

    def _generate_recommendations(self, flagged: FlaggedPackage, 
                                 severity: SeverityLevel) -> List[str]:
        """Generate remediation recommendations"""
        base_recommendations = [
            f"Do NOT install or use package '{flagged.name}' version {flagged.version}",
            "Review all dependencies in package-lock.json or requirements.txt for this package",
            "Check git history for any unexpected commits or changes related to this package"
        ]

        if severity == SeverityLevel.CRITICAL:
            base_recommendations.extend([
                "Immediately audit all systems that may have installed this package",
                "Rotate all credentials and secrets that may have been exposed",
                "Check for unauthorized access logs and suspicious activity",
                "Consider security incident response procedure"
            ])
        elif severity == SeverityLevel.HIGH:
            base_recommendations.extend([
                "Audit systems for package installation within 7 days",
                "Plan immediate update to safe version",
                "Monitor logs for suspicious activity"
            ])
        else:
            base_recommendations.extend([
                "Update to latest verified version when available",
                "Monitor package repository for updates"
            ])

        return base_recommendations


class ThreatDetector:
    """Detect threats in package metadata and behavior"""

    def detect_threats(self, package_feed: List[Dict]) -> List[FlaggedPackage]:
        """Detect threats from package feed"""
        flagged = []

        for package_data in package_feed:
            detected = self._analyze_package(package_data)
            if detected:
                flagged.extend(detected)

        return flagged

    def _analyze_package(self, package_data: Dict) -> List[FlaggedPackage]:
        """Analyze single package for threats"""
        threats = []

        name = package_data.get("name", "")
        version = package_data.get("version", "")
        registry = package_data.get("registry", "unknown")
        metadata = package_data.get("metadata", {})

        typo_threat = self._detect_typosquatting(name, metadata)
        if typo_threat:
            threats.append(typo_threat)

        confusion_threat = self._detect_dependency_confusion(name
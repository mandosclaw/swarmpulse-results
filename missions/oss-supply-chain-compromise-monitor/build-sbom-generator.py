#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build SBOM generator
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-28T22:05:21.726Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build SBOM generator
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024

SBOM (Software Bill of Materials) generator for open-source package analysis.
Generates comprehensive SBOMs in CycloneDX and SPDX formats with dependency trees,
license information, and supply chain metadata.
"""

import json
import argparse
import sys
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from urllib.parse import urlparse
import subprocess
import tempfile
import xml.etree.ElementTree as ET


@dataclass
class License:
    """License information"""
    name: str
    spdx_id: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Vulnerability:
    """Vulnerability information"""
    id: str
    description: str
    severity: str
    cwe: Optional[str] = None
    cvss_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Component:
    """Software component in the SBOM"""
    name: str
    version: str
    component_type: str = "library"
    purl: Optional[str] = None
    licenses: List[License] = field(default_factory=list)
    supplier: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    description: Optional[str] = None
    hashes: Dict[str, str] = field(default_factory=dict)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    scope: str = "required"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "version": self.version,
            "type": self.component_type,
            "scope": self.scope,
        }
        if self.purl:
            result["purl"] = self.purl
        if self.supplier:
            result["supplier"] = self.supplier
        if self.homepage:
            result["homepage"] = self.homepage
        if self.repository:
            result["repository"] = self.repository
        if self.description:
            result["description"] = self.description
        if self.hashes:
            result["hashes"] = self.hashes
        if self.licenses:
            result["licenses"] = [lic.to_dict() for lic in self.licenses]
        if self.vulnerabilities:
            result["vulnerabilities"] = [v.to_dict() for v in self.vulnerabilities]
        if self.dependencies:
            result["dependencies"] = self.dependencies
        return result


@dataclass
class SBOM:
    """Software Bill of Materials"""
    format: str
    spec_version: str
    version: int
    serial_number: str
    created: str
    tools: List[Dict[str, str]]
    components: List[Component] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bomFormat": self.format,
            "specVersion": self.spec_version,
            "version": self.version,
            "serialNumber": self.serial_number,
            "metadata": {
                "timestamp": self.created,
                "tools": self.tools,
                **self.metadata,
            },
            "components": [c.to_dict() for c in self.components],
        }


class SBOMGenerator:
    """Generates Software Bill of Materials for supply chain analysis"""

    def __init__(self, format_type: str = "cyclonedx"):
        self.format_type = format_type.lower()
        self.components: Dict[str, Component] = {}
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)

    def add_component(
        self,
        name: str,
        version: str,
        component_type: str = "library",
        purl: Optional[str] = None,
        licenses: Optional[List[License]] = None,
        supplier: Optional[str] = None,
        homepage: Optional[str] = None,
        repository: Optional[str] = None,
        description: Optional[str] = None,
        hashes: Optional[Dict[str, str]] = None,
    ) -> Component:
        """Add component to SBOM"""
        key = f"{name}@{version}"
        component = Component(
            name=name,
            version=version,
            component_type=component_type,
            purl=purl or self._generate_purl(name, version),
            licenses=licenses or [],
            supplier=supplier,
            homepage=homepage,
            repository=repository,
            description=description,
            hashes=hashes or {},
        )
        self.components[key] = component
        return component

    def add_dependency(self, parent: str, parent_version: str, child: str, child_version: str) -> None:
        """Add dependency relationship"""
        parent_key = f"{parent}@{parent_version}"
        child_key = f"{child}@{child_version}"
        self.dependency_graph[parent_key].append(child_key)

        if parent_key in self.components:
            self.components[parent_key].dependencies.append(child_key)

    def add_vulnerability(
        self,
        component_name: str,
        component_version: str,
        vuln_id: str,
        description: str,
        severity: str,
        cwe: Optional[str] = None,
        cvss_score: Optional[float] = None,
    ) -> None:
        """Add vulnerability to component"""
        key = f"{component_name}@{component_version}"
        if key in self.components:
            vuln = Vulnerability(
                id=vuln_id,
                description=description,
                severity=severity,
                cwe=cwe,
                cvss_score=cvss_score,
            )
            self.components[key].vulnerabilities.append(vuln)

    def add_license(self, component_name: str, component_version: str, license: License) -> None:
        """Add license to component"""
        key = f"{component_name}@{component_version}"
        if key in self.components:
            self.components[key].licenses.append(license)

    def _generate_purl(self, name: str, version: str, package_type: str = "npm") -> str:
        """Generate Package URL (purl)"""
        return f"pkg:{package_type}/{name}@{version}"

    def _calculate_hash(self, content: str, algorithm: str = "sha256") -> str:
        """Calculate content hash"""
        return hashlib.new(algorithm, content.encode()).hexdigest()

    def _generate_serial_number(self) -> str:
        """Generate unique serial number for SBOM"""
        timestamp = datetime.utcnow().isoformat()
        component_hash = self._calculate_hash(
            "".join(sorted(self.components.keys())), "sha1"
        )
        return f"urn:uuid:{component_hash[:8]}-{component_hash[8:12]}-{component_hash[12:16]}-{component_hash[16:20]}-{component_hash[20:32]}"

    def generate_cyclonedx(self, component_name: str = "Application", component_version: str = "1.0.0") -> Dict[str, Any]:
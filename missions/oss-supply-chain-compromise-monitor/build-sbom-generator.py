#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build SBOM generator
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-29T13:21:42.374Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────


"""
SBOM Generator - Open Source Supply Chain Compromise Monitor
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex (SwarmPulse)
Date: 2025-01-15
"""

import json
import hashlib
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import subprocess
import re
from collections import defaultdict
import xml.etree.ElementTree as ET

class SBOMGenerator:
    """Generate Software Bill of Materials for supply chain monitoring."""
    
    SUPPORTED_FORMATS = ['json', 'xml', 'cyclonedx', 'spdx']
    
    def __init__(self, project_path: str, format_type: str = 'json'):
        self.project_path = Path(project_path)
        self.format_type = format_type.lower()
        self.dependencies: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {
            'generated_at': datetime.utcnow().isoformat(),
            'format': format_type,
            'project_path': str(self.project_path)
        }
        
        if self.format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def analyze_python_requirements(self) -> None:
        """Analyze Python requirements.txt and setup.py files."""
        requirements_files = [
            self.project_path / 'requirements.txt',
            self.project_path / 'requirements-dev.txt',
            self.project_path / 'setup.py',
            self.project_path / 'pyproject.toml',
            self.project_path / 'Pipfile',
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                self._parse_requirements_file(req_file)
    
    def _parse_requirements_file(self, file_path: Path) -> None:
        """Parse various Python requirement file formats."""
        try:
            content = file_path.read_text()
            
            if file_path.name == 'setup.py':
                self._parse_setup_py(content)
            elif file_path.name == 'pyproject.toml':
                self._parse_pyproject_toml(content)
            elif file_path.name == 'Pipfile':
                self._parse_pipfile(content)
            else:
                self._parse_requirements_txt(content)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
    
    def _parse_requirements_txt(self, content: str) -> None:
        """Parse requirements.txt format."""
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(r'^([a-zA-Z0-9_\-]+)\s*([=!<>~;].*)?$', line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2) or 'unspecified'
                
                self._add_dependency(
                    name=package_name,
                    version=version_spec,
                    source='requirements.txt',
                    source_type='python_package'
                )
    
    def _parse_setup_py(self, content: str) -> None:
        """Parse setup.py install_requires."""
        install_requires_match = re.search(
            r'install_requires\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )
        
        if install_requires_match:
            requires_str = install_requires_match.group(1)
            packages = re.findall(r"['\"]([^'\"]+)['\"]", requires_str)
            
            for package in packages:
                match = re.match(r'^([a-zA-Z0-9_\-]+)\s*([=!<>~;].*)?$', package)
                if match:
                    self._add_dependency(
                        name=match.group(1),
                        version=match.group(2) or 'unspecified',
                        source='setup.py',
                        source_type='python_package'
                    )
    
    def _parse_pyproject_toml(self, content: str) -> None:
        """Parse pyproject.toml dependencies."""
        dependencies_match = re.search(
            r'\[project\].*?dependencies\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )
        
        if dependencies_match:
            deps_str = dependencies_match.group(1)
            packages = re.findall(r"['\"]([^'\"]+)['\"]", deps_str)
            
            for package in packages:
                match = re.match(r'^([a-zA-Z0-9_\-]+)\s*([=!<>~;].*)?$', package)
                if match:
                    self._add_dependency(
                        name=match.group(1),
                        version=match.group(2) or 'unspecified',
                        source='pyproject.toml',
                        source_type='python_package'
                    )
    
    def _parse_pipfile(self, content: str) -> None:
        """Parse Pipfile dependencies."""
        packages_match = re.search(r'\[packages\](.*?)(?:\[|$)', content, re.DOTALL)
        
        if packages_match:
            packages_str = packages_match.group(1)
            package_lines = re.findall(r'(\w+)\s*=\s*["\']?([^"\'\n]+)', packages_str)
            
            for package_name, version in package_lines:
                self._add_dependency(
                    name=package_name,
                    version=version.strip(),
                    source='Pipfile',
                    source_type='python_package'
                )
    
    def analyze_nodejs_dependencies(self) -> None:
        """Analyze package.json for Node.js dependencies."""
        package_json = self.project_path / 'package.json'
        
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())
                
                for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                    if dep_type in content:
                        for package_name, version in content[dep_type].items():
                            self._add_dependency(
                                name=package_name,
                                version=version,
                                source='package.json',
                                source_type='npm_package'
                            )
            except Exception as e:
                print(f"Warning: Could not parse package.json: {e}", file=sys.stderr)
    
    def analyze_go_dependencies(self) -> None:
        """Analyze go.mod for Go dependencies."""
        go_mod = self.project_path / 'go.mod'
        
        if go_mod.exists():
            try:
                content = go_mod.read_text()
                require_section = re.search(r'require\s*\((.*?)\)', content, re.DOTALL)
                
                if require_section:
                    lines = require_section.group(1).strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('//'):
                            continue
                        
                        match = re.match(r'^([^\s]+)\s+([^\s]+)', line)
                        if match:
                            self._add_dependency(
                                name=match.group(1),
                                version=match.group(2),
                                source='go.mod',
                                source_type='go_package'
                            )
            except Exception as e:
                print(f"Warning: Could not parse go.mod: {e}", file=sys.stderr)
    
    def analyze_rust_dependencies(self) -> None:
        """Analyze Cargo.toml for Rust dependencies."""
        cargo_toml = self.project_path / 'Cargo.toml'
        
        if cargo_toml.exists():
            try:
                content = cargo_toml.read_text()
                
                for section in ['dependencies', 'dev-dependencies']:
                    pattern = rf'\[{section}\](.*?)(?:\[|$)'
                    match = re.search(pattern, content, re.DOTALL)
                    
                    if match:
                        deps_str = match.group(1)
                        dep_lines = re.findall(r'(\w+)\s*=\s*["\{{]?([^"\}}\n]+)', deps_str)
                        
                        for package_name, version in dep_lines:
                            self._add_dependency(
                                name=package_name,
                                version=version.strip().strip('"'),
                                source='Cargo.toml',
                                source_type='rust_crate'
                            )
            except Exception as e:
                print(f"Warning: Could not parse Cargo.toml: {e}", file=sys.stderr)
    
    def _add_dependency(self, name: str, version: str, source: str, source_type: str) -> None:
        """Add a dependency to the SBOM."""
        if name not in self.dependencies:
            self.dependencies[name] = {
                'name': name,
                'version': version,
                'source': source,
                'source_type': source_type,
                'hash': self._generate_hash(f"{name}:{version}"),
                'risk_indicators': self._check_risk_indicators(name, version)
            }
    
    def _generate_hash(self, data: str) -> str:
        """Generate SHA256 hash for dependency."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _check_risk_indicators(self, name: str, version: str) -> Dict[str, Any]:
        """Check for supply chain risk indicators."""
        indicators = {
            'typosquatting_risk': self._assess_typosquatting(name),
            'version_anomaly': self._assess_version_anomaly(version),
            'common_attacks': self._check_common_attack_patterns(name, version)
        }
        return indicators
    
    def _assess_typosquatting(self, package_name: str) -> bool:
        """Detect potential typosquatting patterns."""
        suspicious_patterns = [
            r'^[a-z]*l[a-z]*$',
            r'.*[oO][lI].*',
            r'.*1[lI].*',
        ]
        
        common_packages = {
            'django', 'flask', 'requests', 'numpy', 'pandas',
            'tensorflow', 'pytorch', 'fastapi', 'celery', 'redis'
        }
        
        for pattern in suspicious_patterns:
            if re.match(pattern, package_name.lower()):
                for common in common_packages:
                    if common in package_name.lower() and common != package_name.lower():
                        return True
        
        return False
    
    def _assess_version_anomaly(self, version: str) -> bool:
        """Check for unusual version patterns."""
        if not version or version == 'unspecified':
            return True
        
        if re.match(r'^0\.0\.[0-9]+$', version):
            return True
        
        if re.match(r'^.*\+[a-z0-9]+$', version):
            return True
        
        return False
    
    def _check_common_attack_patterns(self, name: str, version: str) -> List[str]:
        """Check for known attack patterns."""
        patterns = []
        
        if len(name) > 50:
            patterns.append('unusually_long_name')
        
        if name.count('_') > 3:
            patterns.append('excessive_underscores')
        
        if re.search(r'[^\w\-]', name):
            patterns.append('suspicious_characters')
        
        if version.startswith('0.0.'):
            patterns.append('pre_release_pattern')
        
        return patterns
    
    def generate_sbom_json(self) -> Dict[str, Any]:
        """Generate SBOM in JSON format."""
        return {
            'sbom_version': '1.0',
            'metadata': self.metadata,
            'dependencies': list(self.dependencies.values()),
            'summary': {
                'total_dependencies': len(self.dependencies),
                'high_risk_count': sum(
                    1 for dep in self.dependencies.values()
                    if dep['risk_indicators']['typosquatting_risk']
                )
            }
        }
    
    def generate_sbom_xml(self) -> str:
        """Generate SBOM in CycloneDX XML format."""
        root = ET.Element('bom')
        root.set('version', '1')
        root.set('xmlns', 'http://cyclonedx.org/schema/bom/1.2')
        
        metadata_elem = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata_elem, 'timestamp').text = self.metadata['generated_at']
        
        components_elem = ET.SubElement(root, 'components')
        
        for dep in self.dependencies.values():
            component = ET.SubElement(components_elem, 'component')
            component.set('type', 'library')
            
            ET.SubElement(component, 'name').text = dep['name']
            ET.SubElement(component, 'version').text = dep['version']
            ET.SubElement(component, 'purl').text = f"pkg:generic/{dep['name']}@{dep['version']}"
            
            hashes_elem = ET.SubElement(component, 'hashes')
            hash_elem = ET.SubElement(hashes_elem, 'hash')
            hash_elem.set('alg', 'SHA-256')
            hash_elem.text = dep['hash']
        
        return ET.tostring(root, encoding='unicode')
    
    def generate_sbom_cyclonedx(self) -> Dict[str, Any]:
        """Generate SBOM in CycloneDX JSON format."""
        return {
            'bomFormat': 'CycloneDX',
            'specVersion': '1.3',
            'version': 1,
            'metadata': {
                'timestamp': self.metadata['generated_at'],
                'tools': [{
                    'vendor': 'SwarmPulse',
                    'name': 'SBOM-Generator',
                    'version': '1.0'
                }]
            },
            'components': [
                {
                    'type': 'library',
                    'name': dep['name'],
                    'version': dep['version'],
                    'purl': f"pkg:generic/{dep['name']}@{dep['version']}",
                    'hashes': [{
                        'alg': 'SHA-256',
                        'content': dep['hash']
                    }]
                }
                for dep in self.dependencies.values()
            ]
        }
    
    def generate_sbom_spdx(self) -> Dict[str, Any]:
        """Generate SBOM in SPDX format."""
        return {
            'SPDXID': 'SPDXRef-DOCUMENT',
            'spdxVersion': 'SPDX-2.2',
            'creationInfo': {
                'created': self.metadata['generated_at'],
                'creators': ['Tool: SwarmPulse-SBOM-Generator']
            },
            'name': f"SBOM for {self.project_path.name}",
            'packages': [
                {
                    'SPDXID': f"SPDXRef-{dep['name'].replace('-', '_').replace('.', '_')}",
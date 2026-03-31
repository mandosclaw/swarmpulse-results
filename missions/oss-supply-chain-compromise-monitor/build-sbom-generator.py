#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build SBOM generator
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-31T18:52:44.285Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
SBOM (Software Bill of Materials) Generator
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2024
"""

import json
import sys
import argparse
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import urllib.request
import urllib.error


class DependencyParser:
    """Parse various dependency manifest formats."""
    
    @staticmethod
    def parse_requirements_txt(content: str) -> List[Dict[str, Any]]:
        """Parse Python requirements.txt format."""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle different requirement formats
            spec_match = re.match(r'^([a-zA-Z0-9._-]+)\s*([><=!~]+.*)?$', line)
            if spec_match:
                name = spec_match.group(1)
                version_spec = spec_match.group(2) or ""
                
                # Extract version constraint
                version = ""
                constraint = ""
                if version_spec:
                    version_match = re.search(r'(\d+\.\d+[\w.-]*)', version_spec)
                    if version_match:
                        version = version_match.group(1)
                    constraint = version_spec.strip()
                
                deps.append({
                    "name": name,
                    "version": version,
                    "constraint": constraint,
                    "type": "pip"
                })
        return deps
    
    @staticmethod
    def parse_package_json(content: str) -> List[Dict[str, Any]]:
        """Parse Node.js package.json format."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        
        deps = []
        for dep_section in ["dependencies", "devDependencies", "optionalDependencies"]:
            if dep_section in data:
                for name, version_spec in data[dep_section].items():
                    deps.append({
                        "name": name,
                        "version": version_spec,
                        "constraint": version_spec,
                        "type": "npm"
                    })
        return deps
    
    @staticmethod
    def parse_go_mod(content: str) -> List[Dict[str, Any]]:
        """Parse Go module go.mod format."""
        deps = []
        in_require = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('require'):
                in_require = True
                if '(' not in line:
                    # Single line require
                    parts = line.split()
                    if len(parts) >= 3:
                        deps.append({
                            "name": parts[1],
                            "version": parts[2],
                            "constraint": parts[2],
                            "type": "go"
                        })
                    in_require = False
                continue
            
            if in_require:
                if line == ')':
                    in_require = False
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    deps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "constraint": parts[1],
                        "type": "go"
                    })
        
        return deps
    
    @staticmethod
    def parse_gemfile(content: str) -> List[Dict[str, Any]]:
        """Parse Ruby Gemfile format."""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            gem_match = re.match(r"gem\s+['\"]([^'\"]+)['\"]\s*(?:,\s*['\"]([^'\"]+)['\"])?", line)
            if gem_match:
                name = gem_match.group(1)
                version = gem_match.group(2) or ""
                deps.append({
                    "name": name,
                    "version": version,
                    "constraint": version,
                    "type": "rubygems"
                })
        
        return deps


class SBOMGenerator:
    """Generate Software Bill of Materials in SPDX JSON format."""
    
    SPDX_VERSION = "SPDX-2.3"
    SPDX_LICENSE_LIST_VERSION = "3.19"
    
    def __init__(self, project_name: str, project_version: str, project_url: Optional[str] = None):
        self.project_name = project_name
        self.project_version = project_version
        self.project_url = project_url or f"https://example.com/{project_name}"
        self.dependencies: List[Dict[str, Any]] = []
        self.components: List[Dict[str, Any]] = []
    
    def add_dependency(self, dep: Dict[str, Any]) -> None:
        """Add a dependency to the SBOM."""
        self.dependencies.append(dep)
    
    def add_dependencies(self, deps: List[Dict[str, Any]]) -> None:
        """Add multiple dependencies."""
        self.dependencies.extend(deps)
    
    def _generate_component_id(self, name: str, version: str) -> str:
        """Generate unique component ID."""
        identifier = f"{name}@{version}".replace('/', '-').lower()
        return identifier
    
    def _generate_spdx_id(self, name: str, version: str) -> str:
        """Generate SPDX identifier."""
        component_id = self._generate_component_id(name, version)
        return f"SPDXRef-Package-{component_id}"
    
    def _build_components(self) -> None:
        """Build component list from dependencies."""
        self.components = []
        for dep in self.dependencies:
            component = {
                "SPDXID": self._generate_spdx_id(dep["name"], dep["version"]),
                "name": dep["name"],
                "versionInfo": dep.get("version", "UNKNOWN"),
                "downloadLocation": f"NOASSERTION",
                "filesAnalyzed": False,
                "type": "Library",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": self._build_purl(dep)
                    }
                ],
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION"
            }
            self.components.append(component)
    
    def _build_purl(self, dep: Dict[str, Any]) -> str:
        """Build Package URL (purl) for component."""
        pkg_type = dep.get("type", "generic")
        name = dep["name"]
        version = dep.get("version", "")
        
        # Normalize package type to purl format
        purl_type_map = {
            "pip": "pypi",
            "npm": "npm",
            "go": "golang",
            "rubygems": "gem",
            "generic": "generic"
        }
        
        purl_type = purl_type_map.get(pkg_type, pkg_type)
        
        if version:
            return f"pkg:{purl_type}/{name}@{version}"
        return f"pkg:{purl_type}/{name}"
    
    def _generate_document_namespace(self) -> str:
        """Generate unique document namespace."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        content = f"{self.project_name}{self.project_version}{timestamp}"
        doc_hash = hashlib.sha1(content.encode()).hexdigest()
        return f"https://sbom.example.com/{self.project_name}/{doc_hash}"
    
    def generate(self) -> Dict[str, Any]:
        """Generate complete SBOM in SPDX JSON format."""
        self._build_components()
        
        now = datetime.utcnow().isoformat() + "Z"
        
        sbom = {
            "spdxVersion": self.SPDX_VERSION,
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"{self.project_name} SBOM",
            "documentNamespace": self._generate_document_namespace(),
            "documentDescribes": [f"SPDXRef-Package-{self._generate_component_id(self.project_name, self.project_version)}"],
            "creationInfo": {
                "created": now,
                "creators": ["Tool: sbom-generator"],
                "licenseListVersion": self.SPDX_LICENSE_LIST_VERSION
            },
            "packages": [
                {
                    "SPDXID": f"SPDXRef-Package-{self._generate_component_id(self.project_name, self.project_version)}",
                    "name": self.project_name,
                    "versionInfo": self.project_version,
                    "downloadLocation": self.project_url,
                    "filesAnalyzed": False,
                    "licenseConcluded": "NOASSERTION",
                    "licenseDeclared": "NOASSERTION",
                    "copyrightText": "NOASSERTION"
                }
            ] + self.components,
            "relationships": self._generate_relationships()
        }
        
        return sbom
    
    def _generate_relationships(self) -> List[Dict[str, str]]:
        """Generate SPDX relationships."""
        relationships = [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": f"SPDXRef-Package-{self._generate_component_id(self.project_name, self.project_version)}"
            }
        ]
        
        project_spdx_id = f"SPDXRef-Package-{self._generate_component_id(self.project_name, self.project_version)}"
        
        for dep in self.dependencies:
            dep_spdx_id = self._generate_spdx_id(dep["name"], dep["version"])
            relationships.append({
                "spdxElementId": project_spdx_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dep_spdx_id
            })
        
        return relationships


class ManifestDetector:
    """Detect and parse various manifest file formats."""
    
    MANIFEST_PATTERNS = {
        "requirements.txt": r".*requirements.*\.txt$",
        "package.json": r"^package\.json$",
        "go.mod": r"^go\.mod$",
        "Gemfile": r"^Gemfile$",
        "setup.py": r"^setup\.py$",
        "pyproject.toml": r"^pyproject\.toml$"
    }
    
    @staticmethod
    def detect_manifest_type(file_path: str) -> Optional[str]:
        """Detect manifest file type from path."""
        file_name = Path(file_path).name
        
        for manifest_type, pattern in ManifestDetector.MANIFEST_PATTERNS.items():
            if re.match(pattern, file_name):
                return manifest_type
        
        return None
    
    @staticmethod
    def parse_manifest(manifest_type: str, content: str) -> List[Dict[str, Any]]:
        """Parse manifest based on detected type."""
        parser = DependencyParser()
        
        if manifest_type == "requirements.txt":
            return parser.parse_requirements_txt(content)
        elif manifest_type == "package.json":
            return parser.parse_package_json(content)
        elif manifest_type == "go.mod":
            return parser.parse_go_mod(content)
        elif manifest_type == "Gemfile":
            return parser.parse_gemfile(content)
        
        return []


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="SBOM (Software Bill of Materials) Generator for OSS Supply Chain Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project myapp --version 1.0.0 --manifest requirements.txt
  %(prog)s --project myapp --version 2.0.0 --manifest package.json --output sbom.json
  %(prog)s --project golang-app --version 1.5.0 --manifest go.mod --output sbom.json --format spdx
        """
    )
    
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name"
    )
    
    parser.add_argument(
        "--version",
        type=str,
        required=True,
        help="Project version"
    )
    
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to dependency manifest file (requirements.txt, package.json, go.mod, Gemfile, etc.)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for SBOM (default: stdout)"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["spdx", "json"],
        default="spdx",
        help="Output format (default: spdx)"
    )
    
    parser.add_argument(
        "--project-url",
        type=str,
        help="Project URL"
    )
    
    parser.add_argument(
        "--include-hashes",
        action="store_true",
        help="Include dependency hashes in output"
    )
    
    return parser


def load_manifest_file(manifest_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Load and detect manifest file type."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        manifest_type = ManifestDetector.detect_manifest_type(manifest_path)
        return manifest_type, content
    except FileNotFoundError:
        print(f"Error: Manifest file not found: {manifest_path}", file=sys.stderr)
        return None, None
    except IOError as e:
        print(f"Error reading manifest file: {e}", file=sys.stderr)
        return None, None


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    generator = SBOMGenerator(
        project_name=args.project,
        project_version=args.version,
        project_url=args.project_url
    )
    
    if args.manifest:
        manifest_type, content = load_manifest_file(args.manifest)
        
        if manifest_type and content:
            print(f"Detected manifest type: {manifest_type}", file=sys.stderr)
            dependencies = ManifestDetector.parse_manifest(manifest_type, content)
            print(f"Found {len(dependencies)} dependencies", file=sys.stderr)
            
            generator.add_dependencies(dependencies)
        else:
            print("Warning: Could not detect or parse manifest file", file=sys.stderr)
    
    sbom = generator.generate()
    
    output_json = json.dumps(sbom, indent=2)
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"SBOM written to: {args.output}", file=sys.stderr)
        except IOError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_json)


if __name__ == "__main__":
    # Demo with sample data
    demo_mode = len(sys.argv) == 1
    
    if demo_mode:
        print("=== SBOM Generator Demo ===\n", file=sys.stderr)
        
        # Create sample Python project SBOM
        py_generator = SBOMGenerator(
            project_name="example-api",
            project_version="1.2.3",
            project_url="https://github.com/example/example-api"
        )
        
        sample_deps = [
            {"name": "requests", "version": "2.28.1", "type": "pip"},
            {"name": "flask", "version": "2.2.0", "type": "pip"},
            {"name": "sqlalchemy", "version": "1.4.40", "type": "pip"},
            {"name": "python-dotenv", "version": "0.20.0", "type": "pip"},
        ]
        
        py_generator.add_dependencies(sample_deps)
        py_sbom = py_generator.generate()
        
        print("Generated Python Project SBOM:")
        print(json.dumps(py_sbom, indent=2))
        print("\n" + "="*50 + "\n", file=sys.stderr)
        
        # Create sample Node.js project SBOM
        node_generator = SBOMGenerator(
            project_name="web-app",
            project_version="2.0.0",
            project_url="https://github.com/example/web-app"
        )
        
        sample_node_deps = [
            {"name": "express", "version": "4.18.2", "type": "npm"},
            {"name": "react", "version": "18.2.0", "type": "npm"},
            {"name": "webpack", "version": "5.75.0", "type": "npm"},
        ]
        
        node_generator.add_dependencies(sample_node_deps)
        node_sbom = node_generator.generate()
        
        print("Generated Node.js Project SBOM:")
        print(json.dumps(node_sbom, indent=2))
    else:
        main()
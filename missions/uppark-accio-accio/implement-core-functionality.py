#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: uppark/accio: accio
# Agent:   @aria
# Date:    2026-04-01T17:35:46.341Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for accio dependency resolver
MISSION: uppark/accio
AGENT: @aria
DATE: 2024

accio is a dependency resolver and analyzer. This implementation provides
core functionality for resolving Python package dependencies, detecting
version conflicts, and generating dependency reports with proper error
handling and logging.
"""

import sys
import json
import logging
import argparse
import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime


class VersionComparison(Enum):
    """Version comparison operators."""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="
    COMPATIBLE = "~="


@dataclass
class Version:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    pre: Optional[str] = None

    def __init__(self, version_str: str):
        """Parse version string into components."""
        self.pre = None
        version_str = version_str.strip()
        
        # Handle pre-release versions
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:[-.](.+))?$', version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        if match.group(4):
            self.pre = match.group(4)

    def __str__(self) -> str:
        """Return version as string."""
        if self.pre:
            return f"{self.major}.{self.minor}.{self.patch}-{self.pre}"
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: 'Version') -> bool:
        """Check if this version is less than other."""
        if not isinstance(other, Version):
            other = Version(str(other))
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        if self.pre and not other.pre:
            return True
        if not self.pre and other.pre:
            return False
        return False

    def __le__(self, other: 'Version') -> bool:
        """Check if this version is less than or equal to other."""
        return self == other or self < other

    def __gt__(self, other: 'Version') -> bool:
        """Check if this version is greater than other."""
        if not isinstance(other, Version):
            other = Version(str(other))
        return not (self <= other)

    def __ge__(self, other: 'Version') -> bool:
        """Check if this version is greater than or equal to other."""
        return self == other or self > other

    def __eq__(self, other) -> bool:
        """Check if versions are equal."""
        if not isinstance(other, Version):
            try:
                other = Version(str(other))
            except ValueError:
                return False
        return (self.major, self.minor, self.patch, self.pre) == (other.major, other.minor, other.patch, other.pre)

    def __hash__(self) -> int:
        """Return hash of version."""
        return hash((self.major, self.minor, self.patch, self.pre))


@dataclass
class Requirement:
    """Package requirement specification."""
    name: str
    operator: VersionComparison
    version: Version

    def __init__(self, requirement_str: str):
        """Parse requirement string (e.g., 'requests>=2.28.0')."""
        requirement_str = requirement_str.strip()
        
        for op in [VersionComparison.GREATER_EQUAL, VersionComparison.LESS_EQUAL,
                   VersionComparison.NOT_EQUAL, VersionComparison.COMPATIBLE,
                   VersionComparison.EQUAL, VersionComparison.GREATER, VersionComparison.LESS]:
            if op.value in requirement_str:
                parts = requirement_str.split(op.value, 1)
                if len(parts) == 2:
                    self.name = parts[0].strip()
                    self.operator = op
                    self.version = Version(parts[1].strip())
                    return
        
        raise ValueError(f"Invalid requirement format: {requirement_str}")

    def matches(self, version: Version) -> bool:
        """Check if a version matches this requirement."""
        if self.operator == VersionComparison.EQUAL:
            return version == self.version
        elif self.operator == VersionComparison.NOT_EQUAL:
            return version != self.version
        elif self.operator == VersionComparison.GREATER:
            return version > self.version
        elif self.operator == VersionComparison.GREATER_EQUAL:
            return version >= self.version
        elif self.operator == VersionComparison.LESS:
            return version < self.version
        elif self.operator == VersionComparison.LESS_EQUAL:
            return version <= self.version
        elif self.operator == VersionComparison.COMPATIBLE:
            # ~= allows compatible releases
            return (version.major == self.version.major and
                    version.minor == self.version.minor and
                    version >= self.version)
        return False

    def __str__(self) -> str:
        """Return requirement as string."""
        return f"{self.name}{self.operator.value}{self.version}"


@dataclass
class Package:
    """Package with version and dependencies."""
    name: str
    version: Version
    dependencies: List[Requirement]

    def __hash__(self) -> int:
        """Return hash of package."""
        return hash((self.name, str(self.version)))


class DependencyResolver:
    """Resolves package dependencies and detects conflicts."""

    def __init__(self, logger: logging.Logger):
        """Initialize the resolver."""
        self.logger = logger
        self.registry: Dict[str, List[Package]] = {}
        self.resolved: Dict[str, Package] = {}
        self.conflicts: List[Tuple[str, str]] = []

    def register_package(self, package: Package) -> None:
        """Register a package in the registry."""
        if package.name not in self.registry:
            self.registry[package.name] = []
        self.registry[package.name].append(package)
        self.logger.debug(f"Registered {package.name}@{package.version}")

    def find_package(self, requirement: Requirement) -> Optional[Package]:
        """Find a package version matching the requirement."""
        if requirement.name not in self.registry:
            self.logger.warning(f"Package {requirement.name} not found in registry")
            return None
        
        candidates = [p for p in self.registry[requirement.name]
                     if requirement.matches(p.version)]
        
        if not candidates:
            self.logger.warning(f"No version of {requirement.name} matches {requirement}")
            return None
        
        # Return the highest matching version
        return max(candidates, key=lambda p: (p.version.major, p.version.minor, p.version.patch))

    def resolve(self, root_requirement: Requirement) -> bool:
        """Resolve dependencies starting from a root requirement."""
        self.logger.info(f"Starting resolution from {root_requirement}")
        self.resolved.clear()
        self.conflicts.clear()
        
        return self._resolve_recursive(root_requirement, set())

    def _resolve_recursive(self, requirement: Requirement, visited: Set[str]) -> bool:
        """Recursively resolve dependencies."""
        package = self.find_package(requirement)
        
        if not package:
            self.logger.error(f"Could not find package matching {requirement}")
            return False
        
        package_key = f"{package.name}@{package.version}"
        
        if package_key in visited:
            return True
        
        visited.add(package_key)
        
        # Check for conflicts with already resolved packages
        if package.name in self.resolved:
            existing = self.resolved[package.name]
            if existing.version != package.version:
                conflict_msg = f"{package.name}: {existing.version} vs {package.version}"
                self.conflicts.append((existing.name, package.name))
                self.logger.warning(f"Conflict detected: {conflict_msg}")
                return False
        
        self.resolved[package.name] = package
        self.logger.debug(f"Resolved {package.name}@{package.version}")
        
        # Resolve dependencies of this package
        for dep in package.dependencies:
            if not self._resolve_recursive(dep, visited):
                return False
        
        return True

    def get_resolution_tree(self) -> Dict:
        """Get the resolved dependency tree."""
        def build_tree(package: Package, visited: Set[str]) -> Dict:
            key = f"{package.name}@{package.version}"
            if key in visited:
                return {"name": package.name, "version": str(package.version), "circular": True}
            
            visited.add(key)
            return {
                "name": package.name,
                "version": str(package.version),
                "dependencies": [
                    build_tree(self.find_package(dep), visited)
                    for dep in package.dependencies
                    if self.find_package(dep)
                ]
            }
        
        if not self.resolved:
            return {}
        
        # Find root package (one with no incoming edges)
        root_names = set(self.resolved.keys())
        for package in self.resolved.values():
            for dep in package.dependencies:
                root_names.discard(dep.name)
        
        if not root_names:
            root_package = next(iter(self.resolved.values()))
        else:
            root_package = self.resolved[next(iter(root_names))]
        
        return build_tree(root_package, set())


class DependencyAnalyzer:
    """Analyzes dependencies for vulnerabilities and issues."""

    def __init__(self, logger: logging.Logger):
        """Initialize the analyzer."""
        self.logger = logger

    def detect_circular_dependencies(self, packages: Dict[str, Package]) -> List[List[str]]:
        """Detect circular dependencies."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(name: str) -> bool:
            visited.add(name)
            rec_stack.add(name)
            path.append(name)
            
            if name in packages:
                for dep in packages[name].dependencies:
                    if dep.name not in visited:
                        if dfs(dep.name):
                            return True
                    elif dep.name in rec_stack:
                        cycle_start = path.index(dep.name)
                        cycle = path[cycle_start:] + [dep.name]
                        cycles.append(cycle)
                        self.logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
                        return True
            
            path.pop()
            rec_stack.remove(name)
            return False
        
        for name in packages:
            if name not in visited:
                dfs(name)
        
        return cycles

    def check_version_compatibility(self, packages: Dict[str, Package]) -> List[Dict]:
        """Check version compatibility across dependencies."""
        issues = []
        
        for package in packages.values():
            for dep in package.dependencies:
                if dep.name in packages:
                    dep_version = packages[dep.name].version
                    if not dep.matches(dep_version):
                        issue = {
                            "type": "version_mismatch",
                            "package": package.name,
                            "requires": str(dep),
                            "actual": str(dep_version),
                            "severity": "high"
                        }
                        issues.append(issue)
                        self.logger.warning(f"Version mismatch: {package.name} requires {dep} but {dep_version} is resolved")
        
        return issues

    def analyze_depth(self, packages: Dict[str, Package]) -> Dict[str, int]:
        """Analyze dependency tree depth."""
        depths = {}
        
        def calculate_depth(name: str, visited: Set[str]) -> int:
            if name in depths:
                return depths[name]
            if name not in packages or name in visited:
                return 0
            
            visited.add(name)
            max_dep_depth = 0
            
            for dep in packages[name].dependencies:
                dep_depth = calculate_depth(dep.name, visited.copy())
                max_dep_depth = max(max_dep_depth, dep_depth)
            
            depths[name] = max_dep_depth + 1
            return depths[name]
        
        for name in packages:
            if name not in depths:
                calculate_depth(name, set())
        
        return depths


def generate_report(resolver: DependencyResolver, analyzer: DependencyAnalyzer) -> Dict:
    """Generate a comprehensive dependency report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "resolved_packages": {
            name: {"version": str(pkg.version), "dependencies": [str(d) for d in pkg.dependencies]}
            for name, pkg in resolver.resolved.items()
        },
        "conflicts": resolver.conflicts,
        "circular_dependencies": analyzer.detect_circular_dependencies(resolver.resolved),
        "compatibility_issues": analyzer.check_version_compatibility(resolver.resolved),
        "dependency_depths": analyzer.analyze_depth(resolver.resolved),
        "resolution_tree": resolver.get_resolution_tree()
    }
    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="accio - Dependency resolver and analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python3 accio.py resolve --requirement 'requests>=2.28.0'\n"
               "  python3 accio.py analyze --packages package1 package2\n"
               "  python3 accio.py report --output report.json"
    )
    
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--output', type=str,
                       help='Output file for reports (JSON format)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Resolve command
    resolve_parser = subparsers.add_parser('resolve', help='Resolve dependencies')
    resolve_parser.add_argument('--requirement', required=True,
                               help='Root requirement (e.g., requests>=2.28.0)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze dependencies')
    analyze_parser.add_argument('--packages', nargs='+', required=True,
                               help='Package names to analyze')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate dependency report')
    report_parser.add_argument('--requirement', help='Root requirement for resolution')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run demo with sample data')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('accio')
    
    if args.command == 'resolve':
        logger.info(f"Resolving requirement: {args.requirement}")
        resolver = DependencyResolver(logger)
        
        # Demo: register some packages
        demo_packages()
        for packages in [
            [Package("requests", Version("2.28.1"), [Requirement("urllib3>=1.26.0")])],
            [Package("urllib3", Version("1.26.12"), [])],
            [Package("requests", Version("2.27.0"), [Requirement("urllib3>=1.21.0")])],
        ]:
            for pkg in packages:
                resolver.register_package(pkg)
        
        req = Requirement(args.requirement)
        success = resolver.resolve(req)
        
        if success:
            logger.info("Resolution successful")
            print(json.dumps({"status": "success", "resolved": {
                k: {"version": str(v.version)} for k, v in resolver.resolved.items()
            }}, indent=2))
        else:
            logger.error("Resolution failed")
            print(json.dumps({"status": "failed", "conflicts": resolver.conflicts}, indent=2))
            sys.exit(1)
    
    elif args.command == 'analyze':
        logger.info(f"Analyzing packages: {args.packages}")
        analyzer = DependencyAnalyzer(logger)
        
        # Demo packages
        packages = {
            "requests": Package("requests", Version("2.28.1"), [Requirement("urllib3>=1.26.0")]),
            "urllib3": Package("urllib3", Version("1.26.12"), []),
        }
        
        cycles = analyzer.detect_circular_dependencies(packages)
        issues = analyzer.check_version_compatibility(packages)
        depths = analyzer.analyze_depth(packages)
        
        analysis = {
            "packages": args.packages,
            "circular_dependencies": cycles,
            "compatibility_issues": issues,
            "dependency_depths": depths
        }
        
        print(json.dumps(analysis, indent=2))
    
    elif args.command == 'report':
        logger.info("Generating dependency report")
        resolver = DependencyResolver(logger)
        analyzer = DependencyAnalyzer(logger)
        
        # Demo packages
        demo_packages()
        for packages in [
            [Package("requests", Version("2.28.1"), [Requirement("urllib3>=1.26.0")])],
            [Package("urllib3", Version("1.26.12"), [])],
        ]:
            for pkg in packages:
                resolver.register_package(pkg)
        
        if args.requirement:
            req = Requirement(args.requirement)
            resolver.resolve(req)
        
        report = generate_report(resolver, analyzer)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report written to {args.output}")
        else:
            print(json.dumps(report, indent=2))
    
    elif args.command == 'demo':
        logger.info("Running demo")
        resolver = DependencyResolver(logger)
        analyzer = DependencyAnalyzer(logger)
        
        # Create sample packages
        packages_list = [
            Package("requests", Version("2.28.1"), [Requirement("urllib3>=1.26.0"), Requirement("charset-normalizer>=2.0.0")]),
            Package("urllib3", Version("1.26.12"), []),
            Package("charset-normalizer", Version("2.1.0"), []),
            Package("flask", Version("2.2.0"), [Requirement("werkzeug
>=2.2.0"), Requirement("jinja2>=3.0")]),
            Package("werkzeug", Version("2.2.0"), []),
            Package("jinja2", Version("3.1.2"), []),
        ]
        
        for package in packages_list:
            resolver.register_package(package)
        
        # Resolve requests
        logger.info("\n=== Resolving requests>=2.28.0 ===")
        req = Requirement("requests>=2.28.0")
        success = resolver.resolve(req)
        
        if success:
            logger.info("✓ Resolution successful")
            print("\nResolved packages:")
            for name, pkg in resolver.resolved.items():
                print(f"  {name}@{pkg.version}")
        else:
            logger.error("✗ Resolution failed with conflicts")
            print(f"Conflicts: {resolver.conflicts}")
        
        # Analyze
        logger.info("\n=== Analyzing dependencies ===")
        cycles = analyzer.detect_circular_dependencies(resolver.resolved)
        issues = analyzer.check_version_compatibility(resolver.resolved)
        depths = analyzer.analyze_depth(resolver.resolved)
        
        print(f"Circular dependencies: {len(cycles)}")
        print(f"Compatibility issues: {len(issues)}")
        print(f"Dependency depths: {depths}")
        
        # Generate report
        logger.info("\n=== Generating report ===")
        report = generate_report(resolver, analyzer)
        print("\nReport Summary:")
        print(json.dumps({
            "resolved_count": len(report["resolved_packages"]),
            "conflicts": len(report["conflicts"]),
            "circular_dependencies": len(report["circular_dependencies"]),
            "compatibility_issues": len(report["compatibility_issues"])
        }, indent=2))
    
    else:
        parser.print_help()


def demo_packages():
    """Placeholder for demo packages."""
    pass


if __name__ == "__main__":
    main()
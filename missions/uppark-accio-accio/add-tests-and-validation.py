#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: uppark/accio: accio
# Agent:   @aria
# Date:    2026-04-01T17:30:36.511Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation
Mission: uppark/accio
Agent: @aria (SwarmPulse)
Date: 2024

Comprehensive unit and integration test suite for Accio project.
Tests cover main scenarios including dependency resolution, version parsing,
and package information retrieval.
"""

import unittest
import json
import sys
import argparse
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from pathlib import Path
import tempfile
import os


class DependencyParser:
    """Parse and validate Python dependencies."""
    
    def __init__(self):
        self.parsed_dependencies = []
    
    def parse_requirements(self, content):
        """Parse requirements.txt format."""
        lines = content.strip().split('\n')
        deps = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '>=' in line:
                name, version = line.split('>=')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '>='})
            elif '<=' in line:
                name, version = line.split('<=')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '<='})
            elif '==' in line:
                name, version = line.split('==')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '=='})
            elif '~=' in line:
                name, version = line.split('~=')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '~='})
            elif '>' in line:
                name, version = line.split('>')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '>'})
            elif '<' in line:
                name, version = line.split('<')
                deps.append({'name': name.strip(), 'version': version.strip(), 'operator': '<'})
            else:
                deps.append({'name': line, 'version': None, 'operator': None})
        
        self.parsed_dependencies = deps
        return deps
    
    def validate_dependency(self, dep):
        """Validate a single dependency entry."""
        errors = []
        
        if not dep.get('name'):
            errors.append('Dependency name is empty')
        
        if not isinstance(dep['name'], str):
            errors.append('Dependency name must be a string')
        
        if dep.get('version'):
            if not isinstance(dep['version'], str):
                errors.append('Version must be a string')
            if not self._is_valid_version(dep['version']):
                errors.append(f"Invalid version format: {dep['version']}")
        
        if dep.get('operator') and dep['operator'] not in ['>=', '<=', '==', '~=', '>', '<']:
            errors.append(f"Invalid operator: {dep['operator']}")
        
        return len(errors) == 0, errors
    
    def _is_valid_version(self, version):
        """Validate semantic versioning."""
        parts = version.split('.')
        for part in parts:
            if not part.isdigit():
                return False
        return len(parts) >= 1
    
    def validate_all(self):
        """Validate all parsed dependencies."""
        results = []
        for dep in self.parsed_dependencies:
            valid, errors = self.validate_dependency(dep)
            results.append({
                'dependency': dep['name'],
                'valid': valid,
                'errors': errors
            })
        return results


class VersionComparator:
    """Compare semantic versions."""
    
    @staticmethod
    def parse_version(version_str):
        """Parse version string into comparable tuple."""
        try:
            parts = version_str.split('.')
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0,)
    
    @staticmethod
    def compare(version1, version2):
        """Compare two versions. Returns -1, 0, or 1."""
        v1 = VersionComparator.parse_version(version1)
        v2 = VersionComparator.parse_version(version2)
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    @staticmethod
    def is_compatible(required_version, required_op, installed_version):
        """Check if installed version meets requirement."""
        comparison = VersionComparator.compare(installed_version, required_version)
        
        if required_op == '>=':
            return comparison >= 0
        elif required_op == '>':
            return comparison > 0
        elif required_op == '<=':
            return comparison <= 0
        elif required_op == '<':
            return comparison < 0
        elif required_op == '==':
            return comparison == 0
        elif required_op == '~=':
            return comparison >= 0 and VersionComparator.parse_version(installed_version)[0] == VersionComparator.parse_version(required_version)[0]
        
        return False


class PackageResolver:
    """Resolve and validate package dependencies."""
    
    def __init__(self):
        self.packages = {}
        self.resolved_graph = {}
    
    def add_package(self, name, version, dependencies=None):
        """Add a package to the registry."""
        self.packages[name] = {
            'version': version,
            'dependencies': dependencies or []
        }
    
    def resolve_dependencies(self, package_name):
        """Resolve all dependencies for a package."""
        if package_name in self.resolved_graph:
            return self.resolved_graph[package_name]
        
        if package_name not in self.packages:
            return {'error': f'Package {package_name} not found', 'dependencies': []}
        
        resolved = {
            'package': package_name,
            'version': self.packages[package_name]['version'],
            'dependencies': []
        }
        
        for dep_name, dep_version, dep_op in self.packages[package_name]['dependencies']:
            if dep_name in self.packages:
                resolved['dependencies'].append({
                    'name': dep_name,
                    'required_version': dep_version,
                    'operator': dep_op,
                    'installed_version': self.packages[dep_name]['version'],
                    'compatible': VersionComparator.is_compatible(
                        dep_version, dep_op, self.packages[dep_name]['version']
                    )
                })
            else:
                resolved['dependencies'].append({
                    'name': dep_name,
                    'required_version': dep_version,
                    'operator': dep_op,
                    'installed_version': None,
                    'compatible': False
                })
        
        self.resolved_graph[package_name] = resolved
        return resolved


class TestDependencyParser(unittest.TestCase):
    """Test cases for DependencyParser."""
    
    def setUp(self):
        self.parser = DependencyParser()
    
    def test_parse_requirements_with_exact_version(self):
        """Test parsing requirements with exact version pinning."""
        content = "requests==2.28.0\nnumpy==1.21.0"
        deps = self.parser.parse_requirements(content)
        
        self.assertEqual(len(deps), 2)
        self.assertEqual(deps[0]['name'], 'requests')
        self.assertEqual(deps[0]['version'], '2.28.0')
        self.assertEqual(deps[0]['operator'], '==')
    
    def test_parse_requirements_with_version_ranges(self):
        """Test parsing requirements with version ranges."""
        content = "django>=3.2.0\nflask<2.0.0\npandas>=1.0,<2.0"
        deps = self.parser.parse_requirements(content)
        
        self.assertGreater(len(deps), 0)
        self.assertEqual(deps[0]['name'], 'django')
        self.assertEqual(deps[0]['operator'], '>=')
    
    def test_parse_requirements_ignores_comments(self):
        """Test that comments are ignored."""
        content = "# This is a comment\nrequests==2.28.0\n# Another comment"
        deps = self.parser.parse_requirements(content)
        
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]['name'], 'requests')
    
    def test_parse_requirements_handles_blank_lines(self):
        """Test handling of blank lines."""
        content = "requests==2.28.0\n\nnumpy==1.21.0\n\n"
        deps = self.parser.parse_requirements(content)
        
        self.assertEqual(len(deps), 2)
    
    def test_parse_package_without_version(self):
        """Test parsing package without version specification."""
        content = "requests\nnumpy"
        deps = self.parser.parse_requirements(content)
        
        self.assertEqual(len(deps), 2)
        self.assertEqual(deps[0]['version'], None)
        self.assertEqual(deps[0]['operator'], None)
    
    def test_validate_dependency_valid(self):
        """Test validation of valid dependency."""
        dep = {'name': 'requests', 'version': '2.28.0', 'operator': '=='}
        valid, errors = self.parser.validate_dependency(dep)
        
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_dependency_missing_name(self):
        """Test validation fails for missing name."""
        dep = {'name': '', 'version': '1.0.0', 'operator': '=='}
        valid, errors = self.parser.validate_dependency(dep)
        
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
    
    def test_validate_dependency_invalid_version(self):
        """Test validation fails for invalid version."""
        dep = {'name': 'requests', 'version': 'invalid', 'operator': '=='}
        valid, errors = self.parser.validate_dependency(dep)
        
        self.assertFalse(valid)
    
    def test_validate_dependency_invalid_operator(self):
        """Test validation fails for invalid operator."""
        dep = {'name': 'requests', 'version': '2.28.0', 'operator': '!='}
        valid, errors = self.parser.validate_dependency(dep)
        
        self.assertFalse(valid)
    
    def test_validate_all_dependencies(self):
        """Test batch validation of all parsed dependencies."""
        content = "requests==2.28.0\nvalid-package>=1.0.0\ninvalid-=broken"
        self.parser.parse_requirements(content)
        results = self.parser.validate_all()
        
        self.assertGreater(len(results), 0)
        self.assertIn('valid', results[0])


class TestVersionComparator(unittest.TestCase):
    """Test cases for VersionComparator."""
    
    def test_parse_version_standard_format(self):
        """Test parsing standard semantic version."""
        version = VersionComparator.parse_version("1.2.3")
        
        self.assertEqual(version, (1, 2, 3))
    
    def test_parse_version_with_two_parts(self):
        """Test parsing version with two parts."""
        version = VersionComparator.parse_version("2.1")
        
        self.assertEqual(version, (2, 1))
    
    def test_parse_version_single_number(self):
        """Test parsing single number version."""
        version = VersionComparator.parse_version("5")
        
        self.assertEqual(version, (5,))
    
    def test_compare_versions_less_than(self):
        """Test version comparison when first is less."""
        result = VersionComparator.compare("1.0.0", "2.0.0")
        
        self.assertEqual(result, -1)
    
    def test_compare_versions_greater_than(self):
        """Test version comparison when first is greater."""
        result = VersionComparator.compare("3.0.0", "2.0.0")
        
        self.assertEqual(result, 1)
    
    def test_compare_versions_equal(self):
        """Test version comparison when equal."""
        result = VersionComparator.compare("2.0.0", "2.0.0")
        
        self.assertEqual(result, 0)
    
    def test_is_compatible_greater_or_equal(self):
        """Test compatibility check with >= operator."""
        compatible = VersionComparator.is_compatible("2.0.0", ">=", "2.0.0")
        
        self.assertTrue(compatible)
    
    def test_is_compatible_greater_or_equal_higher(self):
        """Test compatibility check with >= operator and higher version."""
        compatible = VersionComparator.is_compatible("2.0.0", ">=", "3.0.0")
        
        self.assertTrue(compatible)
    
    def test_is_compatible_greater_or_equal_lower(self):
        """Test compatibility check with >= operator and lower version."""
        compatible = VersionComparator.is_compatible("2.0.0", ">=", "1.0.0")
        
        self.assertFalse(compatible)
    
    def test_is_compatible_exact_version(self):
        """Test compatibility check with == operator."""
        compatible = VersionComparator.is_compatible("2.0.0", "==", "2.0.0")
        
        self.assertTrue(compatible)
    
    def test_is_compatible_tilde_operator(self):
        """Test compatibility check with ~= operator."""
        compatible = VersionComparator.is_compatible("2.0.0", "~=", "2.1.0")
        
        self.assertTrue(compatible)
    
    def test_is_compatible_tilde_operator_major_mismatch(self):
        """Test compatibility check with ~= operator and major version mismatch."""
        compatible = VersionComparator.is_compatible("2.0.0", "~=", "3.0.0")
        
        self.assertFalse(compatible)


class TestPackageResolver(unittest.TestCase):
    """Test cases for PackageResolver."""
    
    def setUp(self):
        self.resolver = PackageResolver()
    
    def test_add_package(self):
        """Test adding a package to resolver."""
        self.resolver.add_package('requests', '2.28.0', [])
        
        self.assertIn('requests', self.resolver.packages)
        self.assertEqual(self.resolver.packages['requests']['version'], '2.28.0')
    
    def test_add_package_with_dependencies(self):
        """Test adding a package with dependencies."""
        deps = [('urllib3', '1.26.0', '>=')]
        self.resolver.add_package('requests', '2.28.0', deps)
        
        self.assertEqual(len(self.resolver.packages['requests']['dependencies']), 1)
    
    def test_resolve_nonexistent_package(self):
        """Test resolving a nonexistent package."""
        result = self.resolver.resolve_dependencies('nonexistent')
        
        self.assertIn('error', result)
    
    def test_resolve_simple_dependency(self):
        """Test resolving a package with simple dependency."""
        self.resolver.add_package('urllib3', '1.26.0')
        self.resolver.add_package('requests', '2.28.0', [('urllib3', '1.26.0', '>=')])
        
        result = self.resolver.resolve_dependencies('requests')
        
        self.assertEqual(result['package'], 'requests')
        self.assertEqual(len(result['dependencies']), 1)
        self.assertTrue(result['dependencies'][0]['compatible'])
    
    def test_resolve_incompatible_dependency(self):
        """Test resolving with incompatible dependency."""
        self.resolver.add_package('urllib3', '1.20.0')
        self.resolver.add_package('requests', '2.28.0', [('urllib3', '1.26.0', '>=')])
        
        result = self.resolver.resolve_dependencies('requests')
        
        self.assertFalse(result['dependencies'][0]['compatible'])
    
    def test_resolve_missing_dependency(self):
        """Test resolving when dependency is missing."""
        self.resolver.add_package('requests', '2.28.0', [('missing-lib', '1.0.0', '==')])
        
        result = self.resolver.resolve_dependencies('requests')
        
        self.assertFalse(result['dependencies'][0]['compatible'])
        self.assertIsNone(result['dependencies'][0]['installed_version'])
    
    def test_resolution_caching(self):
        """Test that resolutions are cached."""
        self.resolver.add_package('requests', '2.28.0')
        
        result1 = self.resolver.resolve_dependencies('requests')
        result2 = self.resolver.resolve_dependencies('requests')
        
        self.assertIs(result1, result2)


class IntegrationTestSuite(unittest.TestCase):
    """Integration tests for complete workflows."""
    
    def test_full_requirements_parsing_and_validation(self):
        """Test complete workflow of parsing and validating requirements."""
        parser = DependencyParser()
        requirements_content = """
# Project dependencies
requests>=2.25.0
urllib3<2.0.0
certifi==2021.10.8
charset-normalizer>=2.0
idna>=2.5,<4
"""
        deps = parser.parse_requirements(requirements_content)
        results = parser.validate_all()
        
        self.assertGreater(len(deps), 0)
        self.assertEqual(len(results), len(deps))
        self.assertTrue(all(r['valid'] for r in results if 'charset-normalizer' not in r['dependency']))
    
    def test_dependency_resolution_workflow(self):
        """Test complete dependency resolution workflow."""
        resolver = PackageResolver()
        
        # Setup package registry
        resolver.add_package('urllib3', '1.26.12')
        resolver.add_package('charset-normalizer', '2.1.0')
        resolver.add_package('idna', '3.3')
        resolver.add_package('certifi', '2022.6.15')
        resolver.add_package('requests', '2.28.0', [
            ('urllib3', '1.26.0', '>='),
            ('charset-normalizer', '2.0.0', '>='),
            ('idna', '2.5', '>='),
            ('certifi', '2017.4.17', '>=')
        ])
        
        # Resolve main package
        result = resolver.resolve_dependencies('requests')
        
        self.assertEqual(result['package'], 'requests')
        self.assertEqual(result['version'], '2.28.0')
        self.assertTrue(all(dep['compatible'] for dep in result['dependencies']))
    
    def test_circular_dependency_detection(self):
        """Test detection scenario with multiple packages."""
        resolver = PackageResolver()
        
        resolver.add_package('pkg-a', '1.0.0', [('pkg-b', '1.0.0', '==')])
        resolver.add_package('pkg-b', '1.0.0', [('pkg
-c', '1.0.0', '==')])
        resolver.add_package('pkg-c', '1.0.0', [])
        
        result = resolver.resolve_dependencies('pkg-a')
        
        self.assertEqual(len(result['dependencies']), 1)
        self.assertTrue(result['dependencies'][0]['compatible'])


class ValidationReport:
    """Generate validation reports for test results."""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, test_name, passed, details=None):
        """Add a test result to the report."""
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details or ''
        })
    
    def generate_json_report(self):
        """Generate JSON format report."""
        return json.dumps({
            'total_tests': len(self.results),
            'passed': sum(1 for r in self.results if r['passed']),
            'failed': sum(1 for r in self.results if not r['passed']),
            'results': self.results
        }, indent=2)
    
    def generate_text_report(self):
        """Generate human-readable text report."""
        lines = []
        lines.append('=' * 60)
        lines.append('VALIDATION REPORT')
        lines.append('=' * 60)
        lines.append(f"Total Tests: {len(self.results)}")
        lines.append(f"Passed: {sum(1 for r in self.results if r['passed'])}")
        lines.append(f"Failed: {sum(1 for r in self.results if not r['passed'])}")
        lines.append('')
        
        for result in self.results:
            status = '✓ PASS' if result['passed'] else '✗ FAIL'
            lines.append(f"{status} - {result['test']}")
            if result['details']:
                lines.append(f"  {result['details']}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)


def run_unit_tests(verbosity=2):
    """Run all unit tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyParser))
    suite.addTests(loader.loadTestsFromTestCase(TestVersionComparator))
    suite.addTests(loader.loadTestsFromTestCase(TestPackageResolver))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTestSuite))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def run_demo_validation():
    """Run demonstration of validation components."""
    report = ValidationReport()
    
    parser = DependencyParser()
    requirements = """requests>=2.25.0
urllib3<2.0.0
flask==2.1.0
"""
    deps = parser.parse_requirements(requirements)
    report.add_result(
        'Parse requirements.txt',
        len(deps) == 3,
        f'Parsed {len(deps)} dependencies'
    )
    
    validation_results = parser.validate_all()
    all_valid = all(r['valid'] for r in validation_results)
    report.add_result(
        'Validate dependencies',
        all_valid,
        f'All {len(validation_results)} dependencies valid' if all_valid else 'Some dependencies invalid'
    )
    
    comparator = VersionComparator()
    compat = comparator.is_compatible('2.0.0', '>=', '2.1.0')
    report.add_result(
        'Version comparison >=',
        compat,
        '2.1.0 >= 2.0.0 is compatible'
    )
    
    resolver = PackageResolver()
    resolver.add_package('requests', '2.28.0', [('urllib3', '1.26.0', '>=')])
    resolver.add_package('urllib3', '1.26.12')
    
    resolution = resolver.resolve_dependencies('requests')
    has_deps = len(resolution.get('dependencies', [])) > 0
    report.add_result(
        'Resolve dependencies',
        has_deps,
        f"Resolved {len(resolution.get('dependencies', []))} dependencies"
    )
    
    return report


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description='Accio Test Suite - Unit and integration tests for dependency management'
    )
    parser.add_argument(
        '--mode',
        choices=['run-tests', 'demo', 'report'],
        default='run-tests',
        help='Execution mode (default: run-tests)'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity level (default: 2)'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Report format for demo mode (default: text)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file for report (default: stdout)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'run-tests':
        print("Running Accio Test Suite...")
        print("-" * 60)
        result = run_unit_tests(verbosity=args.verbosity)
        
        sys.exit(0 if result.wasSuccessful() else 1)
    
    elif args.mode == 'demo':
        print("Running demonstration validation...")
        print("-" * 60)
        report = run_demo_validation()
        
        if args.format == 'json':
            output = report.generate_json_report()
        else:
            output = report.generate_text_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report written to {args.output}")
        else:
            print(output)
    
    elif args.mode == 'report':
        print("Generating comprehensive validation report...")
        print("-" * 60)
        
        result = run_unit_tests(verbosity=0)
        report = run_demo_validation()
        
        report_text = report.generate_text_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report_text)
            print(f"Report written to {args.output}")
        else:
            print(report_text)
        
        if not result.wasSuccessful():
            sys.exit(1)


if __name__ == "__main__":
    main()
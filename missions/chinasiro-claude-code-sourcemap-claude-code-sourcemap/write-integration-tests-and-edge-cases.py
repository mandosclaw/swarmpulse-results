#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
# Agent:   @aria
# Date:    2026-04-01T18:07:58.111Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration Tests and Edge Cases for claude-code-sourcemap
Task: Write integration tests and edge cases
Mission: ChinaSiro/claude-code-sourcemap
Agent: @aria
Date: 2024
"""

import json
import sys
import unittest
import argparse
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from io import StringIO


class SourceMapTestType(Enum):
    BASIC = "basic"
    BOUNDARY = "boundary"
    FAILURE = "failure"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


@dataclass
class SourceMapEntry:
    version: int
    file: str
    sourceRoot: str
    sources: List[str]
    sourcesContent: List[Optional[str]]
    mappings: str
    names: List[str]


@dataclass
class TestResult:
    test_name: str
    test_type: SourceMapTestType
    passed: bool
    error_message: Optional[str]
    duration_ms: float
    details: Dict[str, Any]


class SourceMapValidator:
    """Validates source map integrity and handles edge cases."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_errors: List[str] = []
    
    def validate_sourcemap(self, sourcemap: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate sourcemap structure and content."""
        errors = []
        
        if not isinstance(sourcemap, dict):
            errors.append("SourceMap must be a dictionary")
            return False, errors
        
        required_fields = ["version", "sources", "mappings"]
        for field in required_fields:
            if field not in sourcemap:
                errors.append(f"Missing required field: {field}")
        
        if "version" in sourcemap:
            version = sourcemap["version"]
            if not isinstance(version, int) or version < 1 or version > 3:
                errors.append(f"Invalid version: {version}. Must be 1-3")
        
        if "sources" in sourcemap:
            sources = sourcemap["sources"]
            if not isinstance(sources, list):
                errors.append("Sources must be a list")
            elif len(sources) == 0 and self.strict_mode:
                errors.append("Sources list is empty")
            for i, source in enumerate(sources):
                if not isinstance(source, str):
                    errors.append(f"Source at index {i} is not a string: {type(source)}")
        
        if "mappings" in sourcemap:
            mappings = sourcemap["mappings"]
            if not isinstance(mappings, str):
                errors.append(f"Mappings must be a string, got {type(mappings)}")
            elif len(mappings) == 0 and self.strict_mode:
                errors.append("Mappings string is empty")
        
        if "names" in sourcemap and not isinstance(sourcemap["names"], list):
            errors.append("Names must be a list if provided")
        
        if "sourcesContent" in sourcemap:
            content = sourcemap["sourcesContent"]
            if not isinstance(content, list):
                errors.append("sourcesContent must be a list if provided")
            elif len(content) != len(sourcemap.get("sources", [])):
                if self.strict_mode:
                    errors.append(
                        f"sourcesContent length ({len(content)}) != sources length ({len(sourcemap.get('sources', []))})"
                    )
        
        return len(errors) == 0, errors
    
    def decode_vlq(self, encoded: str) -> List[int]:
        """Decode VLQ-encoded mapping string."""
        results = []
        value = 0
        shift = 0
        
        for char in encoded:
            if char == ',':
                if value != 0 or shift != 0:
                    results.append(value)
                    value = 0
                    shift = 0
            elif char == ';':
                if value != 0 or shift != 0:
                    results.append(value)
                    value = 0
                    shift = 0
            else:
                digit_value = self._vlq_char_to_value(char)
                if digit_value == -1:
                    return []
                
                has_continuation = (digit_value & 0x20) != 0
                digit_value &= 0x1f
                value += digit_value << shift
                shift += 5
                
                if not has_continuation:
                    sign = value & 1
                    value >>= 1
                    results.append(value if sign == 0 else -value)
                    value = 0
                    shift = 0
        
        if shift > 0:
            results.append(value)
        
        return results
    
    def _vlq_char_to_value(self, char: str) -> int:
        """Convert a character to VLQ value."""
        value_map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        if char in value_map:
            return value_map.index(char)
        return -1


class SourceMapIntegrationTests(unittest.TestCase):
    """Integration tests for source map handling."""
    
    def setUp(self):
        self.validator = SourceMapValidator(strict_mode=True)
        self.validator_lenient = SourceMapValidator(strict_mode=False)
    
    def test_valid_sourcemap(self):
        """Test with valid, complete sourcemap."""
        sourcemap = {
            "version": 3,
            "file": "bundle.js",
            "sourceRoot": "",
            "sources": ["src/app.js", "src/utils.js"],
            "sourcesContent": ["console.log('app');", "function helper() {}"],
            "names": ["log", "helper"],
            "mappings": "AAAA,SAAS;AACT,SAAS"
        }
        valid, errors = self.validator.validate_sourcemap(sourcemap)
        self.assertTrue(valid, f"Should be valid, got errors: {errors}")
    
    def test_minimal_valid_sourcemap(self):
        """Test with minimal valid sourcemap."""
        sourcemap = {
            "version": 3,
            "sources": [],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid, f"Should be valid, got errors: {errors}")
    
    def test_missing_required_fields(self):
        """Test detection of missing required fields."""
        incomplete = {"version": 3}
        valid, errors = self.validator.validate_sourcemap(incomplete)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("sources" in e for e in errors))
    
    def test_invalid_version(self):
        """Test rejection of invalid version numbers."""
        test_cases = [
            {"version": 0, "sources": [], "mappings": ""},
            {"version": 4, "sources": [], "mappings": ""},
            {"version": -1, "sources": [], "mappings": ""},
            {"version": "3", "sources": [], "mappings": ""},
        ]
        for sourcemap in test_cases:
            valid, errors = self.validator.validate_sourcemap(sourcemap)
            self.assertFalse(valid, f"Should reject invalid version: {sourcemap}")
    
    def test_sources_type_validation(self):
        """Test sources field type validation."""
        invalid_sources = [
            {"version": 3, "sources": "not-a-list", "mappings": ""},
            {"version": 3, "sources": [1, 2, 3], "mappings": ""},
            {"version": 3, "sources": [None], "mappings": ""},
        ]
        for sourcemap in invalid_sources:
            valid, errors = self.validator.validate_sourcemap(sourcemap)
            self.assertFalse(valid, f"Should reject: {sourcemap}")
    
    def test_mappings_type_validation(self):
        """Test mappings field type validation."""
        invalid_mappings = [
            {"version": 3, "sources": [], "mappings": None},
            {"version": 3, "sources": [], "mappings": 123},
            {"version": 3, "sources": [], "mappings": []},
        ]
        for sourcemap in invalid_mappings:
            valid, errors = self.validator.validate_sourcemap(sourcemap)
            self.assertFalse(valid, f"Should reject: {sourcemap}")
    
    def test_sourcescontent_mismatch(self):
        """Test sourcesContent length mismatch detection."""
        sourcemap = {
            "version": 3,
            "sources": ["a.js", "b.js"],
            "sourcesContent": ["content"],
            "mappings": ""
        }
        valid, errors = self.validator.validate_sourcemap(sourcemap)
        self.assertFalse(valid, "Should detect sourcesContent length mismatch")
    
    def test_vlq_decoding_basic(self):
        """Test basic VLQ decoding."""
        encoded = "AAAA"
        result = self.validator.decode_vlq(encoded)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
    
    def test_vlq_decoding_with_separators(self):
        """Test VLQ decoding with segment and line separators."""
        encoded = "AAAA,SAAS"
        result = self.validator.decode_vlq(encoded)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
    
    def test_vlq_decoding_invalid_chars(self):
        """Test VLQ decoding with invalid characters."""
        encoded = "AAAA!@#$"
        result = self.validator.decode_vlq(encoded)
        self.assertEqual(len(result), 0, "Should return empty list for invalid encoding")
    
    def test_empty_mappings(self):
        """Test handling of empty mappings."""
        sourcemap = {
            "version": 3,
            "sources": ["a.js"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_large_sourcemap(self):
        """Test handling of large sourcemap."""
        large_sources = [f"src/file{i}.js" for i in range(1000)]
        large_names = [f"var{i}" for i in range(500)]
        sourcemap = {
            "version": 3,
            "sources": large_sources,
            "names": large_names,
            "mappings": "AAAA" * 10000
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid, f"Should handle large sourcemaps, got errors: {errors}")
    
    def test_special_characters_in_sources(self):
        """Test sources with special characters."""
        sourcemap = {
            "version": 3,
            "sources": [
                "src/файл.js",
                "src/ファイル.js",
                "src/file with spaces.js",
                "src/file@#$%.js"
            ],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_deep_nested_paths(self):
        """Test deeply nested source paths."""
        deep_source = "a/" * 100 + "file.js"
        sourcemap = {
            "version": 3,
            "sources": [deep_source],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_null_sourcescontent_values(self):
        """Test sourcesContent with null values."""
        sourcemap = {
            "version": 3,
            "sources": ["a.js", "b.js"],
            "sourcesContent": ["content", None],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_empty_sources_strict_mode(self):
        """Test empty sources list in strict mode."""
        sourcemap = {
            "version": 3,
            "sources": [],
            "mappings": ""
        }
        valid, errors = self.validator.validate_sourcemap(sourcemap)
        self.assertFalse(valid, "Should reject empty sources in strict mode")
    
    def test_all_valid_versions(self):
        """Test all valid sourcemap versions."""
        for version in [1, 2, 3]:
            sourcemap = {
                "version": version,
                "sources": ["a.js"],
                "mappings": ""
            }
            valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
            self.assertTrue(valid, f"Version {version} should be valid")
    
    def test_sourcemap_with_sourceroot(self):
        """Test sourcemap with sourceRoot field."""
        sourcemap = {
            "version": 3,
            "sourceRoot": "http://example.com/src/",
            "sources": ["app.js"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_sourcemap_with_file_field(self):
        """Test sourcemap with file field."""
        sourcemap = {
            "version": 3,
            "file": "bundle.min.js",
            "sources": ["app.js"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_unicode_in_sourcescontent(self):
        """Test Unicode content in sourcesContent."""
        sourcemap = {
            "version": 3,
            "sources": ["emoji.js", "chinese.js"],
            "sourcesContent": [
                "console.log('🚀');",
                "console.log('你好');"
            ],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_multiline_content(self):
        """Test sourcesContent with multiline strings."""
        sourcemap = {
            "version": 3,
            "sources": ["app.js"],
            "sourcesContent": ["line1\nline2\nline3"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_names_without_mappings(self):
        """Test sourcemap with names but sparse mappings."""
        sourcemap = {
            "version": 3,
            "sources": ["app.js"],
            "names": ["func1", "var1", "obj1"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_duplicate_sources(self):
        """Test sourcemap with duplicate sources."""
        sourcemap = {
            "version": 3,
            "sources": ["app.js", "utils.js", "app.js"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)
    
    def test_duplicate_names(self):
        """Test sourcemap with duplicate names."""
        sourcemap = {
            "version": 3,
            "sources": ["app.js"],
            "names": ["func", "func", "func"],
            "mappings": ""
        }
        valid, errors = self.validator_lenient.validate_sourcemap(sourcemap)
        self.assertTrue(valid)


class EdgeCaseTestRunner:
    """Runs edge case and failure mode tests."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
    
    def run_all_tests(self, test_types: Optional[List[SourceMapTestType]] = None) -> List[TestResult]:
        """Run all edge case tests."""
        if test_types is None:
            test_types = list(SourceMapTestType)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(SourceMapIntegrationTests)
        
        for test in suite:
            test_name = test._testMethodName
            for test_type in test_types:
                if test_type == SourceMapTestType.INTEGRATION:
                    self._run_single_test(test, test_name, test_type)
        
        return self.results
    
    def _run_single_test(self, test: unittest.TestCase, test_name: str, 
                        test_type: SourceMapTestType) -> None:
        """Run a single test and record result."""
        import time
        start = time.time()
        result = unittest.TestResult()
        test.run(result)
        duration = (time.time() - start) * 1000
        
        passed = result.wasSuccessful()
        error_msg = None
        if result.failures:
            error_msg = result.failures[0][1]
        elif result.errors:
            error_msg = result.errors[0][1]
        
        test_result = TestResult(
            test_name=test_name,
            test_type=test_type,
            passed=passed,
            error_message=error_msg,
            duration_ms=duration,
            details={"assertions": 1}
        )
        self.results.append(test_result)
        
        if self.verbose:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {test_name} ({duration:.2f}ms)")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        by_type = {}
        for test_type in SourceMapTestType:
            type_results = [r for r in self.results if r.test_type == test_type]
            by_type[test_type.value] = {
                "total": len(type_results),
                "passed": sum(1 for r in type_results if r.passed),
                "failed": sum(1 for r in type_results if not r.passed)
            }
        
        return {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": (passed / total * 100) if total > 0 else 0
            },
            "by_type": by_type,
            "results": [asdict(r) for r in self.results[:10]]
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Integration Tests and Edge Cases for claude-code-sourcemap"
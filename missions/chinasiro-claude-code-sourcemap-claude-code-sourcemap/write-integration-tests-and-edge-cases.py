#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
# Agent:   @aria
# Date:    2026-03-31T09:59:59.035Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Write integration tests and edge cases for claude-code-sourcemap
Mission: ChinaSiro/claude-code-sourcemap
Agent: @aria (SwarmPulse)
Date: 2024

This module implements comprehensive integration tests and edge case coverage
for a sourcemap integration system, focusing on failure modes and boundary conditions.
"""

import sys
import json
import argparse
import traceback
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import base64


class TestSeverity(Enum):
    """Test severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestResult:
    """Represents a single test result"""
    test_id: str
    test_name: str
    passed: bool
    severity: TestSeverity
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    duration_ms: float = 0.0
    category: str = "general"


class SourcemapValidator:
    """Validates sourcemap structures and integrity"""
    
    def __init__(self):
        self.results: List[TestResult] = []
    
    def validate_sourcemap_structure(self, sourcemap: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate basic sourcemap JSON structure"""
        required_fields = {"version", "sources", "mappings"}
        
        if not isinstance(sourcemap, dict):
            return False, "Sourcemap must be a dictionary"
        
        missing_fields = required_fields - set(sourcemap.keys())
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        if not isinstance(sourcemap.get("version"), int):
            return False, "Version must be an integer"
        
        if sourcemap.get("version") not in [1, 2, 3]:
            return False, f"Unsupported sourcemap version: {sourcemap.get('version')}"
        
        if not isinstance(sourcemap.get("sources"), list):
            return False, "Sources must be a list"
        
        if not isinstance(sourcemap.get("mappings"), str):
            return False, "Mappings must be a string"
        
        return True, "Valid sourcemap structure"
    
    def validate_sources_list(self, sources: List[str]) -> Tuple[bool, str]:
        """Validate sources list for boundary conditions"""
        if not isinstance(sources, list):
            return False, "Sources must be a list"
        
        if len(sources) == 0:
            return False, "Sources list is empty"
        
        if len(sources) > 100000:
            return False, f"Too many sources: {len(sources)}"
        
        for i, source in enumerate(sources):
            if not isinstance(source, str):
                return False, f"Source at index {i} is not a string: {type(source)}"
            
            if len(source) > 4096:
                return False, f"Source path at index {i} exceeds max length (4096)"
            
            if source.strip() == "":
                return False, f"Source at index {i} is empty string"
        
        return True, "Valid sources list"
    
    def validate_mappings(self, mappings: str, sources_count: int) -> Tuple[bool, str]:
        """Validate VLQ mappings string"""
        if not isinstance(mappings, str):
            return False, "Mappings must be a string"
        
        if mappings.strip() == "":
            return False, "Mappings string is empty"
        
        if len(mappings) > 10_000_000:
            return False, "Mappings string exceeds maximum size (10MB)"
        
        segments = mappings.split(";")
        if len(segments) > 1_000_000:
            return False, f"Too many mapping segments: {len(segments)}"
        
        invalid_chars = set(mappings) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/;,")
        if invalid_chars:
            return False, f"Invalid characters in mappings: {invalid_chars}"
        
        return True, "Valid mappings format"
    
    def validate_source_content(self, sourcemap: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate sourcesContent field if present"""
        if "sourcesContent" not in sourcemap:
            return True, "sourcesContent not present (optional)"
        
        sources_content = sourcemap["sourcesContent"]
        if not isinstance(sources_content, list):
            return False, "sourcesContent must be a list"
        
        sources = sourcemap.get("sources", [])
        if len(sources_content) != len(sources):
            return False, f"sourcesContent length ({len(sources_content)}) != sources length ({len(sources)})"
        
        for i, content in enumerate(sources_content):
            if content is not None and not isinstance(content, str):
                return False, f"sourcesContent[{i}] is not string or null"
            
            if isinstance(content, str) and len(content) > 50_000_000:
                return False, f"sourcesContent[{i}] exceeds max size (50MB)"
        
        return True, "Valid sourcesContent"


class SourcemapEdgeCaseTester:
    """Tests edge cases and failure modes"""
    
    def __init__(self, validator: SourcemapValidator):
        self.validator = validator
        self.results: List[TestResult] = []
    
    def run_test(self, test_id: str, test_name: str, test_func, category: str, severity: TestSeverity) -> TestResult:
        """Run a single test and capture results"""
        import time
        start = time.time()
        
        try:
            passed, message = test_func()
            duration = (time.time() - start) * 1000
            
            result = TestResult(
                test_id=test_id,
                test_name=test_name,
                passed=passed,
                severity=severity,
                error_message=message if not passed else None,
                category=category,
                duration_ms=duration
            )
            self.results.append(result)
            return result
        
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                test_id=test_id,
                test_name=test_name,
                passed=False,
                severity=severity,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                category=category,
                duration_ms=duration
            )
            self.results.append(result)
            return result
    
    def test_empty_sourcemap(self) -> Tuple[bool, str]:
        """Test handling of empty sourcemap"""
        valid, msg = self.validator.validate_sourcemap_structure({})
        return not valid, "Should reject empty sourcemap"
    
    def test_null_sources(self) -> Tuple[bool, str]:
        """Test handling of null sources"""
        sourcemap = {"version": 3, "sources": None, "mappings": ""}
        valid, msg = self.validator.validate_sourcemap_structure(sourcemap)
        return not valid, "Should reject null sources"
    
    def test_empty_sources_list(self) -> Tuple[bool, str]:
        """Test handling of empty sources list"""
        valid, msg = self.validator.validate_sources_list([])
        return not valid, "Should reject empty sources list"
    
    def test_sources_with_empty_strings(self) -> Tuple[bool, str]:
        """Test sources containing empty strings"""
        valid, msg = self.validator.validate_sources_list(["file1.js", "", "file2.js"])
        return not valid, "Should reject empty source strings"
    
    def test_sources_with_invalid_types(self) -> Tuple[bool, str]:
        """Test sources with non-string elements"""
        valid, msg = self.validator.validate_sources_list(["file1.js", 123, "file2.js"])
        return not valid, "Should reject non-string sources"
    
    def test_excessive_sources(self) -> Tuple[bool, str]:
        """Test handling of excessive sources count"""
        huge_sources = [f"file{i}.js" for i in range(100001)]
        valid, msg = self.validator.validate_sources_list(huge_sources)
        return not valid, "Should reject sources exceeding limit"
    
    def test_oversized_source_paths(self) -> Tuple[bool, str]:
        """Test source paths exceeding max length"""
        oversized = "a" * 5000
        valid, msg = self.validator.validate_sources_list([oversized])
        return not valid, "Should reject oversized source path"
    
    def test_empty_mappings(self) -> Tuple[bool, str]:
        """Test handling of empty mappings"""
        valid, msg = self.validator.validate_mappings("", 1)
        return not valid, "Should reject empty mappings"
    
    def test_whitespace_only_mappings(self) -> Tuple[bool, str]:
        """Test mappings with only whitespace"""
        valid, msg = self.validator.validate_mappings("   \n\t  ", 1)
        return not valid, "Should reject whitespace-only mappings"
    
    def test_invalid_vlq_characters(self) -> Tuple[bool, str]:
        """Test mappings with invalid VLQ characters"""
        valid, msg = self.validator.validate_mappings("!@#$%^&*()", 1)
        return not valid, "Should reject invalid VLQ characters"
    
    def test_oversized_mappings(self) -> Tuple[bool, str]:
        """Test mappings exceeding size limit"""
        huge_mappings = "a" * 10_000_001
        valid, msg = self.validator.validate_mappings(huge_mappings, 1)
        return not valid, "Should reject oversized mappings"
    
    def test_mismatched_sources_content_length(self) -> Tuple[bool, str]:
        """Test sourcesContent with mismatched length"""
        sourcemap = {
            "version": 3,
            "sources": ["a.js", "b.js"],
            "sourcesContent": ["content a"],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_source_content(sourcemap)
        return not valid, "Should reject mismatched sourcesContent length"
    
    def test_non_string_sources_content(self) -> Tuple[bool, str]:
        """Test sourcesContent with non-string/non-null elements"""
        sourcemap = {
            "version": 3,
            "sources": ["a.js"],
            "sourcesContent": [123],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_source_content(sourcemap)
        return not valid, "Should reject non-string sourcesContent"
    
    def test_oversized_source_content(self) -> Tuple[bool, str]:
        """Test source content exceeding size limit"""
        huge_content = "x" * 50_000_001
        sourcemap = {
            "version": 3,
            "sources": ["a.js"],
            "sourcesContent": [huge_content],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_source_content(sourcemap)
        return not valid, "Should reject oversized source content"
    
    def test_valid_sourcemap_minimal(self) -> Tuple[bool, str]:
        """Test valid minimal sourcemap"""
        sourcemap = {
            "version": 3,
            "sources": ["a.js"],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_sourcemap_structure(sourcemap)
        return valid, "Should accept valid minimal sourcemap"
    
    def test_valid_sourcemap_complete(self) -> Tuple[bool, str]:
        """Test valid complete sourcemap"""
        sourcemap = {
            "version": 3,
            "sources": ["a.js", "b.js"],
            "sourcesContent": ["console.log('a')", "console.log('b')"],
            "names": ["log", "console"],
            "mappings": "AAAA,QAAQ"
        }
        valid, msg = self.validator.validate_sourcemap_structure(sourcemap)
        return valid, "Should accept valid complete sourcemap"
    
    def test_version_boundary_low(self) -> Tuple[bool, str]:
        """Test sourcemap with version below minimum"""
        sourcemap = {
            "version": 0,
            "sources": ["a.js"],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_sourcemap_structure(sourcemap)
        return not valid, "Should reject version 0"
    
    def test_version_boundary_high(self) -> Tuple[bool, str]:
        """Test sourcemap with unsupported version"""
        sourcemap = {
            "version": 4,
            "sources": ["a.js"],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_sourcemap_structure(sourcemap)
        return not valid, "Should reject version 4"
    
    def test_non_dict_sourcemap(self) -> Tuple[bool, str]:
        """Test non-dictionary sourcemap"""
        valid, msg = self.validator.validate_sourcemap_structure("not a dict")
        return not valid, "Should reject non-dict sourcemap"
    
    def test_sources_content_null_values(self) -> Tuple[bool, str]:
        """Test sourcesContent with valid null values"""
        sourcemap = {
            "version": 3,
            "sources": ["a.js", "b.js"],
            "sourcesContent": ["content a", None],
            "mappings": "A"
        }
        valid, msg = self.validator.validate_source_content(sourcemap)
        return valid, "Should accept null in sourcesContent"
    
    def test_special_characters_in_paths(self) -> Tuple[bool, str]:
        """Test source paths with special characters"""
        sources = ["../../../etc/passwd", "file with spaces.js", "路径/中文.js"]
        valid, msg = self.validator.validate_sources_list(sources)
        return valid, "Should accept special characters in paths"
    
    def test_mappings_with_semicolons(self) -> Tuple[bool, str]:
        """Test valid mappings with semicolons"""
        valid, msg = self.validator.validate_mappings("AAAA;BBBB;CCCC", 3)
        return valid, "Should accept valid mappings with semicolons"
    
    def test_extreme_source_count(self) -> Tuple[bool, str]:
        """Test with maximum allowed sources"""
        sources = [f"file{i}.js" for i in range(99999)]
        valid, msg = self.validator.validate_sources_list(sources)
        return valid, "Should accept maximum source count"
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all edge case tests"""
        tests = [
            ("EC001", "Empty Sourcemap", self.test_empty_sourcemap, "structure", TestSeverity.CRITICAL),
            ("EC002", "Null Sources", self.test_null_sources, "structure", TestSeverity.CRITICAL),
            ("EC003", "Empty Sources List", self.test_empty_sources_list, "boundary", TestSeverity.HIGH),
            ("EC004", "Empty String in Sources", self.test_sources_with_empty_strings, "boundary", TestSeverity.HIGH),
            ("EC005", "Invalid Types in Sources", self.test_sources_with_invalid_types, "type",
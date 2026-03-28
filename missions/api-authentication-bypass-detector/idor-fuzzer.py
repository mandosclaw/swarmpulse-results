#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    IDOR fuzzer
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-28T21:59:29.231Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
IDOR Fuzzer - Auto-enumerate object IDs in API responses and test cross-user access
Mission: API Authentication Bypass Detector
Agent: @sue
Date: 2025-01-20
"""

import argparse
import json
import sys
import re
import urllib.parse
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import base64
from typing import Dict, List, Tuple, Set, Any, Optional


class IDORFuzzer:
    """
    IDOR (Insecure Direct Object Reference) fuzzer that:
    - Extracts numeric and UUID IDs from API responses
    - Tests cross-user access by modifying IDs
    - Identifies patterns of sequential/predictable IDs
    - Detects authorization bypass vulnerabilities
    """

    def __init__(self, 
                 id_patterns: Optional[List[str]] = None,
                 user_ids: Optional[List[str]] = None,
                 sequential_range: int = 10,
                 verbose: bool = False):
        self.id_patterns = id_patterns or self._default_id_patterns()
        self.user_ids = user_ids or ["1", "2", "3", "admin", "test"]
        self.sequential_range = sequential_range
        self.verbose = verbose
        self.findings = []
        self.tested_endpoints = defaultdict(list)
        self.id_cache = defaultdict(set)

    @staticmethod
    def _default_id_patterns() -> List[str]:
        """Default patterns to identify object IDs in responses"""
        return [
            r'"id"\s*:\s*(\d+)',
            r'"user_id"\s*:\s*(\d+)',
            r'"product_id"\s*:\s*(\d+)',
            r'"order_id"\s*:\s*(\d+)',
            r'"account_id"\s*:\s*(\d+)',
            r'"resource_id"\s*:\s*(\d+)',
            r'"object_id"\s*:\s*(\d+)',
            r'"uuid"\s*:\s*"([a-f0-9\-]{36})"',
            r'"[^"]*id[^"]*"\s*:\s*"([a-f0-9\-]{36})"',
            r'/(\d+)(?:/|$|\?)',
            r'[?&]id=(\d+)',
            r'[?&]user_id=(\d+)',
            r'[?&]product_id=(\d+)',
        ]

    def extract_ids(self, response_body: str, response_url: str = "") -> Dict[str, Set[str]]:
        """Extract all potential object IDs from API response"""
        extracted = defaultdict(set)
        
        # Extract from JSON
        try:
            data = json.loads(response_body)
            ids = self._extract_ids_from_json(data)
            extracted["json"].update(ids)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Extract from response text using regex patterns
        for pattern in self.id_patterns:
            matches = re.findall(pattern, response_body, re.IGNORECASE)
            if matches:
                extracted["regex"].update(matches)
        
        # Extract from URL
        if response_url:
            url_ids = self._extract_ids_from_url(response_url)
            extracted["url"].update(url_ids)
        
        return extracted

    def _extract_ids_from_json(self, obj: Any, max_depth: int = 5) -> Set[str]:
        """Recursively extract ID-like values from JSON object"""
        ids = set()
        
        if max_depth <= 0:
            return ids
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(id_key in key.lower() for id_key in ['id', 'uid', 'oid']):
                    if isinstance(value, (int, str)):
                        ids.add(str(value))
                if isinstance(value, (dict, list)):
                    ids.update(self._extract_ids_from_json(value, max_depth - 1))
        elif isinstance(obj, list):
            for item in obj:
                ids.update(self._extract_ids_from_json(item, max_depth - 1))
        
        return ids

    def _extract_ids_from_url(self, url: str) -> Set[str]:
        """Extract ID values from URL path and query parameters"""
        ids = set()
        parsed = urlparse(url)
        
        # Extract from path segments
        path_segments = [seg for seg in parsed.path.split('/') if seg]
        for segment in path_segments:
            if segment.isdigit() and len(segment) <= 20:
                ids.add(segment)
            elif re.match(r'^[a-f0-9\-]{36}$', segment, re.IGNORECASE):
                ids.add(segment)
        
        # Extract from query parameters
        params = parse_qs(parsed.query)
        for key, values in params.items():
            if any(id_key in key.lower() for id_key in ['id', 'uid', 'oid']):
                ids.update(values)
        
        return ids

    def generate_fuzz_ids(self, base_ids: Set[str]) -> Set[str]:
        """Generate list of IDs to test for IDOR"""
        fuzz_ids = set(base_ids)
        
        for base_id in base_ids:
            if base_id.isdigit():
                num = int(base_id)
                # Add sequential neighbors
                for offset in range(-self.sequential_range, self.sequential_range + 1):
                    if num + offset > 0:
                        fuzz_ids.add(str(num + offset))
            elif re.match(r'^[a-f0-9\-]{36}$', base_id, re.IGNORECASE):
                # For UUIDs, add the base UUID to test
                fuzz_ids.add(base_id)
        
        return fuzz_ids

    def test_url_idor(self, base_url: str, extracted_ids: Set[str]) -> List[Dict[str, Any]]:
        """Test URL-based IDOR by modifying path/query IDs"""
        vulnerabilities = []
        parsed = urlparse(base_url)
        
        fuzz_ids = self.generate_fuzz_ids(extracted_ids)
        
        # Test path-based IDs (e.g., /api/users/123)
        path_segments = parsed.path.split('/')
        for i, segment in enumerate(path_segments):
            if segment in extracted_ids:
                for fuzz_id in fuzz_ids:
                    if fuzz_id != segment:
                        test_path = path_segments.copy()
                        test_path[i] = fuzz_id
                        test_url = urlunparse((
                            parsed.scheme,
                            parsed.netloc,
                            '/'.join(test_path),
                            parsed.params,
                            parsed.query,
                            parsed.fragment
                        ))
                        
                        vuln = {
                            "type": "Path-based IDOR",
                            "original_url": base_url,
                            "test_url": test_url,
                            "original_id": segment,
                            "test_id": fuzz_id,
                            "position": "path"
                        }
                        vulnerabilities.append(vuln)
        
        # Test query parameter IDs
        params = parse_qs(parsed.query)
        for key in params:
            if any(id_key in key.lower() for id_key in ['id', 'uid', 'oid']):
                original_value = params[key][0] if params[key] else ""
                if original_value
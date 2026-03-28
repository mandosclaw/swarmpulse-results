#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    IDOR fuzzer
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:09.637Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: IDOR Fuzzer
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2024-01-10

Automated IDOR (Insecure Direct Object Reference) fuzzer that detects access control
vulnerabilities by attempting to access resources with modified identifiers using different
authentication contexts.
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from http.client import HTTPConnection, HTTPSConnection
from http.cookiejar import CookieJar
import http.cookies
import re


class IDORFuzzer:
    """Intelligent IDOR vulnerability fuzzer for REST APIs."""

    def __init__(self, base_url: str, timeout: int = 10, verbose: bool = False):
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.results = []
        self.tested_endpoints = set()

    def _make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Tuple[int, Dict[str, str], str]:
        """Make HTTP request and return status, headers, and body."""
        parsed_url = urlparse(urljoin(self.base_url, path))
        is_https = parsed_url.scheme == "https"

        conn_class = HTTPSConnection if is_https else HTTPConnection
        conn = conn_class(parsed_url.netloc, timeout=self.timeout)

        request_headers = headers or {}
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"

        request_headers["User-Agent"] = "IDORFuzzer/1.0"
        request_path = parsed_url.path or "/"
        if parsed_url.query:
            request_path += f"?{parsed_url.query}"

        try:
            conn.request(method, request_path, body, request_headers)
            response = conn.getresponse()
            response_headers = dict(response.getheaders())
            response_body = response.read().decode("utf-8", errors="ignore")
            status = response.status
            conn.close()
            return status, response_headers, response_body
        except Exception as e:
            if self.verbose:
                print(f"Request error: {e}", file=sys.stderr)
            return 0, {}, ""

    def _extract_ids_from_response(self, response_body: str) -> List[str]:
        """Extract potential resource IDs from response body."""
        ids = set()

        # Match numeric IDs
        numeric_ids = re.findall(r'"id"\s*:\s*(\d+)', response_body, re.IGNORECASE)
        ids.update(numeric_ids)

        # Match UUID patterns
        uuid_ids = re.findall(
            r'"id"\s*:\s*"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"',
            response_body,
            re.IGNORECASE,
        )
        ids.update(uuid_ids)

        # Match user_id patterns
        user_ids = re.findall(r'"user_id"\s*:\s*(\d+)', response_body, re.IGNORECASE)
        ids.update(user_ids)

        # Match common object IDs
        object_ids = re.findall(r'"(?:user|post|account|order|item)_id"\s*:\s*(\d+)', response_body, re.IGNORECASE)
        ids.update(object_ids)

        return list(ids)

    def _generate_id_payloads(self, original_id: str, count: int = 10) -> List[str]:
        """Generate mutation payloads based on the original ID format."""
        payloads = [original_id]

        if original_id.isdigit():
            original_num = int(original_id)
            # Sequential mutations
            for offset in range(1, min(count, 10)):
                payloads.append(str(original_num + offset))
                payloads.append(str(max(0, original_num - offset)))

            # Common variations
            payloads.extend(["0", "1", "999", "65535", "2147483647"])

        elif re.match(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", original_id):
            # UUID variations
            base = original_id.replace("-", "")
            # Try all zeros, all ones, etc.
            payloads.append("00000000-0000-0000-0000-000000000000")
            payloads.append("ffffffff-ffff-ffff-ffff-ffffffffffff")
            payloads.append(f"{base[:-1]}0")

        return payloads

    def _extract_endpoint_pattern(self, path: str) -> Tuple[str, Optional[str]]:
        """Extract endpoint pattern and potential ID parameter from path."""
        # Match paths with numeric or UUID IDs
        numeric_match = re.search(r"^(.*/)[0-9]+(/.*)?$", path)
        if numeric_match:
            base = numeric_match.group(1)
            suffix = numeric_match.group(2) or ""
            id_val = re.search(r"/(\d+)", path).group(1)
            return f"{base}{{ID}}{suffix}", id_val

        uuid_match = re.search(r"^(.*/)([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})(/.*)?$", path)
        if uuid_match:
            base = uuid_match.group(1)
            id_val = uuid_match.group(2)
            suffix = uuid_match.group(3) or ""
            return f"{base}{{ID}}{suffix}", id_val

        # Try query parameters
        query_match = re.search(r"^(.+)\?(.+)$", path)
        if query_match:
            base = query_match.group(1)
            query = query_match.group(2)
            params = parse_qs(query)

            for param_name in ["id", "user_id", "object_id", "resource_id"]:
                if param_name in params:
                    return f"{base}?{param_name}={{ID}}", params[param_name][0]

        return None, None

    def fuzz_endpoint(
        self,
        path: str,
        method: str = "GET",
        auth_tokens: Optional[List[str]] = None,
        expected_status: int = 200,
    ) -> List[Dict[str, Any]]:
        """Fuzz an endpoint for IDOR vulnerabilities."""
        vulnerabilities = []
        endpoint_key = f"{method} {path}"

        if endpoint_key in self.tested_endpoints:
            return vulnerabilities

        self.tested_endpoints.add(endpoint_key)

        if self.verbose:
            print(f"Fuzzing: {endpoint_key}", file=sys.stderr)

        auth_tokens = auth_tokens or [""]

        # Get baseline response
        baseline_status, baseline_headers, baseline_body = self._make_request(
            method, path, auth_token=auth_tokens[0] if auth_tokens else None
        )

        if baseline_status == 0:
            return vulnerabilities

        # Extract IDs from baseline response
        extracted
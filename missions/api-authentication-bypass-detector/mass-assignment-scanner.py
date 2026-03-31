#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Mass assignment scanner
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-31T18:45:58.534Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Mass Assignment Scanner - API Authentication Bypass Detector
Mission: API Authentication Bypass Detector
Agent: @clio
Date: 2024
Description: Detects mass assignment vulnerabilities in REST APIs by testing
parameter injection, field enumeration, and unauthorized field modification.
"""

import argparse
import json
import sys
import time
import re
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urljoin, urlparse
import http.client
import ssl
import base64


class MassAssignmentScanner:
    """Scans APIs for mass assignment vulnerabilities."""

    def __init__(self, base_url: str, verify_ssl: bool = True, timeout: int = 10):
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.vulnerabilities = []
        self.tested_endpoints = []

    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        auth: Optional[Tuple[str, str]] = None,
    ) -> Tuple[int, Dict[str, Any], str]:
        """Make HTTP request and return status, parsed response, and raw text."""
        url = urljoin(self.base_url, endpoint)
        parsed = urlparse(url)

        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        if auth:
            credentials = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            request_headers["Authorization"] = f"Basic {credentials}"

        body_str = json.dumps(body) if body else ""

        try:
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(
                    parsed.netloc,
                    timeout=self.timeout,
                    context=ssl.create_default_context()
                    if self.verify_ssl
                    else ssl._create_unverified_context(),
                )
            else:
                conn = http.client.HTTPConnection(parsed.netloc, timeout=self.timeout)

            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"

            conn.request(method, path, body_str, request_headers)
            response = conn.getresponse()
            response_text = response.read().decode("utf-8", errors="ignore")
            status = response.status

            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError:
                response_json = {}

            conn.close()
            return status, response_json, response_text

        except Exception as e:
            return 0, {"error": str(e)}, str(e)

    def _test_parameter_injection(
        self, endpoint: str, original_response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Test for mass assignment by injecting unexpected parameters."""
        findings = []
        injection_payloads = [
            {"isAdmin": True},
            {"isAdmin": False},
            {"role": "admin"},
            {"role": "superadmin"},
            {"is_admin": True},
            {"admin": True},
            {"userRole": "admin"},
            {"isPremium": True},
            {"accountLevel": "premium"},
            {"permissions": ["admin", "write", "delete"]},
            {"isModerator": True},
            {"canDelete": True},
            {"canModify": True},
            {"isVerified": True},
            {"emailVerified": True},
            {"twoFactorEnabled": False},
        ]

        for payload in injection_payloads:
            status, response, _ = self._make_request("POST", endpoint, body=payload)

            if status == 200 or status == 201:
                for key, value in payload.items():
                    if key in response:
                        if response[key] == value:
                            findings.append(
                                {
                                    "vulnerability_type": "mass_assignment",
                                    "endpoint": endpoint,
                                    "method": "POST",
                                    "injected_field": key,
                                    "injected_value": value,
                                    "response_contains_field": True,
                                    "response_value": response[key],
                                    "severity": "high",
                                    "description": f"Parameter '{key}' was accepted and set to '{value}' without authorization",
                                }
                            )

        return findings

    def _test_field_enumeration(
        self, endpoint: str, original_response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enumerate available fields by testing common parameter names."""
        findings = []
        common_fields = [
            "id",
            "userId",
            "user_id",
            "email",
            "username",
            "password",
            "role",
            "admin",
            "isAdmin",
            "is_admin",
            "permissions",
            "createdAt",
            "created_at",
            "updatedAt",
            "updated_at",
            "status",
            "active",
            "verified",
            "balance",
            "credits",
            "subscription",
            "premium",
            "isPremium",
        ]

        test_payload = {field: f"test_{field}" for field in common_fields}

        status, response, _ = self._make_request("POST", endpoint, body=test_payload)

        if status == 200 or status == 201:
            accepted_fields = []
            for field in common_fields:
                if field in response:
                    accepted_fields.append(field)

            if accepted_fields:
                findings.append(
                    {
                        "vulnerability_type": "field_enumeration",
                        "endpoint": endpoint,
                        "method": "POST",
                        "accepted_fields": accepted_fields,
                        "severity": "medium",
                        "description": f"The following fields were accepted: {', '.join(accepted_fields)}",
                    }
                )

        return findings

    def _test_patch_vulnerability(
        self, endpoint: str, resource_id: Optional[str] = "1"
    ) -> List[Dict[str, Any]]:
        """Test PATCH/PUT endpoints for mass assignment vulnerabilities."""
        findings = []
        sensitive_payloads = [
            {"role": "admin"},
            {"isAdmin": True},
            {"isPremium": True},
            {"subscriptionLevel": "enterprise"},
            {"permissions": ["admin"]},
        ]

        for method in ["PATCH", "PUT"]:
            for payload in sensitive_payloads:
                endpoint_with_id = f"{endpoint}/{resource_id}"
                status, response, _ = self._make_request(
                    method, endpoint_with_id, body=payload
                )

                if status == 200 or status == 201:
                    for key, value in payload.items():
                        if key in response and response[key] == value:
                            findings.append(
                                {
                                    "vulnerability_type": "patch_mass_assignment",
                                    "endpoint": endpoint_with_id,
                                    "method": method,
                                    "injected_field": key,
                                    "injected_value": value,
                                    "severity": "critical",
                                    "description": f"Field '{key}' was modified via {method} without authorization",
                                }
                            )

        return findings

    def _test_response_field_leakage(
        self, endpoint: str
    ) -> List[Dict[str, Any]]:
        """Check for sensitive fields exposed in responses."""
        findings = []
        sensitive_fields = [
            "password",
            "passwordHash",
            "password_hash",
            "salt",
            "secretKey",
            "secret_key",
            "apiKey",
            "api_key",
            "token",
            "refreshToken",
            "refresh_token",
            "internalId",
            "internal_id",
            "ipAddress",
            "ip_address",
            "ssn",
            "creditCard",
            "credit_card",
        ]

        status, response, raw_text = self._make_request("GET", endpoint)

        if status == 200:
            found_sensitive = []
            for field in sensitive_fields:
                if field in str(response).lower():
                    found_sensitive.append(field)

            if found_sensitive:
                findings.append(
                    {
                        "vulnerability_type": "response_field_leakage",
                        "endpoint": endpoint,
                        "method": "GET",
                        "exposed_fields": found_sensitive,
                        "severity": "medium",
                        "description": f"Sensitive fields may be exposed in response: {', '.join(found_sensitive)}",
                    }
                )

        return findings

    def _test_nested_object_assignment(
        self, endpoint: str
    ) -> List[Dict[str, Any]]:
        """Test nested object mass assignment vulnerabilities."""
        findings = []

        nested_payloads = [
            {"user": {"role": "admin"}},
            {"metadata": {"isAdmin": True}},
            {"profile": {"isPremium": True}},
            {"settings": {"emailVerified": True}},
            {"permissions": {"canDelete": True, "canModify": True}},
        ]

        for payload in nested_payloads:
            status, response, _ = self._make_request("POST", endpoint, body=payload)

            if status == 200 or status == 201:
                for key, nested in payload.items():
                    if key in response:
                        if isinstance(nested, dict):
                            for subkey, subvalue in nested.items():
                                nested_path = f"{key}.{subkey}"
                                if (
                                    isinstance(response[key], dict)
                                    and subkey in response[key]
                                    and response[key][subkey] == subvalue
                                ):
                                    findings.append(
                                        {
                                            "vulnerability_type": "nested_mass_assignment",
                                            "endpoint": endpoint,
                                            "method": "POST",
                                            "injected_path": nested_path,
                                            "injected_value": subvalue,
                                            "severity": "high",
                                            "description": f"Nested field '{nested_path}' was accepted without validation",
                                        }
                                    )

        return findings

    def scan_endpoint(
        self, endpoint: str, method: str = "POST", auth: Optional[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Scan a specific endpoint for mass assignment vulnerabilities."""
        findings = []

        status, response, _ = self._make_request(method, endpoint, auth=auth)

        if status != 0:
            self.tested_endpoints.append({"endpoint": endpoint, "method": method})

            findings.extend(
                self._test_parameter_injection(endpoint, response)
            )
            findings.extend(self._test_field_enumeration(endpoint, response))
            findings.extend(self._test_patch_vulnerability(endpoint))
            findings.extend(self._test_response_field_leakage(endpoint))
            findings.extend(self._test_nested_object_assignment(endpoint))

            self.vulnerabilities.extend(findings)

        return findings

    def scan_endpoints(
        self,
        endpoints: List[str],
        auth: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """Scan multiple endpoints and return aggregated results."""
        for endpoint in endpoints:
            self.scan_endpoint(endpoint, auth=auth)

        return self.get_report()

    def get_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report."""
        critical = [v for v in self.vulnerabilities if v.get("severity") == "critical"]
        high = [v for v in self.vulnerabilities if v.get("severity") == "high"]
        medium = [v for v in self.vulnerabilities if v.get("severity") == "medium"]

        return {
            "scan_summary": {
                "total_vulnerabilities": len(self.vulnerabilities),
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "endpoints_tested": len(self.tested_endpoints),
            },
            "vulnerabilities": self.vulnerabilities,
            "endpoints_tested": self.tested_endpoints,
            "timestamp": time.time(),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Mass Assignment Vulnerability Scanner for REST APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 script.py --url http://localhost:8000 --endpoint /api/users
  python3 script.py --url http://api.example.com --endpoint /api/profile --endpoint /api/settings
  python3 script.py --url http://api.example.com --endpoint /api/users --auth user:password
  python3 script.py --url http://api.example.com --endpoint /api/users --output report.json
        """,
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of the API to scan (e.g., http://localhost:8000)",
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        required=True,
        help="API endpoint(s) to scan (can specify multiple times)",
    )
    parser.add_argument(
        "--auth",
        help="Basic authentication credentials (format: username:password)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report (default: stdout)",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    auth = None
    if args.auth:
        if ":" not in args.auth:
            print("Error: Auth format must be username:password", file=sys.stderr)
            sys.exit(1)
        username, password = args.auth.split(":", 1)
        auth = (username, password)

    scanner = MassAssignmentScanner(
        base_url=args.url,
        verify_ssl=not args.no_verify_ssl,
        timeout=args.timeout,
    )

    if args.verbose:
        print(f"[*] Scanning {args.url}", file=sys.stderr)
        print(f"[*] Endpoints: {args.endpoint}", file=sys.stderr)
        if auth:
            print(f"[*] Using authentication: {auth[0]}", file=sys.stderr)

    report = scanner.scan_endpoints(args.endpoint, auth=auth)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        if args.verbose:
            print(f"[+] Report saved to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(report, indent=2))

    if args.verbose:
        summary = report["scan_summary"]
        print(
            f"\n[+] Scan complete: {summary['total_vulnerabilities']} vulnerabilities found",
            file=sys.stderr,
        )
        print(
            f"    Critical: {summary['critical']}, High: {summary['high']}, Medium: {summary['medium']}",
            file=sys.stderr,
        )

    critical_count = report["scan_summary"]["critical"]
    if critical_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
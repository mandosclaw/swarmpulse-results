#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Mass assignment scanner
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-28T21:59:28.771Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Mass Assignment Scanner - API Authentication Bypass Detector
MISSION: API Authentication Bypass Detector
AGENT: @quinn
DATE: 2025-01-20
CATEGORY: Engineering

Detects fields accepted but not in API spec, flags privilege escalation vectors.
Scans for mass assignment vulnerabilities in API endpoints.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin
import re


@dataclass
class FieldDefinition:
    """Represents an API field specification"""
    name: str
    type: str
    required: bool = False
    writable: bool = True
    sensitive: bool = False


@dataclass
class MassAssignmentVulnerability:
    """Represents a detected mass assignment vulnerability"""
    endpoint: str
    method: str
    field_name: str
    field_type: str
    severity: str
    reason: str
    suggested_action: str


class APISpecParser:
    """Parses API specifications and extracts field definitions"""
    
    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.endpoints = {}
        self._parse_spec()
    
    def _parse_spec(self):
        """Parse OpenAPI/Swagger-like specification"""
        if "paths" in self.spec:
            for path, path_item in self.spec["paths"].items():
                for method, operation in path_item.items():
                    if method not in ["get", "post", "put", "patch", "delete"]:
                        continue
                    
                    endpoint_key = f"{method.upper()} {path}"
                    self.endpoints[endpoint_key] = self._extract_fields(operation)
    
    def _extract_fields(self, operation: Dict[str, Any]) -> Dict[str, FieldDefinition]:
        """Extract field definitions from an operation"""
        fields = {}
        
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema", {})
            
            if "properties" in schema:
                for field_name, field_schema in schema["properties"].items():
                    required = field_name in schema.get("required", [])
                    writable = field_schema.get("readOnly", False) is False
                    sensitive = any(kw in field_name.lower() for kw in 
                                  ["password", "secret", "token", "api_key", "admin"])
                    
                    field_type = field_schema.get("type", "unknown")
                    fields[field_name] = FieldDefinition(
                        name=field_name,
                        type=field_type,
                        required=required,
                        writable=writable,
                        sensitive=sensitive
                    )
        
        return fields
    
    def get_writable_fields(self, endpoint: str) -> Set[str]:
        """Get all writable fields for an endpoint"""
        if endpoint not in self.endpoints:
            return set()
        
        return {field.name for field in self.endpoints[endpoint].values() 
                if field.writable}
    
    def get_sensitive_fields(self, endpoint: str) -> Set[str]:
        """Get all sensitive fields for an endpoint"""
        if endpoint not in self.endpoints:
            return set()
        
        return {field.name for field in self.endpoints[endpoint].values() 
                if field.sensitive}


class MassAssignmentScanner:
    """Scans for mass assignment vulnerabilities"""
    
    PRIVILEGE_ESCALATION_PATTERNS = [
        "admin", "is_admin", "role", "is_staff", "is_superuser",
        "permissions", "groups", "access_level", "privilege",
        "is_moderator", "is_operator", "account_type"
    ]
    
    SENSITIVE_PATTERNS = [
        "password", "secret", "token", "api_key", "private_key",
        "credit_card", "ssn", "email", "phone", "birthdate"
    ]
    
    def __init__(self, api_spec: Dict[str, Any]):
        self.spec_parser = APISpecParser(api_spec)
        self.vulnerabilities: List[MassAssignmentVulnerability] = []
    
    def scan_endpoint(self, endpoint: str, method: str, 
                     accepted_fields: Dict[str, Any]) -> List[MassAssignmentVulnerability]:
        """
        Scan an endpoint for mass assignment vulnerabilities
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            accepted_fields: Dictionary of fields accepted by the API
        
        Returns:
            List of detected vulnerabilities
        """
        endpoint_key = f"{method} {endpoint}"
        spec_fields = self.spec_parser.endpoints.get(endpoint_key, {})
        spec_field_names = set(spec_fields.keys())
        accepted_field_names = set(accepted_fields.keys())
        
        findings = []
        
        # 1. Detect fields not in specification
        undocumented_fields = accepted_field_names - spec_field_names
        for field_name in undocumented_fields:
            findings.append(self._create_vulnerability(
                endpoint, method, field_name,
                accepted_fields[field_name],
                severity="HIGH",
                reason="Field accepted but not documented in API specification",
                suggested_action="Remove field from accepted parameters or document in API spec"
            ))
        
        # 2. Detect privilege escalation vectors
        for field_name in accepted_field_names:
            if any(pattern in field_name.lower() 
                   for pattern in self.PRIVILEGE_ESCALATION_PATTERNS):
                
                spec_writable = (spec_field_names and 
                               field_name in spec_fields and 
                               spec_fields[field_name].writable)
                
                if not spec_field_names or spec_writable:
                    findings.append(self._create_vulnerability(
                        endpoint, method, field_name,
                        accepted_fields[field_name],
                        severity="CRITICAL",
                        reason="Privilege escalation vector - privilege/role field is writable",
                        suggested_action="Mark field as read-only or remove from API spec"
                    ))
        
        # 3. Detect sensitive field mass assignment
        for field_name in accepted_field_names:
            if any(pattern in field_name.lower() 
                   for pattern in self.SENSITIVE_PATTERNS):
                
                if field_name not in spec_field_names:
                    findings.append(self._create_vulnerability(
                        endpoint, method, field_name,
                        accepted_fields[field_name],
                        severity="HIGH",
                        reason="Sensitive field accepted but not documented",
                        suggested_action="Remove or properly validate sensitive field"
                    ))
        
        # 4. Detect IDOR-related mass assignment
        idor_patterns = ["id", "user_id", "account_id", "org_id", "resource_id"]
        for field_name in accepted_field_names:
            if any(pattern in field_name.lower() for pattern in idor_patterns):
                if field_name not in spec_field_names:
                    findings.append(self._create_vulnerability(
                        endpoint, method, field_name,
                        accepted_fields[field_name],
                        severity="MEDIUM",
                        reason="ID field accepted but not documented - potential IDOR",
                        suggested_action="Validate authorization for resource access"
                    ))
        
        self.vulnerabilities.extend(findings)
        return findings
    
    def _create_vulnerability(self, endpoint: str, method: str, 
                             field_name: str, field_value: Any,
                             severity: str, reason: str,
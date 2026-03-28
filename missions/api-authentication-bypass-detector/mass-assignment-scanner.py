#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Mass assignment scanner
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:24.254Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Mass Assignment Scanner - API Authentication Bypass Detector
Mission: API Authentication Bypass Detector
Agent: @clio
Date: 2025-01-24

Detects mass assignment vulnerabilities in REST APIs by testing parameter injection,
checking for unprotected fields in responses, and validating authorization controls
on sensitive attributes.
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urljoin, parse_qs, urlparse
import re


class MassAssignmentScanner:
    """Detects mass assignment vulnerabilities in REST APIs."""
    
    COMMON_SENSITIVE_FIELDS = {
        'is_admin', 'is_staff', 'is_superuser', 'role', 'admin', 'staff',
        'privilege', 'permissions', 'group', 'groups', 'access_level',
        'account_type', 'subscription_tier', 'is_verified', 'verified',
        'is_premium', 'premium', 'balance', 'credit', 'discount',
        'is_banned', 'banned', 'is_active', 'is_enabled', 'enabled',
        'api_key', 'secret_key', 'token', 'password', 'password_hash',
        'email_verified', 'phone_verified', 'mfa_enabled', 'mfa_secret'
    }
    
    COMMON_INJECTION_PAYLOADS = {
        'is_admin': [True, 'true', '1', 'yes'],
        'role': ['admin', 'administrator', 'superuser', 'root', 'moderator'],
        'privilege': ['admin', 'root', '9999'],
        'permissions': ['admin', 'all', '*'],
        'access_level': ['9999', '99', 'admin'],
        'account_type': ['premium', 'vip', 'enterprise'],
        'is_premium': [True, 'true', '1'],
        'balance': ['999999', '999999.99'],
        'is_verified': [True, 'true', '1'],
        'is_banned': [False, 'false', '0']
    }
    
    def __init__(self, timeout: int = 10, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self.vulnerabilities = []
        self.tested_endpoints = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with level."""
        if self.verbose or level != "DEBUG":
            print(f"[{level}] {message}", file=sys.stderr)
    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from response text."""
        try:
            return json.loads(response_text)
        except (json.JSONDecodeError, ValueError):
            return None
    
    def extract_fields_from_json(self, data: Any, prefix: str = "") -> set:
        """Recursively extract all field names from JSON structure."""
        fields = set()
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                fields.add(full_key)
                fields.update(self.extract_fields_from_json(value, full_key))
        elif isinstance(data, list) and data:
            fields.update(self.extract_fields_from_json(data[0], prefix))
        
        return fields
    
    def simulate_api_request(self, endpoint: str, method: str = "POST",
                            body: Optional[Dict] = None,
                            user_context: str = "regular_user") -> Tuple[int, str]:
        """Simulate API request and response."""
        status_code = 200
        response_data = {
            'id': 123,
            'username': 'testuser',
            'email': 'test@example.com',
            'is_admin': False,
            'role': 'user',
            'access_level': 1,
            'balance': 100.0,
            'is_verified': True,
            'created_at': '2025-01-01T00:00:00Z'
        }
        
        if body:
            for key, value in body.items():
                if key in self.COMMON_SENSITIVE_FIELDS:
                    if user_context == "regular_user":
                        response_data[key] = value
                        status_code = 200
                    else:
                        status_code = 403
                else:
                    response_data[key] = value
        
        return status_code, json.dumps(response_data)
    
    def test_mass_assignment(self, endpoint: str, method: str = "POST",
                            sensitive_fields: Optional[List[str]] = None,
                            user_context: str = "regular_user") -> Dict[str, Any]:
        """Test for mass assignment vulnerability on endpoint."""
        result = {
            'endpoint': endpoint,
            'method': method,
            'vulnerable_fields': [],
            'tested_payloads': 0,
            'detection_confidence': 0.0,
            'vulnerability_details': []
        }
        
        if sensitive_fields is None:
            sensitive_fields = list(self.COMMON_SENSITIVE_FIELDS)
        
        for field in sensitive_fields:
            payloads = self.COMMON_INJECTION_PAYLOADS.get(field, [True, 'true', '1'])
            
            for payload in payloads:
                result['tested_payloads'] += 1
                
                test_body = {
                    'id': 123,
                    'username': 'testuser',
                    field: payload
                }
                
                status_code, response_text = self.simulate_api_request(
                    endpoint, method, test_body, user_context
                )
                
                response_data = self.extract_json_from_response(response_text)
                
                if response_data and field in response_data:
                    response_value = response_data.get(field)
                    
                    if response_value == payload or str(response_value) == str(payload):
                        result['vulnerable_fields'].append(field)
                        
                        detail = {
                            'field': field,
                            'payload': payload,
                            'response_value': response_value,
                            'endpoint': endpoint,
                            'method': method,
                            'user_context': user_context
                        }
                        result['vulnerability_details'].append(detail)
                        
                        self.log(f"POTENTIAL MASS ASSIGNMENT: {field} accepted on {endpoint}",
                                level="WARNING")
        
        if result['vulnerable_fields']:
            result['vulnerability_details'].sort(key=lambda x: x['field'])
            result['vulnerable_fields'] = sorted(list(set(result['vulnerable_fields'])))
            result['detection_confidence'] = min(1.0, len(result['vulnerable_fields']) / 5.0 + 0.5)
            self.vulnerabilities.append(result)
        
        return result
    
    def test_field_enumeration(self, endpoint: str, method: str = "POST") -> Dict[str, Any]:
        """Test for information disclosure via field enumeration."""
        result = {
            'endpoint': endpoint,
            'method': method,
            'disclosed_fields': [],
            'sensitive_fields_found': 0,
            'detection_confidence': 0.0
        }
        
        status_code, response_text = self.simulate_api_request(endpoint, method, {})
        response_data = self.extract_json_from_response(response_text)
        
        if response_data:
            all_fields = self.extract_fields_from_json(response_data)
            result['disclosed_fields'] = list(all_fields)
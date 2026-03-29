#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OAuth 2.0 implementation audit
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-29T13:17:47.453Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
OAuth 2.0 Implementation Audit
Mission: API Authentication Bypass Detector
Agent: @clio
Date: 2024
"""

import argparse
import json
import re
import sys
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple, Any, Optional


class OAuth2Auditor:
    """Comprehensive OAuth 2.0 implementation audit scanner."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings: List[Dict[str, Any]] = []
        self.severity_levels = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "INFO": 0
        }
    
    def log(self, message: str):
        if self.verbose:
            print(f"[DEBUG] {message}")
    
    def add_finding(self, severity: str, finding_type: str, description: str, 
                   remediation: str, endpoint: str = ""):
        """Record a security finding."""
        self.findings.append({
            "severity": severity,
            "type": finding_type,
            "description": description,
            "remediation": remediation,
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat()
        })
        self.log(f"Found {severity}: {finding_type}")
    
    def audit_client_registration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit OAuth 2.0 client registration endpoint."""
        results = {
            "endpoint": config.get("registration_endpoint", ""),
            "issues": []
        }
        
        # Check for open registration (no authentication required)
        if config.get("registration_requires_auth") is False:
            self.add_finding(
                "HIGH",
                "OPEN_CLIENT_REGISTRATION",
                "Client registration endpoint allows unauthenticated registration",
                "Require authentication or implement CAPTCHA/approval workflow for client registration",
                config.get("registration_endpoint", "")
            )
            results["issues"].append("Open client registration enabled")
        
        # Check for client secret handling
        if config.get("client_secret_in_url") is True:
            self.add_finding(
                "CRITICAL",
                "CLIENT_SECRET_EXPOSURE",
                "Client secret transmitted in URL parameters",
                "Always transmit client credentials via request body with POST method",
                config.get("registration_endpoint", "")
            )
            results["issues"].append("Client secret exposure in URL")
        
        # Check for HTTPS enforcement
        if config.get("uses_https") is False:
            self.add_finding(
                "CRITICAL",
                "UNENCRYPTED_TRANSPORT",
                "OAuth endpoint does not use HTTPS",
                "Enforce HTTPS/TLS 1.2+ for all OAuth endpoints",
                config.get("registration_endpoint", "")
            )
            results["issues"].append("No HTTPS enforcement")
        
        # Check for redirect URI validation
        if config.get("redirect_uri_validation") == "none":
            self.add_finding(
                "CRITICAL",
                "REDIRECT_URI_VALIDATION_MISSING",
                "No redirect URI validation performed",
                "Implement strict whitelist-based redirect URI validation",
                config.get("registration_endpoint", "")
            )
            results["issues"].append("Missing redirect URI validation")
        elif config.get("redirect_uri_validation") == "loose":
            self.add_finding(
                "HIGH",
                "REDIRECT_URI_VALIDATION_LOOSE",
                "Redirect URI validation uses loose matching (wildcard, suffix matching)",
                "Implement exact matching for redirect URIs with full domain validation",
                config.get("registration_endpoint", "")
            )
            results["issues"].append("Loose redirect URI validation")
        
        return results
    
    def audit_authorization_endpoint(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit OAuth 2.0 authorization endpoint."""
        results = {
            "endpoint": config.get("authorization_endpoint", ""),
            "issues": []
        }
        
        # Check for response_type parameter manipulation
        if config.get("validates_response_type") is False:
            self.add_finding(
                "MEDIUM",
                "INVALID_RESPONSE_TYPE_ACCEPTED",
                "Authorization endpoint accepts invalid response_type values",
                "Validate response_type against registered values (code, token, id_token, etc.)",
                config.get("authorization_endpoint", "")
            )
            results["issues"].append("Invalid response_type not rejected")
        
        # Check for PKCE enforcement
        if config.get("pkce_required") is False and config.get("pkce_supported") is True:
            self.add_finding(
                "HIGH",
                "PKCE_NOT_ENFORCED",
                "PKCE not enforced for public clients (browser/mobile)",
                "Enforce PKCE (RFC 7636) for all public client flows",
                config.get("authorization_endpoint", "")
            )
            results["issues"].append("PKCE not enforced")
        
        # Check for state parameter validation
        if config.get("validates_state") is False:
            self.add_finding(
                "CRITICAL",
                "STATE_PARAMETER_NOT_VALIDATED",
                "State parameter not validated or enforcement optional",
                "Validate state parameter in authorization response; make it mandatory",
                config.get("authorization_endpoint", "")
            )
            results["issues"].append("State parameter not validated")
        
        # Check for state parameter strength
        if config.get("state_length_minimum", 0) < 20:
            self.add_finding(
                "MEDIUM",
                "WEAK_STATE_PARAMETER",
                "State parameter minimum length less than 20 bytes",
                "Enforce minimum 32-byte cryptographically random state values",
                config.get("authorization_endpoint", "")
            )
            results["issues"].append("Weak state parameter enforcement")
        
        # Check for implicit flow usage
        if config.get("allows_implicit_flow") is True:
            self.add_finding(
                "HIGH",
                "IMPLICIT_FLOW_ENABLED",
                "Implicit grant flow is enabled and allowed",
                "Disable implicit flow; use authorization code flow with PKCE instead",
                config.get("authorization_endpoint", "")
            )
            results["issues"].append("Implicit flow enabled")
        
        # Check for form_post response mode
        if config.get("form_post_response_mode_default") is True:
            results["issues"].append("Form POST response mode enabled (security check)")
        
        return results
    
    def audit_token_endpoint(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit OAuth 2.0 token endpoint."""
        results = {
            "endpoint": config.get("token_endpoint", ""),
            "issues": []
        }
        
        # Check for token endpoint authentication
        if config.get("token_endpoint_auth_required") is False:
            self.add_finding(
                "HIGH",
                "TOKEN_ENDPOINT_NO_AUTH",
                "Token endpoint does not require client authentication",
                "Require client authentication (client_secret, mTLS, or signed JWT) at token endpoint",
                config.get("token_endpoint", "")
            )
            results["issues"].append("No token endpoint authentication")
        
        # Check for client authentication methods
        auth_methods = config.get("token_endpoint_auth_methods", [])
        if "client_secret_basic" not in auth_methods and "client_secret_post" in auth_methods:
            self.add_finding(
                "MEDIUM",
                "WEAK_CLIENT_AUTH_METHOD",
                "Only client_secret_post method supported (client_secret_basic more secure)",
                "Support client_secret_basic as primary method; only use _post as fallback",
                config.get("token_endpoint", "")
            )
            results["issues"].append("Weak client authentication method")
        
        # Check for client_secret plaintext storage (conceptual)
        if config.get("client_secret_hashed") is False:
            self.add_finding(
                "CRITICAL",
                "CLIENT_SECRET_PLAINTEXT_STORAGE",
                "Client secrets stored in plaintext in database",
                "Hash all client secrets using bcrypt/scrypt with salt before storage",
                config.get("token_endpoint", "")
            )
            results["issues"].append("Client secrets not hashed")
        
        # Check for token expiration
        if config.get("access_token_expires_seconds", 0) > 3600:
            self.add_finding(
                "MEDIUM",
                "LONG_TOKEN_LIFETIME",
                "Access token lifetime exceeds 1 hour",
                "Reduce access token lifetime to 15-60 minutes based on use case",
                config.get("token_endpoint", "")
            )
            results["issues"].append("Long token lifetime")
        
        # Check for refresh token rotation
        if config.get("refresh_token_rotation") is False:
            self.add_finding(
                "MEDIUM",
                "NO_REFRESH_TOKEN_ROTATION",
                "Refresh tokens not rotated on use",
                "Implement refresh token rotation to limit compromise window",
                config.get("token_endpoint", "")
            )
            results["issues"].append("No refresh token rotation")
        
        # Check for refresh token expiration
        if config.get("refresh_token_expires_seconds", float('inf')) == float('inf'):
            self.add_finding(
                "HIGH",
                "REFRESH_TOKEN_NO_EXPIRATION",
                "Refresh tokens do not expire",
                "Set refresh token expiration to 7-30 days or implement absolute timeout",
                config.get("token_endpoint", "")
            )
            results["issues"].append("Refresh token never expires")
        
        return results
    
    def audit_resource_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit OAuth 2.0 resource server implementation."""
        results = {
            "endpoint": config.get("resource_endpoint", ""),
            "issues": []
        }
        
        # Check for token validation
        if config.get("validates_token_signature") is False:
            self.add_finding(
                "CRITICAL",
                "TOKEN_SIGNATURE_NOT_VALIDATED",
                "Resource server does not validate token signature",
                "Always validate JWT signature using provider's public key",
                config.get("resource_endpoint", "")
            )
            results["issues"].append("Token signature not validated")
        
        # Check for token expiration validation
        if config.get("validates_token_expiration") is False:
            self.add_finding(
                "CRITICAL",
                "TOKEN_EXPIRATION_NOT_VALIDATED",
                "Resource server does not validate token expiration",
                "Always check 'exp' claim and reject expired tokens",
                config.get("resource_endpoint", "")
            )
            results["issues"].append("Token expiration not validated")
        
        # Check for scope validation
        if config.get("validates_token_scope") is False:
            self.add_finding(
                "HIGH",
                "SCOPE_NOT_VALIDATED",
                "Resource server does not validate token scope",
                "Validate 'scope' claim matches required scopes for requested resource",
                config.get("resource_endpoint", "")
            )
            results["issues"].append("Scope not validated")
        
        # Check for token binding
        if config.get("supports_token_binding") is False:
            results["issues"].append("Token binding not supported (informational)")
        
        # Check for revocation endpoint
        if config.get("has_revocation_endpoint") is False:
            self.add_finding(
                "MEDIUM",
                "NO_REVOCATION_ENDPOINT",
                "No token revocation endpoint available",
                "Implement RFC 7009 token revocation endpoint for user logout",
                config.get("resource_endpoint", "")
            )
            results["issues"].append("No revocation endpoint")
        
        return results
    
    def audit_jwt_handling(self, token_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audit JWT token construction and validation."""
        results = {
            "tokens_analyzed": len(token_samples),
            "issues": []
        }
        
        for idx, token_data in enumerate(token_samples):
            # Check for algorithm verification bypass (alg: none)
            if token_data.get("algorithm") == "none":
                self.add_finding(
                    "CRITICAL",
                    "JWT_ALG_NONE_ACCEPTED",
                    f"JWT token {idx} uses 'none' algorithm",
                    "Reject 'alg: none' tokens; validate algorithm against whitelist",
                    f"token_{idx}"
                )
                results["issues"].append(f"Token {idx}: alg=none vulnerability")
            
            # Check for weak algorithm
            if token_data.get("algorithm", "").startswith("HS"):
                self.add_finding(
                    "MEDIUM",
                    "WEAK_JWT_ALGORITHM",
                    f"JWT token {idx} uses HMAC-based algorithm (HS256/HS384/HS512)",
                    "Use RSA (RS256+) or EC (ES256+) algorithms for asymmetric verification",
                    f"token_{idx}"
                )
                results["issues"].append(f"Token {idx}: weak HMAC algorithm")
            
            # Check for missing header validation
            if "algorithm" not in token_data or "typ" not in token_data:
                self.add_finding(
                    "HIGH",
                    "JWT_HEADER_VALIDATION_WEAK",
                    f"JWT token {idx} missing algorithm or type validation",
                    "Validate and enforce JWT headers; set alg whitelist",
                    f"token_{idx}"
                )
                results["issues"].append(f"Token {idx}: weak header validation")
            
            # Check for critical claims
            payload = token_data.get("payload", {})
            required_claims = {"iss", "sub", "aud", "exp"}
            missing_claims = required_claims - set(payload.keys())
            
            if missing_claims:
                self.add_finding(
                    "HIGH",
                    "JWT_MISSING_CLAIMS",
                    f"JWT token {idx} missing claims: {missing_claims}",
                    f"Include all required claims: {required_claims}",
                    f"token_{idx}"
                )
                results["issues"].append(f"Token {idx}: missing claims {missing_claims}")
        
        return results
    
    def audit_scope_handling(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit OAuth 2.0 scope handling and principle of least privilege."""
        results = {
            "scope_model": config.get("scope_model", "unknown"),
            "issues": []
        }
        
        # Check for overly broad default scopes
        default_scopes = config.get("default_scopes", [])
        if not default_scopes or len(default_scopes) == 0:
            self.add_finding(
                "MEDIUM",
                "NO_DEFAULT_SCOPE",
                "No default scope specified; uses all requested scopes",
                "Define minimal default scope; require explicit user consent for expanded scopes",
                ""
            )
            results["issues"].append("No default scope defined")
        
        defined_scopes = config.get("defined_scopes", {})
        for scope_name, scope_desc in defined_scopes.items():
            if len(scope_name) > 50:
                results["issues"].append(f"Scope '{scope_name}' excessively permissive")
        
        # Check for scope granularity
        scope_count = len(defined_scopes)
        if scope_count < 5:
            self.add_finding(
                "MEDIUM",
                "INSUFFICIENT_SCOPE_GRANULARITY",
                f"Only {scope_count} scopes defined; insufficient granularity",
                "Implement fine-grained scopes for different API operations",
                ""
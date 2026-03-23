#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OAuth 2.0 Implementation Audit
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T13:09:44.382Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
OAuth 2.0 Implementation Audit — checks for common misconfigurations and vulnerabilities.
"""
import argparse
import json
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

KNOWN_ISSUES = {
    "implicit_flow": "Implicit flow leaks access tokens in URL fragments. Use PKCE.",
    "no_state": "Missing 'state' parameter enables CSRF attacks.",
    "no_pkce": "Authorization Code flow without PKCE is vulnerable to code interception.",
    "weak_redirect": "Redirect URI contains wildcard or broad pattern.",
    "token_in_url": "Access token found in URL — it will appear in server logs.",
    "http_redirect": "Redirect URI uses HTTP (not HTTPS) — token may be intercepted.",
    "short_expiry_missing": "No token expiry information returned from token endpoint.",
    "no_scope": "No scope restriction — token has unrestricted access.",
}

@dataclass
class Finding:
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    code: str
    detail: str

@dataclass
class AuditResult:
    target: str
    findings: list = field(default_factory=list)
    raw_discovery: dict = field(default_factory=dict)

    def add(self, severity: str, code: str, detail: str = ""):
        self.findings.append(Finding(severity, code, detail or KNOWN_ISSUES.get(code, "")))

    def summary(self) -> dict:
        by_sev = {}
        for f in self.findings:
            by_sev.setdefault(f.severity, []).append({"code": f.code, "detail": f.detail})
        return {"target": self.target, "total_findings": len(self.findings), "by_severity": by_sev}

def fetch_oidc_discovery(base_url: str) -> Optional[dict]:
    for path in ["/.well-known/openid-configuration", "/.well-known/oauth-authorization-server"]:
        try:
            r = requests.get(base_url.rstrip("/") + path, timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            log.debug("Discovery fetch failed: %s", e)
    return None

def audit_discovery(result: AuditResult, doc: dict):
    grant_types = doc.get("grant_types_supported", [])
    if "implicit" in grant_types:
        result.add("HIGH", "implicit_flow")
    response_types = doc.get("response_types_supported", [])
    if any("token" in rt for rt in response_types):
        result.add("HIGH", "implicit_flow", "response_types_supported includes 'token' (implicit)")
    pkce_methods = doc.get("code_challenge_methods_supported", [])
    if not pkce_methods:
        result.add("HIGH", "no_pkce", "PKCE (code_challenge_methods_supported) not advertised")
    token_ep = doc.get("token_endpoint", "")
    if token_ep.startswith("http://"):
        result.add("CRITICAL", "http_redirect", f"token_endpoint uses HTTP: {token_ep}")

def audit_auth_url(result: AuditResult, auth_url: str):
    parsed = urllib.parse.urlparse(auth_url)
    params = urllib.parse.parse_qs(parsed.query)
    if not params.get("state"):
        result.add("HIGH", "no_state")
    if not params.get("code_challenge"):
        result.add("HIGH", "no_pkce", "Authorization URL missing code_challenge")
    redirect = params.get("redirect_uri", [""])[0]
    if redirect.startswith("http://"):
        result.add("HIGH", "http_redirect", f"redirect_uri uses HTTP: {redirect}")
    if re.search(r"[*?]", redirect):
        result.add("HIGH", "weak_redirect", f"Wildcard redirect_uri: {redirect}")
    rt = params.get("response_type", [""])[0]
    if "token" in rt:
        result.add("HIGH", "implicit_flow", f"response_type={rt}")
    if not params.get("scope"):
        result.add("MEDIUM", "no_scope")

def run_audit(target: str, auth_url: Optional[str] = None) -> AuditResult:
    result = AuditResult(target=target)
    discovery = fetch_oidc_discovery(target)
    if discovery:
        result.raw_discovery = discovery
        audit_discovery(result, discovery)
        log.info("Audited OIDC discovery document")
    else:
        log.warning("No OIDC discovery found at %s", target)
    if auth_url:
        audit_auth_url(result, auth_url)
    return result

def main():
    parser = argparse.ArgumentParser(description="OAuth 2.0 Implementation Auditor")
    parser.add_argument("target", help="Base URL of authorization server")
    parser.add_argument("--auth-url", help="Full authorization URL to inspect")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    args = parser.parse_args()

    result = run_audit(args.target, args.auth_url)
    report = result.summary()
    print(json.dumps(report, indent=2))
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        log.info("Report written to %s", args.output)

if __name__ == "__main__":
    main()

# API Authentication Bypass Detector

> **SwarmPulse Mission** | Agent: @clio | Status: COMPLETED

Automated security scanner detecting JWT vulnerabilities, IDOR flaws, OAuth
misconfigurations, mass assignment, and broken rate limiting in REST APIs.

## Scripts

| Script | Description |
|--------|-------------|
| `jwt-token-weakness-scanner.py` | Tests JWT implementations for alg:none, weak secrets, missing exp, and typ confusion |
| `jwt-confusion-test-suite.py` | Full test suite for RS256→HS256 confusion attacks and key confusion vulnerabilities |
| `idor-fuzzer.py` | Enumerates API endpoints for IDOR by mutating IDs in requests and comparing responses |
| `oauth-2-0-implementation-audit.py` | Checks OAuth flows for open redirects, PKCE bypass, implicit flow misuse |
| `mass-assignment-scanner.py` | Sends extra JSON fields to POST/PUT endpoints to detect unfiltered mass assignment |
| `api-rate-limiting-analysis.py` | Stress-tests rate limiting by sending burst traffic and measuring enforcement accuracy |
| `api-key-rotation-enforcer.py` | Checks for long-lived API keys and alerts when keys exceed rotation policy age |
| `ci-cd-integration.py` | Wraps all scanners for CI/CD pipeline integration with JUnit XML output |

## Requirements

```bash
pip install requests pyjwt cryptography pytest
```

## Usage

```bash
# Scan for JWT weaknesses
python jwt-token-weakness-scanner.py --token "eyJ..." --target https://api.example.com

# Run IDOR fuzzer
python idor-fuzzer.py --base-url https://api.example.com/users/{id} --start 1 --end 100

# OAuth audit
python oauth-2-0-implementation-audit.py --auth-url https://api.example.com/oauth/authorize

# Full CI scan (outputs JUnit XML)
python ci-cd-integration.py --target https://staging-api.example.com --output results.xml
```

## Mission Context

API authentication bypass is the #1 cause of data breaches in SaaS companies.
This scanner runs in CI/CD pipelines to catch auth issues before they reach production.

> ⚠️ **For authorized security testing only.** Always obtain written permission before scanning.

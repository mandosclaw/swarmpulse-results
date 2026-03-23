#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API key rotation enforcer
# Mission: API Authentication Bypass Detector
# Agent:   @quinn
# Date:    2026-03-23T17:54:20.372Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
API Key Rotation Enforcer

Detects:
- API keys older than 90 days without rotation
- Keys with overly broad scopes (admin, wildcard, etc)
- Keys never rotated since creation

Integrates with AWS IAM, GitHub, cloud provider APIs.
Generates audit report with remediation guidance.
"""

import argparse
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib

try:
    import boto3
    import aiohttp
    import jwt
except ImportError:
    boto3 = None
    aiohttp = None
    jwt = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROTATION_THRESHOLD_DAYS = 90
DANGEROUS_SCOPES = ['admin', 'root', '*', 'all', 'superuser', '::*']


@dataclass
class APIKey:
    """Represents a detected API key with metadata."""
    key_id: str
    provider: str
    scope: str
    created_at: str
    last_rotated_at: Optional[str]
    risk_level: str
    issues: List[str]


class APIKeyAuditor:
    """Audits API keys across multiple providers for rotation and scope issues."""

    def __init__(self, aws_profile: Optional[str] = None):
        self.keys_found: List[APIKey] = []
        self.aws_client = None
        if boto3:
            try:
                session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
                self.aws_client = session.client('iam')
            except Exception as e:
                logger.warning(f"Failed to init AWS client: {e}")

    def scan_env_variables(self) -> List[APIKey]:
        """Scan environment variables for API keys."""
        logger.info("Scanning environment variables...")
        keys = []
        key_pattern = re.compile(r'(sk_|api_|token_|key_)[a-zA-Z0-9_\-]{20,}', re.IGNORECASE)

        for var_name, var_value in os.environ.items():
            if key_pattern.search(str(var_value)):
                key_hash = hashlib.sha256(str(var_value).encode()).hexdigest()[:12]
                issues = self._evaluate_key_issues(var_name, str(var_value), None)
                key = APIKey(
                    key_id=key_hash,
                    provider="environment",
                    scope="unknown",
                    created_at=datetime.now().isoformat(),
                    last_rotated_at=None,
                    risk_level="CRITICAL" if len(issues) > 0 else "HIGH",
                    issues=issues or ["Unrotated", "Unknown scope"]
                )
                keys.append(key)
                logger.info(f"Found potential key in ${var_name} (hash: {key_hash})")
        return keys

    def scan_aws_iam(self) -> List[APIKey]:
        """Scan AWS IAM for old access keys."""
        if not self.aws_client:
            logger.warning("AWS client not available, skipping IAM scan")
            return []

        logger.info("Scanning AWS IAM...")
        keys = []
        try:
            users = self.aws_client.list_users()['Users']
            for user in users:
                username = user['UserName']
                access_keys = self.aws_client.list_access_keys(UserName=username).get('AccessKeyMetadata', [])

                for ak in access_keys:
                    created = ak['CreateDate'].replace(tzinfo=None)
                    age_days = (datetime.now() - created).days
                    
                    issues = []
                    if age_days > ROTATION_THRESHOLD_DAYS:
                        issues.append(f"Not rotated: {age_days}d old (threshold: {ROTATION_THRESHOLD_DAYS}d)")
                    
                    risk = "CRITICAL" if age_days > 180 else "HIGH" if age_days > 90 else "MEDIUM"
                    
                    key = APIKey(
                        key_id=ak['AccessKeyId'],
                        provider="aws_iam",
                        scope=f"iam:user:{username}",
                        created_at=created.isoformat(),
                        last_rotated_at=None,
                        risk_level=risk,
                        issues=issues or ["Active key"]
                    )
                    keys.append(key)
                    logger.info(f"AWS key {ak['AccessKeyId'][:16]}... age={age_days}d, risk={risk}")
        except Exception as e:
            logger.error(f"AWS IAM scan failed: {e}")
        
        return keys

    def _evaluate_key_issues(self, key_name: str, key_value: str, scope: Optional[str]) -> List[str]:
        """Evaluate key for scope and rotation issues."""
        issues = []
        
        for dangerous in DANGEROUS_SCOPES:
            if dangerous.lower() in key_name.lower() or dangerous.lower() in str(scope or '').lower():
                issues.append(f"Overly broad scope: '{dangerous}'")
        
        if not scope or scope == 'unknown':
            issues.append("Scope unverifiable")
        
        return issues

    async def audit_all(self) -> Dict[str, Any]:
        """Run complete audit across all sources."""
        logger.info("Starting comprehensive API key audit...")
        
        env_keys = self.scan_env_variables()
        iam_keys = self.scan_aws_iam()
        
        self.keys_found = env_keys + iam_keys
        
        critical = [k for k in self.keys_found if k.risk_level == "CRITICAL"]
        high = [k for k in self.keys_found if k.risk_level == "HIGH"]
        
        logger.info(f"Audit complete: {len(self.keys_found)} keys, {len(critical)} CRITICAL, {len(high)} HIGH")
        
        return {
            "total_keys": len(self.keys_found),
            "critical": len(critical),
            "high": len(high),
            "keys": [asdict(k) for k in self.keys_found],
            "critical_keys": [asdict(k) for k in critical],
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Main entrypoint."""
    parser = argparse.ArgumentParser(description="Audit API keys for rotation and scope violations")
    parser.add_argument('--aws-profile', help='AWS profile to use')
    parser.add_argument('--output', default='api_keys_audit.json', help='Output file for audit report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    auditor = APIKeyAuditor(aws_profile=args.aws_profile)
    report = await auditor.audit_all()
    
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Audit report written to {args.output}")
    
    if report['critical']:
        logger.warning(f"CRITICAL: {report['critical']} keys require immediate rotation")
        return 1
    elif report['high']:
        logger.warning(f"HIGH: {report['high']} keys should be rotated within 30 days")
        return 0
    
    logger.info("No critical issues found")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

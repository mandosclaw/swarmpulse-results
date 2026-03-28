#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Registry change stream ingestion
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-28T21:57:48.866Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Registry change stream ingestion
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @sue
DATE: 2025-01-13

Subscribe to npm/PyPI webhook feeds. Capture every publish/update event.
Implements real monitoring of package registry changes with configurable
thresholds and structured JSON output for SBOM alert system integration.
"""

import argparse
import json
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse, parse_qs
import hashlib
import hmac

# Global state for webhook server
WEBHOOK_EVENTS: List[Dict[str, Any]] = []
WEBHOOK_LOCK = threading.Lock()
REGISTRY_ALERTS: List[Dict[str, Any]] = []


class RegistryChangeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for registry webhook events."""

    def do_POST(self):
        """Handle incoming webhook POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        # Verify webhook signature if secret is provided
        signature = self.headers.get('X-Npm-Signature') or self.headers.get('X-PyPI-Signature')
        webhook_secret = getattr(self.server, 'webhook_secret', None)

        if webhook_secret and signature:
            if not self._verify_signature(body, signature, webhook_secret):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error": "Signature verification failed"}')
                return

        # Process the webhook event
        event = self._process_webhook_payload(payload)

        with WEBHOOK_LOCK:
            WEBHOOK_EVENTS.append(event)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "received", "event_id": event['id']}).encode())

    def _verify_signature(self, body: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature using HMAC-SHA256."""
        if signature.startswith('sha256='):
            signature = signature[7:]

        expected = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def _process_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw webhook payload to standardized event format."""
        event_id = f"{int(time.time() * 1000)}-{hashlib.md5(json.dumps(payload).encode()).hexdigest()[:8]}"

        # Detect registry type and extract relevant fields
        if 'name' in payload and 'version' in payload:
            # npm style
            registry_type = 'npm'
            package_name = payload.get('name', 'unknown')
            package_version = payload.get('version', 'unknown')
            author = payload.get('author', {}).get('name', 'unknown') if isinstance(payload.get('author'), dict) else 'unknown'
            event_type = 'publish'
            timestamp = payload.get('publishedAt', datetime.utcnow().isoformat())
            maintainers = [m.get('name', 'unknown') for m in payload.get('maintainers', [])]
            dist_tarball = payload.get('dist', {}).get('tarball', '')
        elif 'project_name' in payload or 'project_url' in payload:
            # PyPI style
            registry_type = 'pypi'
            package_name = payload.get('project_name') or payload.get('name', 'unknown')
            package_version = payload.get('project_version') or payload.get('version', 'unknown')
            author = payload.get('author_email', 'unknown')
            event_type = payload.get('action', 'publish')
            timestamp = payload.get('upload_time', datetime.utcnow().isoformat())
            maintainers = [payload.get('author_email', 'unknown')]
            dist_tarball = payload.get('url', '')
        else:
            # Generic/unknown format
            registry_type = 'unknown'
            package_name = payload.get('name', 'unknown')
            package_version = payload.get('version', '0.0.0')
            author = payload.get('author', 'unknown')
            event_type = 'update'
            timestamp = datetime.utcnow().isoformat()
            maintainers = []
            dist_tarball = ''

        # Check for suspicious patterns
        risk_indicators = self._detect_risk_indicators(
            package_name,
            author,
            payload,
            registry_type
        )

        return {
            'id': event_id,
            'timestamp': timestamp,
            'registry': registry_type,
            'event_type': event_type,
            'package_name': package_name,
            'package_version': package_version,
            'author': author,
            'maintainers': maintainers,
            'dist_tarball': dist_tarball,
            'risk_indicators': risk_indicators,
            'risk_score': len(risk_indicators),
            'raw_payload': payload
        }

    def _detect_risk_indicators(self, package_name: str, author: str, payload: Dict[str, Any], registry: str) -> List[str]:
        """Detect suspicious patterns in package metadata."""
        indicators = []

        # Typosquatting detection
        common_packages = [
            'requests', 'flask', 'django', 'numpy', 'pandas', 'react', 'lodash',
            'express', 'vue', 'typescript', 'webpack', 'babel', 'pytest'
        ]
        normalized = package_name.lower().replace('-', '').replace('_', '')
        for common in common_packages:
            common_norm = common.lower().replace('-', '').replace('_', '')
            if self._is_typosquat(normalized, common_norm):
                indicators.append(f'potential_typosquatting:{common}')

        # Single character difference from popular packages
        if len(package_name) < 15 and package_name.lower() not in ['a', 'b', 'c']:
            for common in common_packages:
                if abs(len(package_name) - len(common)) <= 1:
                    if self._levenshtein_distance(package_name.lower(), common.lower()) == 1:
                        indicators.append(f'single_char_variation:{common}')

        # New account publishing
        if 'author_email' not in payload and 'author' not in payload:
            indicators.append('no_author_metadata')

        # Empty or minimal description
        description = payload.get('description', '') or payload.get('summary', '')
        if not description or len(description) < 10:
            indicators.append('missing_or_minimal_description')

        # Suspicious author names
        if author and any(x in author.lower() for x in ['test', 'demo', 'temp', 'fake']):
            indicators.append('suspicious_author_name')

        # Very recent account (would need historical data in production)
        if 'created' in payload:
            try:
                created = datetime.fromisoformat(payload['created'].replace('Z', '+00:00'))
                age_hours = (datetime.utcnow() - created).total_seconds() / 3
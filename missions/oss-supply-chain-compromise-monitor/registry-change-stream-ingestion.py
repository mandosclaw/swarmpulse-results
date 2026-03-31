#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Registry change stream ingestion
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @sue
# Date:    2026-03-31T17:58:17.967Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Registry change stream ingestion
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @sue
DATE: 2024-01-15

Subscribe to npm/PyPI webhook feeds. Capture every publish/update event.
Implements real monitoring loop with registry event ingestion, validation,
and structured JSON output for SBOM alert system integration.
"""

import argparse
import json
import sys
import time
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from datetime import datetime
from queue import Queue
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

# Global event queue for thread-safe event handling
EVENT_QUEUE: Queue = Queue()
MONITORED_PACKAGES: Dict[str, Any] = {}
ALERT_THRESHOLD_SCORE = 0.6


class RegistryEvent:
    """Represents a normalized registry event from npm/PyPI."""
    
    def __init__(self, registry: str, package_name: str, version: str,
                 event_type: str, author: str, timestamp: float,
                 raw_data: Dict[str, Any]):
        self.registry = registry
        self.package_name = package_name
        self.version = version
        self.event_type = event_type
        self.author = author
        self.timestamp = timestamp
        self.raw_data = raw_data
        self.risk_score = 0.0
        self.alerts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "registry": self.registry,
            "package_name": self.package_name,
            "version": self.version,
            "event_type": self.event_type,
            "author": self.author,
            "risk_score": self.risk_score,
            "alerts": self.alerts,
            "raw_event": self.raw_data
        }


class PyPIWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for PyPI webhook events."""
    
    def do_POST(self):
        """Handle incoming PyPI webhook POST request."""
        if self.path != "/pypi":
            self.send_response(404)
            self.end_headers()
            return
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode("utf-8"))
            event = self._parse_pypi_event(data)
            if event:
                EVENT_QUEUE.put(event)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "accepted"}).encode())
            else:
                self.send_response(400)
                self.end_headers()
        except Exception as e:
            print(f"[ERROR] PyPI webhook parse error: {e}", file=sys.stderr)
            self.send_response(500)
            self.end_headers()
    
    def _parse_pypi_event(self, data: Dict[str, Any]) -> Optional[RegistryEvent]:
        """Parse PyPI JSON event format."""
        try:
            if "action" not in data or "package" not in data:
                return None
            
            action = data["action"]
            package_name = data["package"]["name"]
            version = data.get("release", {}).get("version", "unknown")
            author = data.get("actor", {}).get("username", "unknown")
            
            event = RegistryEvent(
                registry="pypi",
                package_name=package_name,
                version=version,
                event_type=action,
                author=author,
                timestamp=time.time(),
                raw_data=data
            )
            return event
        except (KeyError, TypeError):
            return None
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


class NPMEventFetcher:
    """Polls npm change stream API for new package events."""
    
    def __init__(self, since_seq: Optional[int] = None):
        self.since_seq = since_seq or 0
        self.base_url = "https://replicate.npmjs.com"
        self.changes_url = f"{self.base_url}/_changes"
        self.db_url = f"{self.base_url}"
    
    def fetch_changes(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Fetch latest changes from npm change stream."""
        try:
            params = f"?since={self.since_seq}&limit={limit}&include_docs=true"
            url = self.changes_url + params
            
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "OSS-Supply-Chain-Monitor/1.0")
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
            return None
    
    def parse_changes(self, changes_data: Dict[str, Any]) -> List[RegistryEvent]:
        """Parse npm changes into normalized events."""
        events = []
        
        if "results" not in changes_data:
            return events
        
        for result in changes_data["results"]:
            try:
                doc_id = result.get("id", "")
                doc = result.get("doc", {})
                
                if doc_id.startswith("_design"):
                    continue
                
                package_name = doc_id
                versions = doc.get("versions", {})
                
                if not versions:
                    continue
                
                latest_version = max(versions.keys(), 
                                   key=lambda v: versions[v].get("_npmUser", {}).get("date", ""),
                                   default=None)
                
                if not latest_version:
                    continue
                
                version_data = versions[latest_version]
                author = version_data.get("_npmUser", {}).get("name", "unknown")
                
                event = RegistryEvent(
                    registry="npm",
                    package_name=package_name,
                    version=latest_version,
                    event_type="publish",
                    author=author,
                    timestamp=time.time(),
                    raw_data={"id": doc_id, "doc": doc}
                )
                events.append(event)
                
                self.since_seq = result.get("seq", self.since_seq)
                
            except (KeyError, ValueError, TypeError):
                continue
        
        return events


class SupplyChainAnalyzer:
    """Analyzes registry events for supply chain risks."""
    
    SUSPICIOUS_PATTERNS = {
        "typosquatting": [
            r"^[a-z0-9]*[\-_][a-z0-9]*$",  # Common typo pattern with dash/underscore
        ],
        "suspicious_author_names": [
            "admin", "root", "test", "demo", "temp"
        ],
        "suspicious_keywords": [
            "crypto", "miner", "bitcoin", "exploit", "malware", "backdoor"
        ]
    }
    
    RISKY_VERSION_PATTERNS = [
        r"^0\.0\.",  # Zero-version (often test/throwaway)
        r"^999\.",   # Intentionally high version
    ]
    
    def __init__(self):
        self.known_good_packages = set()
        self.known_authors = set()
    
    def analyze_event(self, event: RegistryEvent) -> float:
        """
        Analyze event and return risk score (0.0-1.0).
        """
        score = 0.0
        
        # Check for suspicious package name patterns (typosquatting)
        if self._check_typosquatting(event.package_name):
            score += 0.3
            event.alerts.append("potential_typosquatting_detected")
        
        # Check for suspicious author
        if self._is_suspicious_author(event.author):
            score += 0.25
            event.alerts.append("suspicious_author_name")
        
        # Check for suspicious version pattern
        if self._is_risky_version(event.version):
            score += 0.15
            event.alerts.append("suspicious_version_pattern")
        
        # Check package metadata for red flags
        risk_from_metadata = self._analyze_metadata(event)
        score += risk_from_metadata
        
        # First release from new author (possible dependency confusion)
        if event.version == "1.0.0" and event.author not in self.known_authors:
            score += 0.2
            event.alerts.append("first_release_new_author")
        
        # Rapid consecutive updates (indicator of post-publish injection)
        if self._detect_rapid_updates(event):
            score += 0.15
            event.alerts.append("rapid_consecutive_updates")
        
        event.risk_score = min(score, 1.0)
        return event.risk_score
    
    def _check_typosquatting(self, package_name: str) -> bool:
        """Check for common typosquatting patterns."""
        import re
        
        # Check against known packages with character confusion
        name_lower = package_name.lower()
        
        # Detect common typosquatting: missing/added/swapped chars near popular packages
        popular_packages = ["react", "lodash", "express", "requests", "django", "flask"]
        
        for pkg in popular_packages:
            if self._levenshtein_distance(name_lower, pkg) <= 2:
                return True
        
        # Check pattern matches
        for pattern in self.SUSPICIOUS_PATTERNS["typosquatting"]:
            if re.match(pattern, name_lower):
                return True
        
        return False
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _is_suspicious_author(self, author: str) -> bool:
        """Check for suspicious author names."""
        author_lower = author.lower()
        
        for suspicious in self.SUSPICIOUS_PATTERNS["suspicious_author_names"]:
            if suspicious in author_lower:
                return True
        
        return False
    
    def _is_risky_version(self, version: str) -> bool:
        """Check for risky version patterns."""
        import re
        
        for pattern in self.RISKY_VERSION_PATTERNS:
            if re.match(pattern, version):
                return True
        
        return False
    
    def _analyze_metadata(self, event: RegistryEvent) -> float:
        """Analyze package metadata for red flags."""
        score = 0.0
        
        # Check for suspicious keywords in package name or description
        package_name_lower = event.package_name.lower()
        
        for keyword in self.SUSPICIOUS_PATTERNS["suspicious_keywords"]:
            if keyword in package_name_lower:
                score += 0.1
        
        # Check raw data for suspicious content
        if "description" in event.raw_data:
            description = str(event.raw_data.get("description", "")).lower()
            for keyword in self.SUSPICIOUS_PATTERNS["suspicious_keywords"]:
                if keyword in description:
                    score += 0.1
        
        return min(score, 0.25)
    
    def _detect_rapid_updates(self, event: RegistryEvent) -> bool:
        """Detect if this package has rapid consecutive updates (XZ-style pattern)."""
        # In a real system, this would query historical update timestamps
        # For now, we implement a placeholder that checks timing patterns
        
        if event.package_name not in MONITORED_PACKAGES:
            MONITORED_PACKAGES[event.package_name] = {
                "last_update": event.timestamp,
                "update_count": 1,
                "versions": [event.version]
            }
            return False
        
        pkg_info = MONITORED_PACKAGES[event.package_name]
        time_delta = event.timestamp - pkg_info["last_update"]
        
        # Flag if multiple updates within 30 minutes
        if time_delta < 1800 and event.version not in pkg_info["versions"]:
            pkg_info["update_count"] += 1
            if pkg_info["update_count"] >= 3:
                return True
        
        pkg_info["last_update"] = event.timestamp
        if event.version not in pkg_info["versions"]:
            pkg_info["versions"].append(event.version)
        
        return False


class RegistryMonitor:
    """Main monitoring orchestrator."""
    
    def __init__(self, pypi_port: int = 8080, npm_poll_interval: int = 300):
        self.pypi_port = pypi_port
        self.npm_poll_interval = npm_poll_interval
        self.analyzer = SupplyChainAnalyzer()
        self.npm_fetcher = NPMEventFetcher()
        self.running = False
        self.alerts = []
    
    def start_pypi_webhook_server(self):
        """Start HTTP server for PyPI webhooks."""
        server = HTTPServer(("127.0.0.1", self.pypi_port), PyPIWebhookHandler)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"[INFO] PyPI webhook server started on port {self.pypi_port}")
        return server
    
    def start_npm_polling(self):
        """Start npm change stream polling thread."""
        def poll_npm():
            while self.running:
                changes = self.npm_fetcher.fetch_changes(limit=100)
                if changes:
                    events = self.npm_fetcher.parse_changes(changes)
                    for event in events:
                        EVENT_QUEUE.put(event)
                
                time.sleep(self.npm_poll_interval)
        
        npm_thread = Thread(target=poll_npm, daemon=True)
        npm_thread.start()
        print(f"[INFO] npm change stream polling started (interval: {self.npm_poll_interval}s)")
        return npm_thread
    
    def process_events(self, output_file: Optional[str] = None):
        """Main event processing loop."""
        self.running = True
        
        print("[INFO] Registry change stream monitor started")
        print("[INFO] Listening for package events...")
        
        try:
            while self.running:
                try:
                    event = EVENT_QUEUE.get(timeout=5)
                    
                    # Analyze event
                    risk_score = self.analyzer.analyze_event(event)
                    
                    # Log event
                    event_dict = event.to_dict()
                    print(json.dumps(event_dict, indent=2))
                    
                    # Generate alert if threshold exceeded
                    if risk_score >= ALERT_THRESHOLD_SCORE:
                        alert = {
                            "severity": self._classify_severity(risk_score),
                            "timestamp": datetime.now().isoformat(),
                            "event": event_dict
                        }
                        self.alerts.append(alert)
                        print(f"[ALERT] High-risk package detected: {event.package_name}@{event.version}")
                        print(f"[ALERT] Risk Score: {risk_score:.2f}")
                        print(f"[ALERT] Concerns: {', '.join(event.alerts)}")
                    
                    # Write to output file if specified
                    if output_file:
                        with open(output_file, "a") as f:
                            f.write(json.dumps(event_dict) + "\n")
                
                except Exception as e:
                    if str(e) != "Empty":  # Ignore queue.Empty timeout exception
                        print(f"[ERROR] Event processing error: {e}", file=sys.stderr)
        
        except KeyboardInterrupt:
            self.running = False
            print("\n[INFO] Monitor shutting down...")
    
    def _classify_severity(self, risk_score: float) -> str:
        """Classify alert severity based on risk score."""
        if risk_score >= 0.9:
            return "CRITICAL"
        elif risk_score >= 0.8:
            return "HIGH"
        elif risk_score >= 0.7:
            return "MEDIUM"
        else:
            return "LOW"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OSS Supply Chain Compromise Monitor - Registry Change Stream Ingestion"
    )
    
    parser.add_argument(
        "--registries",
        type=str,
        default="npm,pypi",
        help="Comma-separated list of registries to monitor (npm, pypi)"
    )
    
    parser.add_argument(
        "--pypi-webhook-port",
        type=int,
        default=8080,
        help="Port for PyPI webhook server"
    )
    
    parser.add_argument(
        "--npm-poll-interval",
        type=int,
        default=300,
        help="Polling interval for npm change stream (seconds)"
    )
    
    parser.add_argument(
        "--risk-threshold",
        type=float,
        default=0.6,
        help="Risk score threshold for alerting (0.0-1.0)"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Optional file to write all events to (JSONL format)"
    )
    
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode with synthetic events"
    )
    
    args = parser.parse_args()
    
    global ALERT_THRESHOLD_SCORE
    ALERT_THRESHOLD_SCORE = args.risk_threshold
    
    monitor = RegistryMonitor(
        pypi_port=args.pypi_webhook_port,
        npm_poll_interval=args.npm_poll_interval
    )
    
    registries = [r.strip() for r in args.registries.split(",")]
    
    if args.demo_mode:
        print("[INFO] Running in demo mode with synthetic events")
        demo_run(monitor, args.output_file)
    else:
        if "pypi" in registries:
            monitor.start_pypi_webhook_server()
        
        if "npm" in registries:
            monitor.start_npm_polling()
        
        monitor.process_events(output_file=args.output_file)


def demo_run(monitor: RegistryMonitor, output_file: Optional[str] = None):
    """Run monitor in demo mode with synthetic test events."""
    
    print("[INFO] Generating synthetic test events...")
    
    # Synthetic test events
    test_events = [
        RegistryEvent(
            registry="npm",
            package_name="lodash-pro",  # Typosquatting
            version="1.0.0",
            event_type="publish",
            author="unknown_author",
            timestamp=time.time(),
            raw_data={"description": "A utility library"}
        ),
        RegistryEvent(
            registry="pypi",
            package_name="django-payment",
            version="2.0.0",
            event_type="publish",
            author="john_smith",
            timestamp=time.time() + 1,
            raw_data={"description": "Django payment processor"}
        ),
        RegistryEvent(
            registry="npm",
            package_name="express-miner",  # Suspicious keyword
            version="1.0.0",
            event_type="publish",
            author="crypto_dev",
            timestamp=time.time() + 2,
            raw_data={"description": "High performance miner"}
        ),
        RegistryEvent(
            registry="npm",
            package_name="react-utils",
            version="0.0.1",  # Zero version
            event_type="publish",
            author="admin",  # Suspicious author name
            timestamp=time.time() + 3,
            raw_data={"description": "React utilities"}
        ),
        RegistryEvent(
            registry="pypi",
            package_name="requests-fork",
            version="2.31.0",
            event_type="publish",
            author="jane_developer",
            timestamp=time.time() + 4,
            raw_data={"description": "HTTP library fork"}
        ),
    ]
    
    # Process synthetic events
    for event in test_events:
        EVENT_QUEUE.put(event)
    
    # Process queue
    alerts_found = []
    while not EVENT_QUEUE.empty():
        try:
            event = EVENT_QUEUE.get_nowait()
            
            # Analyze event
            risk_score = monitor.analyzer.analyze_event(event)
            
            # Output event
            event_dict = event.to_dict()
            print("\n" + json.dumps(event_dict, indent=2))
            
            # Check for alerts
            if risk_score >= ALERT_THRESHOLD_SCORE:
                alert = {
                    "severity": monitor._classify_severity(risk_score),
                    "timestamp": datetime.now().isoformat(),
                    "event": event_dict
                }
                alerts_found.append(alert)
                print(f"\n⚠️  [ALERT] High-risk package detected!")
                print(f"   Package: {event.package_name}@{event.version}")
                print(f"   Risk Score: {risk_score:.2f}")
                print(f"   Concerns: {', '.join(event.alerts)}")
            
            # Write to output file if specified
            if output_file:
                with open(output_file, "a") as f:
                    f.write(json.dumps(event_dict) + "\n")
        
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
    
    # Summary
    print(f"\n[INFO] Demo complete. Processed {len(test_events)} events.")
    print(f"[INFO] High-risk alerts: {len(alerts_found)}")
    
    if alerts_found:
        print("\n[SUMMARY] ALERTS GENERATED:")
        for alert in alerts_found:
            print(f"  - {alert['severity']}: {alert['event']['package_name']}")


if __name__ == "__main__":
    main()
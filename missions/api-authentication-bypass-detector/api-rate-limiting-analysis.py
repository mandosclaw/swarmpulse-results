#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API rate limiting analysis
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-28T22:03:23.636Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: API rate limiting analysis
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2025-01-01

Automated security scanner that detects JWT vulnerabilities, IDOR flaws, OAuth 
misconfigurations, mass assignment, and broken rate limiting in REST APIs.
Specifically implements API rate limiting analysis to identify rate limit bypass
vulnerabilities and weaknesses in rate limiting enforcement.
"""

import argparse
import json
import time
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import hashlib


@dataclass
class RateLimitViolation:
    """Represents a detected rate limit violation"""
    endpoint: str
    client_id: str
    timestamp: str
    requests_made: int
    limit: int
    window_seconds: int
    violation_type: str
    severity: str
    evidence: List[str]


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint"""
    endpoint: str
    requests_per_window: int
    window_seconds: int
    detection_enabled: bool
    bypass_patterns: List[str]


class APIRateLimitAnalyzer:
    """Analyzes API traffic for rate limiting vulnerabilities"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.request_history: Dict[str, List[Tuple[float, Dict]]] = defaultdict(list)
        self.violations: List[RateLimitViolation] = []
        self.rate_limit_configs: Dict[str, RateLimitConfig] = {}
        self.bypass_indicators = {
            'ip_rotation': [],
            'header_manipulation': [],
            'parameter_obfuscation': [],
            'distributed_requests': [],
            'timing_patterns': [],
            'token_refresh_abuse': []
        }
    
    def add_rate_limit_config(self, config: RateLimitConfig):
        """Add or update rate limit configuration for endpoint"""
        self.rate_limit_configs[config.endpoint] = config
        if self.verbose:
            print(f"[*] Configured rate limit for {config.endpoint}: "
                  f"{config.requests_per_window} requests per {config.window_seconds}s")
    
    def analyze_request(self, endpoint: str, request_data: Dict) -> Optional[RateLimitViolation]:
        """Analyze single request for rate limit violations"""
        
        if endpoint not in self.rate_limit_configs:
            return None
        
        config = self.rate_limit_configs[endpoint]
        if not config.detection_enabled:
            return None
        
        timestamp = time.time()
        client_id = request_data.get('client_id', 'unknown')
        
        # Create request record
        request_record = (timestamp, request_data)
        self.request_history[f"{endpoint}:{client_id}"].append(request_record)
        
        # Check for violations
        window_start = timestamp - config.window_seconds
        requests_in_window = [
            req for req in self.request_history[f"{endpoint}:{client_id}"]
            if req[0] >= window_start
        ]
        
        violation = None
        if len(requests_in_window) > config.requests_per_window:
            evidence = self._gather_evidence(endpoint, client_id, requests_in_window, request_data)
            bypass_type = self._detect_bypass_pattern(endpoint, client_id, requests_in_window, request_data)
            
            violation = RateLimitViolation(
                endpoint=endpoint,
                client_id=client_id,
                timestamp=datetime.fromtimestamp(timestamp).isoformat(),
                requests_made=len(requests_in_window),
                limit=config.requests_per_window,
                window_seconds=config.window_seconds,
                violation_type=bypass_type,
                severity=self._calculate_severity(len(requests_in_window), config.requests_per_window),
                evidence=evidence
            )
            self.violations.append(violation)
            
            if self.verbose:
                print(f"[!] VIOLATION: {endpoint} by {client_id} - "
                      f"{len(requests_in_window)} requests in {config.window_seconds}s "
                      f"(limit: {config.requests_per_window})")
        
        return violation
    
    def _detect_bypass_pattern(self, endpoint: str, client_id: str, 
                               requests: List[Tuple[float, Dict]], 
                               current_request: Dict) -> str:
        """Detect specific rate limit bypass patterns"""
        
        if len(requests) < 2:
            return "unknown"
        
        # Check for IP rotation
        ips = set(req[1].get('source_ip', '') for req in requests)
        if len(ips) > 1 and len(ips) >= len(requests) * 0.5:
            self.bypass_indicators['ip_rotation'].append({
                'endpoint': endpoint,
                'client_id': client_id,
                'unique_ips': len(ips),
                'total_requests': len(requests)
            })
            return "ip_rotation"
        
        # Check for header manipulation (User-Agent changes)
        user_agents = set(req[1].get('user_agent', '') for req in requests)
        if len(user_agents) > len(requests) * 0.7:
            self.bypass_indicators['header_manipulation'].append({
                'endpoint': endpoint,
                'client_id': client_id,
                'unique_agents': len(user_agents)
            })
            return "header_manipulation"
        
        # Check for parameter obfuscation (API key rotation)
        api_keys = set(req[1].get('api_key', '') for req in requests)
        if len(api_keys) > 1:
            self.bypass_indicators['parameter_obfuscation'].append({
                'endpoint': endpoint,
                'client_id': client_id,
                'unique_keys': len(api_keys)
            })
            return "parameter_obfuscation"
        
        # Check for distributed pattern (timing variation)
        timestamps = [req[0] for req in requests]
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        if intervals and min(intervals) < 0.01 and max(intervals) > 0.5:
            self.bypass_indicators['timing_patterns'].append({
                'endpoint': endpoint,
                'client_id': client_id,
                'min_interval': min(intervals),
                'max_interval': max(intervals)
            })
            return "timing_manipulation"
        
        # Check for token refresh abuse
        tokens = set(req[1].get('auth_token', '') for req in requests)
        if len(tokens) > len(requests) * 0.3:
            self.bypass_indicators['token_refresh_abuse'].append({
                'endpoint': endpoint,
                'client_id': client_id,
                'unique_tokens': len(tokens)
            })
            return "token_refresh_abuse"
        
        return "brute_force"
    
    def _gather_evidence(self, endpoint: str, client_id: str, 
                        requests: List[Tuple[float, Dict]], 
                        current_request: Dict) -> List[str]:
        """Gather evidence for violation"""
        evidence = []
        
        request_count = len(requests)
        evidence.append(f"Made {request_count} requests in rapid succession")
        
        time_span = requests[-1][0] - requests[0][0]
        if time_span > 0:
            rps = request_count / time_span
            evidence.append(f"Rate: {rps:.2f} requests/second")
        
        # Check response codes
        response_codes = [str(req[1].get('response_code', 'unknown')) for req in requests]
        status_summary = {code: response_codes.count(code) for code in set(response_codes)}
        evidence.append(f"Response codes: {status_summary}")
        
        # Check for similar patterns across requests
        methods = [req[1].get('method', 'unknown') for req in requests]
        if len(set(methods)) == 1:
            evidence.append(f"All requests use same HTTP method: {methods[0]}")
        
        # Check target patterns
        targets = [req[1].get('target', 'unknown') for req in requests]
        unique_targets = len(set(targets))
        evidence.append(f"Targeting {unique_targets} unique resources out of {len(targets)} requests")
        
        return evidence
    
    def _calculate_severity(self, requests_made: int, limit: int) -> str:
        """Calculate severity level of violation"""
        ratio = requests_made / limit if limit > 0 else 1.0
        
        if ratio >= 10:
            return "CRITICAL"
        elif ratio >= 5:
            return "HIGH"
        elif ratio >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_violations_summary(self) -> Dict:
        """Get summary of detected violations"""
        if not self.violations:
            return {
                'total_violations': 0,
                'by_endpoint': {},
                'by_type': {},
                'by_severity': {}
            }
        
        summary = {
            'total_violations': len(self.violations),
            'by_endpoint': defaultdict(int),
            'by_type': defaultdict(int),
            'by_severity': defaultdict(int),
            'violations': []
        }
        
        for violation in self.violations:
            summary['by_endpoint'][violation.endpoint] += 1
            summary['by_type'][violation.violation_type] += 1
            summary['by_severity'][violation.severity] += 1
            summary['violations'].append(asdict(violation))
        
        return summary
    
    def get_bypass_indicators_summary(self) -> Dict:
        """Get summary of detected bypass indicators"""
        return {
            'ip_rotation': len(self.bypass_indicators['ip_rotation']),
            'header_manipulation': len(self.bypass_indicators['header_manipulation']),
            'parameter_obfuscation': len(self.bypass_indicators['parameter_obfuscation']),
            'timing_patterns': len(self.bypass_indicators['timing_patterns']),
            'token_refresh_abuse': len(self.bypass_indicators['token_refresh_abuse']),
            'details': self.bypass_indicators
        }
    
    def export_report(self, filename: Optional[str] = None) -> str:
        """Export analysis report as JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'violations_summary': self.get_violations_summary(),
            'bypass_indicators': self.get_bypass_indicators_summary(),
            'endpoints_monitored': list(self.rate_limit_configs.keys()),
            'total_requests_analyzed': sum(
                len(reqs) for reqs in self.request_history.values()
            )
        }
        
        json_report = json.dumps(report, indent=2, default=str)
        
        if filename:
            with open(filename, 'w') as f:
                f.write(json_report)
            if self.verbose:
                print(f"[*] Report exported to {filename}")
        
        return json_report
    
    def print_report(self):
        """Print formatted analysis report"""
        summary = self.get_violations_summary()
        bypass = self.get_bypass_indicators_summary()
        
        print("\n" + "="*70)
        print("API RATE LIMITING ANALYSIS REPORT")
        print("="*70)
        
        print(f"\n[+] Total Violations Detected: {summary['total_violations']}")
        
        if summary['total_violations'] > 0:
            print("\n[+] Violations by Endpoint:")
            for endpoint, count in summary['by_endpoint'].items():
                print(f"    - {endpoint}: {count}")
            
            print("\n[+] Violations by Type:")
            for vtype, count in summary['by_type'].items():
                print(f"    - {vtype}: {count}")
            
            print("\n[+] Violations by Severity:")
            for severity, count in summary['by_severity'].items():
                print(f"    - {severity}: {count}")
        
        print("\n[+] Bypass Indicators Detected:")
        print(f"    - IP Rotation: {bypass['ip_rotation']}")
        print(f"    - Header Manipulation: {bypass['header_manipulation']}")
        print(f"    - Parameter Obfuscation: {bypass['parameter_obfuscation']}")
        print(f"    - Timing Patterns: {bypass['timing_patterns']}")
        print(f"    - Token Refresh Abuse: {bypass['token_refresh_abuse']}")
        
        print("\n" + "="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='API Rate Limiting Analysis - Detect rate limit bypass vulnerabilities'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-o', '--output', type=str, help='Output report to file')
    parser.add_argument('--demo', action='store_true', help='Run demonstration mode')
    
    args = parser.parse_args()
    
    # Create analyzer instance
    analyzer = APIRateLimitAnalyzer(verbose=args.verbose)
    
    # Configure endpoints
    analyzer.add_rate_limit_config(RateLimitConfig(
        endpoint='/api/login',
        requests_per_window=5,
        window_seconds=60,
        detection_enabled=True,
        bypass_patterns=['ip_rotation', 'header_manipulation']
    ))
    
    analyzer.add_rate_limit_config(RateLimitConfig(
        endpoint='/api/search',
        requests_per_window=100,
        window_seconds=60,
        detection_enabled=True,
        bypass_patterns=['parameter_obfuscation', 'timing_manipulation']
    ))
    
    analyzer.add_rate_limit_config(RateLimitConfig(
        endpoint='/api/user/profile',
        requests_per_window=20,
        window_seconds=60,
        detection_enabled=True,
        bypass_patterns=['token_refresh_abuse']
    ))
    
    if args.demo:
        # Simulate suspicious API traffic
        print("[*] Running demonstration mode...")
        
        # Simulate brute force attack on login endpoint
        print("\n[*] Simulating brute force attack on /api/login...")
        for i in range(8):
            analyzer.analyze_request('/api/login', {
                'client_id': 'attacker_001',
                'source_ip': f'192.168.1.{100 + i}',
                'user_agent': f'Mozilla/5.0 variant {i}',
                'api_key': f'key_{i}',
                'method': 'POST',
                'target': '/api/login',
                'response_code': 401 if i < 7 else 200,
                'auth_token': f'token_{i}'
            })
            time.sleep(0.01)
        
        # Simulate distributed attack with parameter obfuscation
        print("[*] Simulating distributed attack on /api/search...")
        for i in range(120):
            analyzer.analyze_request('/api/search', {
                'client_id': 'attacker_002',
                'source_ip': f'10.0.0.{i % 50}
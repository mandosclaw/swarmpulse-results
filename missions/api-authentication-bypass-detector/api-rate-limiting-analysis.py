#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API rate limiting analysis
# Mission: API Authentication Bypass Detector
# Agent:   @clio
# Date:    2026-03-31T18:46:06.866Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: API rate limiting analysis
MISSION: API Authentication Bypass Detector
AGENT: @clio
DATE: 2024

Automated security scanner that analyzes API rate limiting configurations,
detects bypass techniques, and identifies misconfigurations that could lead
to authentication/authorization bypass attacks.
"""

import argparse
import json
import sys
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import urllib.request
import urllib.error


@dataclass
class RateLimitHeader:
    """Represents rate limit headers from an API response"""
    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset: Optional[int] = None
    retry_after: Optional[int] = None
    raw_headers: Dict[str, str] = None


@dataclass
class RequestMetrics:
    """Metrics for a single request attempt"""
    timestamp: float
    status_code: int
    response_time: float
    headers: Dict[str, str]
    body_size: int


@dataclass
class RateLimitViolation:
    """Detected rate limit bypass or misconfiguration"""
    violation_type: str
    severity: str
    description: str
    endpoint: str
    details: Dict
    timestamp: datetime


class RateLimitAnalyzer:
    """Analyzes API rate limiting for vulnerabilities and misconfigurations"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.violations: List[RateLimitViolation] = []
        self.rate_limit_configs: Dict[str, RateLimitHeader] = {}
        self.window_size = 60  # seconds

    def parse_rate_limit_headers(self, headers: Dict[str, str]) -> RateLimitHeader:
        """Extract rate limit information from response headers"""
        header_lower = {k.lower(): v for k, v in headers.items()}

        rl = RateLimitHeader(raw_headers=headers)

        # Common header patterns
        limit_keys = ['x-ratelimit-limit', 'ratelimit-limit', 'x-rate-limit-limit']
        remaining_keys = ['x-ratelimit-remaining', 'ratelimit-remaining', 'x-rate-limit-remaining']
        reset_keys = ['x-ratelimit-reset', 'ratelimit-reset', 'x-rate-limit-reset']
        retry_keys = ['retry-after', 'x-retry-after']

        for key in limit_keys:
            if key in header_lower:
                try:
                    rl.limit = int(header_lower[key])
                    break
                except (ValueError, TypeError):
                    pass

        for key in remaining_keys:
            if key in header_lower:
                try:
                    rl.remaining = int(header_lower[key])
                    break
                except (ValueError, TypeError):
                    pass

        for key in reset_keys:
            if key in header_lower:
                try:
                    rl.reset = int(header_lower[key])
                    break
                except (ValueError, TypeError):
                    pass

        for key in retry_keys:
            if key in header_lower:
                try:
                    rl.retry_after = int(header_lower[key])
                    break
                except (ValueError, TypeError):
                    pass

        return rl

    def analyze_response(self, endpoint: str, status_code: int, 
                        response_time: float, headers: Dict[str, str], 
                        body_size: int) -> None:
        """Analyze a single API response for rate limit indicators"""
        timestamp = time.time()
        
        metrics = RequestMetrics(
            timestamp=timestamp,
            status_code=status_code,
            response_time=response_time,
            headers=headers,
            body_size=body_size
        )

        # Store metrics
        self.request_history[endpoint].append(metrics)
        
        # Keep only recent history
        cutoff = timestamp - self.window_size
        while self.request_history[endpoint] and self.request_history[endpoint][0].timestamp < cutoff:
            self.request_history[endpoint].popleft()

        # Parse rate limit headers
        rl_header = self.parse_rate_limit_headers(headers)
        self.rate_limit_configs[endpoint] = rl_header

        # Detect violations
        self._detect_violations(endpoint, metrics, rl_header)

    def _detect_violations(self, endpoint: str, metrics: RequestMetrics, 
                          rl_header: RateLimitHeader) -> None:
        """Detect rate limiting violations and misconfigurations"""

        # Check 1: Missing rate limit headers
        if not rl_header.limit and not rl_header.retry_after:
            self.violations.append(RateLimitViolation(
                violation_type="MISSING_RATE_LIMIT_HEADERS",
                severity="HIGH",
                description="API endpoint missing rate limit headers",
                endpoint=endpoint,
                details={
                    "headers_present": list(metrics.headers.keys()),
                    "status_code": metrics.status_code
                },
                timestamp=datetime.now()
            ))

        # Check 2: Inconsistent rate limit values
        if rl_header.remaining is not None and rl_header.limit is not None:
            if rl_header.remaining > rl_header.limit:
                self.violations.append(RateLimitViolation(
                    violation_type="INCONSISTENT_RATE_LIMIT",
                    severity="MEDIUM",
                    description="Remaining requests exceeds limit",
                    endpoint=endpoint,
                    details={
                        "remaining": rl_header.remaining,
                        "limit": rl_header.limit
                    },
                    timestamp=datetime.now()
                ))

        # Check 3: Rate limit reset in past
        if rl_header.reset is not None:
            current_time = int(time.time())
            if rl_header.reset < current_time:
                self.violations.append(RateLimitViolation(
                    violation_type="INVALID_RESET_TIME",
                    severity="MEDIUM",
                    description="Rate limit reset time is in the past",
                    endpoint=endpoint,
                    details={
                        "reset_time": rl_header.reset,
                        "current_time": current_time
                    },
                    timestamp=datetime.now()
                ))

        # Check 4: Response after rate limit exceeded but no 429
        if rl_header.remaining == 0 and metrics.status_code != 429:
            self.violations.append(RateLimitViolation(
                violation_type="MISSING_429_RESPONSE",
                severity="HIGH",
                description="Rate limit exhausted but no 429 status code returned",
                endpoint=endpoint,
                details={
                    "status_code": metrics.status_code,
                    "remaining": rl_header.remaining
                },
                timestamp=datetime.now()
            ))

        # Check 5: Header injection vulnerability (duplicate headers)
        header_counts = defaultdict(int)
        for header in metrics.headers.keys():
            header_lower = header.lower()
            if 'ratelimit' in header_lower or 'rate-limit' in header_lower:
                header_counts[header_lower] += 1
        
        if any(count > 1 for count in header_counts.values()):
            self.violations.append(RateLimitViolation(
                violation_type="DUPLICATE_RATE_LIMIT_HEADERS",
                severity="LOW",
                description="Duplicate rate limit headers detected",
                endpoint=endpoint,
                details={"header_counts": dict(header_counts)},
                timestamp=datetime.now()
            ))

    def detect_bypass_patterns(self, endpoint: str) -> List[RateLimitViolation]:
        """Detect potential rate limit bypass techniques"""
        violations = []
        history = self.request_history.get(endpoint, [])
        
        if len(history) < 2:
            return violations

        # Check for rapid successive requests after 429
        status_codes = [m.status_code for m in history]
        for i, code in enumerate(status_codes):
            if code == 429 and i + 1 < len(status_codes):
                next_code = status_codes[i + 1]
                if next_code == 200:
                    violations.append(RateLimitViolation(
                        violation_type="BYPASS_AFTER_429",
                        severity="HIGH",
                        description="Successful request immediately after 429 response",
                        endpoint=endpoint,
                        details={
                            "position": i,
                            "next_status": next_code
                        },
                        timestamp=datetime.now()
                    ))

        # Check for timing pattern (exponential backoff not enforced)
        if len(history) > 3:
            response_times = [m.response_time for m in history[-10:]]
            try:
                avg_response_time = statistics.mean(response_times)
                std_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
                
                # If std dev is very low, timing might be controlled/bypassed
                if std_response_time < avg_response_time * 0.1 and avg_response_time < 0.1:
                    violations.append(RateLimitViolation(
                        violation_type="SUSPICIOUSLY_CONSISTENT_TIMING",
                        severity="MEDIUM",
                        description="Requests show suspiciously consistent timing",
                        endpoint=endpoint,
                        details={
                            "average_response_time": avg_response_time,
                            "std_deviation": std_response_time
                        },
                        timestamp=datetime.now()
                    ))
            except (ValueError, statistics.StatisticsError):
                pass

        # Check for increasing remaining count (clock reset bypass)
        remaining_counts = [m for m in history if self.rate_limit_configs.get(endpoint, RateLimitHeader()).remaining]
        if len(remaining_counts) > 2:
            remaining_values = []
            for m in remaining_counts:
                cfg = self.rate_limit_configs.get(endpoint, RateLimitHeader())
                if cfg.remaining:
                    remaining_values.append(cfg.remaining)
            
            if len(remaining_values) > 2:
                for i in range(1, len(remaining_values)):
                    if remaining_values[i] > remaining_values[i-1]:
                        violations.append(RateLimitViolation(
                            violation_type="RATE_LIMIT_RESET_BYPASS",
                            severity="HIGH",
                            description="Rate limit remaining count increased (possible clock reset)",
                            endpoint=endpoint,
                            details={
                                "previous_remaining": remaining_values[i-1],
                                "current_remaining": remaining_values[i]
                            },
                            timestamp=datetime.now()
                        ))
                        break

        return violations

    def analyze_endpoint_behavior(self, endpoint: str) -> Dict:
        """Comprehensive analysis of endpoint rate limiting behavior"""
        history = self.request_history.get(endpoint, [])
        config = self.rate_limit_configs.get(endpoint, RateLimitHeader())

        if not history:
            return {"endpoint": endpoint, "status": "NO_DATA"}

        status_codes = [m.status_code for m in history]
        response_times = [m.response_time for m in history]
        
        analysis = {
            "endpoint": endpoint,
            "total_requests": len(history),
            "time_window_seconds": self.window_size,
            "status_codes": dict(sorted(defaultdict(int, 
                [(code, status_codes.count(code)) for code in set(status_codes)]).items())),
            "rate_limit_config": {
                "limit": config.limit,
                "remaining": config.remaining,
                "reset": config.reset,
                "retry_after": config.retry_after
            },
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "average": statistics.mean(response_times),
                "median": statistics.median(response_times)
            },
            "is_rate_limited": 429 in status_codes,
            "violation_count": len([v for v in self.violations if v.endpoint == endpoint])
        }

        return analysis

    def generate_report(self) -> Dict:
        """Generate comprehensive security report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_endpoints_analyzed": len(self.request_history),
                "total_violations": len(self.violations),
                "critical_violations": len([v for v in self.violations if v.severity == "HIGH"]),
                "rate_limited_endpoints": len([e for e, h in self.request_history.items() 
                                              if 429 in [m.status_code for m in h]])
            },
            "endpoints": {},
            "violations": []
        }

        # Endpoint analysis
        for endpoint in self.request_history.keys():
            report["endpoints"][endpoint] = self.analyze_endpoint_behavior(endpoint)

        # Violations with bypass detection
        all_violations = self.violations.copy()
        for endpoint in self.request_history.keys():
            all_violations.extend(self.detect_bypass_patterns(endpoint))

        # Deduplicate violations by key
        seen = set()
        unique_violations = []
        for v in all_violations:
            key = (v.violation_type, v.endpoint)
            if key not in seen:
                seen.add(key)
                unique_violations.append(v)

        for violation in unique_violations:
            report["violations"].append({
                "type": violation.violation_type,
                "severity": violation.severity,
                "description": violation.description,
                "endpoint": violation.endpoint,
                "details": violation.details,
                "timestamp": violation.timestamp.isoformat()
            })

        return report

    def print_report(self, report: Dict) -> None:
        """Pretty print the analysis report"""
        print("\n" + "="*70)
        print("API RATE LIMITING ANALYSIS REPORT")
        print("="*70)
        print(f"Analysis Time: {report['timestamp']}")
        
        summary = report["summary"]
        print(f"\nSUMMARY:")
        print(f"  Total Endpoints Analyzed: {summary['total_endpoints_analyzed']}")
        print(f"  Total Violations: {summary['total_violations']}")
        print(f"  Critical Violations: {summary['critical_violations']}")
        print(f"  Rate Limited Endpoints: {summary['rate_limited_endpoints']}")

        if report["endpoints"]:
            print(f"\nENDPOINT ANALYSIS:")
            for endpoint, analysis in report["endpoints"].items():
                print(f"\n  Endpoint: {endpoint}")
                if analysis["status"] == "NO_DATA":
                    print(f"    Status: No data available")
                    continue
                print(f"    Requests: {analysis['total_requests']}")
                print(f"    Is Rate Limited: {analysis['is_rate_limited']}")
                print(f"    Status Codes: {analysis['status_codes']}")
                if analysis["rate_limit_config"]["limit"]:
                    print(f"    Rate Limit: {analysis['rate_limit_config']['limit']}")
                    print(f"    Remaining: {analysis['rate_limit_config']['remaining']}")
                print(f"    Avg Response Time: {analysis['response_times']['average']:.4f}s")

        if report["violations"]:
            print(f"\nDETECTED VIOLATIONS:")
            for i, violation in enumerate(report["violations"], 1):
                severity_color = {
                    "HIGH": "🔴",
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }.get(violation["severity"], "⚪")
                
                print(f"\n  {i}. {severity_color} {violation['type']} ({violation['severity']})")
                print(f"     Endpoint: {violation['endpoint']}")
                print(f"     Description: {violation['description']}")
                if violation["details"]:
                    print(f"     Details: {json.dumps(violation['details'], indent=8)}")
        else:
            print(f"\n✅ No violations detected!")

        print("\n" + "="*70 + "\n")


def simulate_api_requests(analyzer: RateLimitAnalyzer, endpoint: str, 
                         num_requests: int, violation_scenario: str = "normal") -> None:
    """Simulate API requests with various rate limiting scenarios"""
    
    for i in range(num_requests):
        if violation_scenario == "normal":
            # Normal scenario: gradual rate limit decrease
            status_code = 200
            remaining = max(0, 100 - i)
            headers = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 3600)
            }
            response_time = 0.05 + (i * 0.001)

        elif violation_scenario == "missing_headers":
            # Missing rate limit headers
            status_code = 200
            headers = {"Content-Type": "application/json"}
            response_time = 0.05

        elif violation_scenario == "inconsistent":
            # Inconsistent rate limit values
            status_code = 200
            remaining = 150 - i  # Can go above limit
            headers = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) - 100)  # Past time
            }
            response_time = 0.05

        elif violation_scenario == "no_429":
            # Rate limit exceeded but no 429
            status_code = 200
            remaining = 0
            headers = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 3600)
            }
            response_time = 0.05

        elif violation_scenario == "bypass_429":
            # Request succeeds after 429
            if i % 3 == 0:
                status_code = 429
                remaining = 0
            else:
                status_code = 200
                remaining = 100
            headers = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 3600)
            }
            response_time = 0.05

        elif violation_scenario == "reset_bypass":
            # Rate limit gets reset (remaining increases)
            remaining = 100 - (i % 20)  # Cycles from 100 to 80 repeatedly
            status_code = 200
            headers = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 3600)
            }
            response_time = 0.05

        else:
            status_code = 200
            headers = {}
            response_time = 0.05

        analyzer.analyze_response(endpoint, status_code, response_time, headers, 1024)
        time.sleep(0.01)  # Small delay between requests


def main():
    parser = argparse.ArgumentParser(
        description="API Rate Limiting Analysis and Bypass Detection Tool"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="/api/users",
        help="API endpoint to analyze (default: /api/users)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=50,
        help="Number of requests to simulate (default: 50)"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["normal", "missing_headers", "inconsistent", "no_429", 
                "bypass_429", "reset_bypass"],
        default="normal",
        help="Simulation scenario to test (default: normal)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save JSON report to file"
    )

    args = parser.parse_args()

    analyzer = RateLimitAnalyzer(verbose=args.verbose)

    print(f"Starting API rate limiting analysis...")
    print(f"Endpoint: {args.endpoint}")
    print(f"Scenario: {args.scenario}")
    print(f"Requests: {args.requests}")

    simulate_api_requests(analyzer, args.endpoint, args.requests, args.scenario)

    report = analyzer.generate_report()
    analyzer.print_report(report)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")

    return 0 if report["summary"]["critical_violations"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
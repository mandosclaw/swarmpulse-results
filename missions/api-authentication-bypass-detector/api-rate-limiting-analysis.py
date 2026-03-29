#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API Rate Limiting Analysis
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-29T13:08:37.064Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
API Rate Limiting Analysis
Mission: API Authentication Bypass Detector
Agent: @sue
Date: 2024-01-15

Analyzes current API rate limiting implementations across production services.
Identifies gaps, recommends improvements, and monitors for rate limit abuse patterns.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import hashlib
import random


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an API endpoint"""
    service_name: str
    endpoint: str
    requests_per_window: int
    window_seconds: int
    rate_limit_header: str
    has_key_based_limiting: bool
    has_ip_based_limiting: bool
    has_user_based_limiting: bool
    burst_allowed: bool
    bypass_patterns: List[str]
    implementation_type: str


@dataclass
class RateLimitAnalysis:
    """Analysis result for a service"""
    service_name: str
    total_endpoints: int
    endpoints_with_limiting: int
    gaps_identified: List[str]
    risk_level: str
    recommendations: List[str]
    compliance_score: float
    implementation_quality: Dict[str, int]


@dataclass
class AbuseEvent:
    """Rate limit abuse event"""
    timestamp: float
    service_name: str
    endpoint: str
    client_identifier: str
    requests_in_window: int
    threshold: int
    excess_percentage: float
    event_type: str


class RateLimitingAnalyzer:
    """Analyzes and monitors API rate limiting implementations"""
    
    def __init__(self, monitoring_window: int = 3600):
        self.monitoring_window = monitoring_window
        self.abuse_events: List[AbuseEvent] = []
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.service_configs: Dict[str, List[RateLimitConfig]] = {}
        self.analysis_results: Dict[str, RateLimitAnalysis] = {}
        
    def add_service_config(self, config: RateLimitConfig) -> None:
        """Add a service configuration to analyze"""
        if config.service_name not in self.service_configs:
            self.service_configs[config.service_name] = []
        self.service_configs[config.service_name].append(config)
    
    def analyze_service(self, service_name: str) -> RateLimitAnalysis:
        """Analyze rate limiting for a specific service"""
        if service_name not in self.service_configs:
            raise ValueError(f"Service {service_name} not configured")
        
        configs = self.service_configs[service_name]
        endpoints_with_limiting = sum(1 for c in configs if c.requests_per_window > 0)
        gaps = self._identify_gaps(configs)
        recommendations = self._generate_recommendations(configs, gaps)
        quality_metrics = self._assess_implementation_quality(configs)
        compliance = self._calculate_compliance_score(configs, gaps)
        risk_level = self._determine_risk_level(compliance)
        
        analysis = RateLimitAnalysis(
            service_name=service_name,
            total_endpoints=len(configs),
            endpoints_with_limiting=endpoints_with_limiting,
            gaps_identified=gaps,
            risk_level=risk_level,
            recommendations=recommendations,
            compliance_score=compliance,
            implementation_quality=quality_metrics
        )
        
        self.analysis_results[service_name] = analysis
        return analysis
    
    def _identify_gaps(self, configs: List[RateLimitConfig]) -> List[str]:
        """Identify gaps in rate limiting implementation"""
        gaps = []
        
        if not configs:
            gaps.append("No rate limiting configured")
            return gaps
        
        endpoints_without_limiting = sum(1 for c in configs if c.requests_per_window == 0)
        if endpoints_without_limiting > 0:
            gaps.append(f"{endpoints_without_limiting} endpoints lack rate limiting")
        
        endpoints_without_key_limiting = sum(1 for c in configs if not c.has_key_based_limiting)
        if endpoints_without_key_limiting > len(configs) * 0.5:
            gaps.append("Majority of endpoints lack API key-based limiting")
        
        endpoints_with_bypass = sum(1 for c in configs if c.bypass_patterns)
        if endpoints_with_bypass > 0:
            total_bypasses = sum(len(c.bypass_patterns) for c in configs)
            gaps.append(f"Potential bypass patterns detected in {endpoints_with_bypass} endpoints ({total_bypasses} patterns)")
        
        endpoints_without_burst = sum(1 for c in configs if not c.burst_allowed)
        if endpoints_without_burst == len(configs):
            gaps.append("No burst allowance configured - may impact legitimate spikes")
        
        endpoints_without_ip_limiting = sum(1 for c in configs if not c.has_ip_based_limiting)
        if endpoints_without_ip_limiting > 0:
            gaps.append(f"IP-based limiting absent on {endpoints_without_ip_limiting} endpoints")
        
        endpoints_without_user_limiting = sum(1 for c in configs if not c.has_user_based_limiting)
        if endpoints_without_user_limiting > 0:
            gaps.append(f"User-based limiting absent on {endpoints_without_user_limiting} endpoints")
        
        return gaps
    
    def _generate_recommendations(self, configs: List[RateLimitConfig], gaps: List[str]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if any("lack rate limiting" in gap for gap in gaps):
            recommendations.append("Implement rate limiting on all public endpoints immediately")
        
        if any("bypass patterns" in gap for gap in gaps):
            recommendations.append("Audit and remediate detected bypass patterns")
        
        low_limits = [c for c in configs if c.requests_per_window < 10]
        if low_limits:
            recommendations.append("Review aggressive rate limits that may impact legitimate users")
        
        if any("burst" in gap for gap in gaps):
            recommendations.append("Configure token bucket algorithm with burst allowance")
        
        if any("IP-based" in gap for gap in gaps):
            recommendations.append("Implement IP-based rate limiting with allowlist for known services")
        
        if any("User-based" in gap for gap in gaps):
            recommendations.append("Implement per-user rate limiting with tier-based quotas")
        
        inconsistent_headers = len(set(c.rate_limit_header for c in configs)) > 1
        if inconsistent_headers:
            recommendations.append("Standardize rate limit response headers across services")
        
        slow_windows = [c for c in configs if c.window_seconds > 3600]
        if slow_windows:
            recommendations.append("Consider shorter rate limit windows for better DDoS mitigation")
        
        recommendations.append("Implement monitoring alerts for rate limit abuse patterns")
        recommendations.append("Add distributed rate limiting for multi-instance deployments")
        
        return recommendations[:10]
    
    def _assess_implementation_quality(self, configs: List[RateLimitConfig]) -> Dict[str, int]:
        """Assess the quality of rate limiting implementations"""
        quality = {
            "key_based": 0,
            "ip_based": 0,
            "user_based": 0,
            "burst_enabled": 0,
            "standardized_headers": 0,
            "appropriate_windows": 0,
            "bypass_free": 0
        }
        
        if not configs:
            return quality
        
        quality["key_based"] = sum(1 for c in configs if c.has_key_based_limiting)
        quality["ip_based"] = sum(1 for c in configs if c.has_ip_based_limiting)
        quality["user_based"] = sum(1 for c in configs if c.has_user_based_limiting)
        quality["burst_enabled"] = sum(1 for c in configs if c.burst_allowed)
        quality["bypass_free"] = sum(1 for c in configs if not c.bypass_patterns)
        
        quality["standardized_headers"] = len(set(c.rate_limit_header for c in configs))
        if quality["standardized_headers"] == 1:
            quality["standardized_headers"] = len(configs)
        else:
            quality["standardized_headers"] = 0
        
        quality["appropriate_windows"] = sum(1 for c in configs if 60 <= c.window_seconds <= 3600)
        
        return quality
    
    def _calculate_compliance_score(self, configs: List[RateLimitConfig], gaps: List[str]) -> float:
        """Calculate compliance score (0-100)"""
        if not configs:
            return 0.0
        
        score = 100.0
        
        endpoints_with_limiting = sum(1 for c in configs if c.requests_per_window > 0)
        coverage_ratio = endpoints_with_limiting / len(configs)
        score -= (1 - coverage_ratio) * 30
        
        score -= len(gaps) * 5
        
        key_limiting_ratio = sum(1 for c in configs if c.has_key_based_limiting) / len(configs)
        score -= (1 - key_limiting_ratio) * 15
        
        ip_limiting_ratio = sum(1 for c in configs if c.has_ip_based_limiting) / len(configs)
        score -= (1 - ip_limiting_ratio) * 10
        
        bypass_ratio = sum(1 for c in configs if c.bypass_patterns) / len(configs)
        score -= bypass_ratio * 20
        
        return max(0.0, min(100.0, score))
    
    def _determine_risk_level(self, compliance_score: float) -> str:
        """Determine risk level based on compliance score"""
        if compliance_score >= 80:
            return "LOW"
        elif compliance_score >= 60:
            return "MEDIUM"
        elif compliance_score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def simulate_requests(self, service_name: str, endpoint: str, 
                         client_id: str, num_requests: int, 
                         abuse_pattern: bool = False) -> None:
        """Simulate requests to track for abuse patterns"""
        if service_name not in self.service_configs:
            raise ValueError(f"Service {service_name} not configured")
        
        endpoint_config = None
        for config in self.service_configs[service_name]:
            if config.endpoint == endpoint:
                endpoint_config = config
                break
        
        if not endpoint_config:
            raise ValueError(f"Endpoint {endpoint} not found in {service_name}")
        
        current_time = time.time()
        key = f"{service_name}:{endpoint}:{client_id}"
        
        if abuse_pattern:
            interval = 0.1
        else:
            interval = endpoint_config.window_seconds / endpoint_config.requests_per_window
        
        for i in range(num_requests):
            request_time = current_time + (i * interval)
            self.request_history[key].append(request_time)
    
    def detect_abuse(self, service_name: str, endpoint: str, 
                    client_id: str, threshold_multiplier: float = 1.5) -> Optional[AbuseEvent]:
        """Detect rate limit abuse for a specific client"""
        if service_name not in self.service_configs:
            return None
        
        endpoint_config = None
        for config in self.service_configs[service_name]:
            if config.endpoint == endpoint:
                endpoint_config = config
                break
        
        if not endpoint_config or endpoint_config.requests_per_window == 0:
            return None
        
        key = f"{service_name}:{endpoint}:{client_id}"
        requests = self.request_history.get(key, [])
        
        if not requests:
            return None
        
        current_time = time.time()
        window_start = current_time - endpoint_config.window_seconds
        requests_in_window = sum(1 for r in requests if r >= window_start)
        
        limit = endpoint_config.requests_per_window
        threshold = int(limit * threshold_multiplier)
        
        if requests_in_window > threshold:
            excess_percentage = ((requests_in_window - limit) / limit) * 100
            
            if requests_in_window > limit * 2:
                event_type = "SEVERE_ABUSE"
            elif requests_in_window > limit * 1.5:
                event_type = "MODERATE_ABUSE"
            else:
                event_type = "MINOR_ABUSE"
            
            event = AbuseEvent(
                timestamp=current_time,
                service_name=service_name,
                endpoint=endpoint,
                client_identifier=client_id,
                requests_in_window=requests_in_window,
                threshold=limit,
                excess_percentage=excess_percentage,
                event_type=event_type
            )
            
            self.abuse_events.append(event)
            return event
        
        return None
    
    def get_abuse_report(self) -> Dict:
        """Generate comprehensive abuse report"""
        if not self.abuse_events:
            return {
                "total_events": 0,
                "events": [],
                "summary": "No abuse events detected"
            }
        
        events_by_type = defaultdict(int)
        events_by_service = defaultdict(int)
        events_by_client = defaultdict(int)
        
        for event in self.abuse_events:
            events_by_type[event.event_type] += 1
            events_by_service[event.service_name] += 1
            events_by_client[event.client_identifier] += 1
        
        return {
            "total_events": len(self.abuse_events),
            "events": [asdict(e) for e in self.abuse_events],
            "by_type": dict(events_by_type),
            "by_service": dict(events_by_service),
            "by_client": dict(events_by_client),
            "top_offenders": sorted(events_by_client.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def get_full_report(self) -> Dict:
        """Generate full analysis and monitoring report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "analyses": [asdict(analysis) for analysis in self.analysis_results.values()],
            "abuse_report": self.get_abuse_report(),
            "services_analyzed": len(self.analysis_results)
        }


def generate_sample_configs() -> List[RateLimitConfig]:
    """Generate sample rate limit configurations for 15 services"""
    services = [
        ("user-service", "/api/users", 100, 60, "X-RateLimit-Limit", True, True, True, True, [], "sliding-window"),
        ("user-service", "/api/users/{id}", 50, 60, "X-RateLimit-Limit", True, False, True, False, [], "fixed-window"),
        ("user-service", "/api/auth/login", 5, 300, "X-RateLimit-Limit", False, True, False, False, ["token_reuse"], "fixed-window"),
        
        ("product-service", "/api/products", 500, 60, "RateLimit-Limit", True, True, False, True, [], "sliding-window"),
        ("product-service", "/api/products/search", 100, 60, "RateLimit-Limit", False, False, False, False, ["sql_injection_bypass"], "fixed-window"),
        ("product-service", "/api/products/{id}/reviews", 50, 300, "RateLimit-Limit", True, False, True, True, [], "leaky-bucket"),
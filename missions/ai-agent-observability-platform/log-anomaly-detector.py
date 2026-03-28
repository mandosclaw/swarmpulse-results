#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Log anomaly detector
# Mission: AI Agent Observability Platform
# Agent:   @bolt
# Date:    2026-03-28T22:01:26.876Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Log anomaly detector
MISSION: AI Agent Observability Platform
AGENT: @bolt
DATE: 2024

Detect anomalous log patterns in agent output streams using regex pattern analysis
and z-score statistical anomaly detection.
"""

import argparse
import json
import re
import sys
import statistics
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict


@dataclass
class LogEntry:
    timestamp: str
    level: str
    message: str
    source: str
    token_count: int
    latency_ms: float


@dataclass
class AnomalyResult:
    log_entry: LogEntry
    anomaly_type: str
    anomaly_score: float
    reason: str
    detected_patterns: List[str]
    is_anomaly: bool


class LogAnomalyDetector:
    def __init__(self, z_score_threshold: float = 2.5, pattern_threshold: int = 3):
        self.z_score_threshold = z_score_threshold
        self.pattern_threshold = pattern_threshold
        
        self.token_scores: List[float] = []
        self.latency_scores: List[float] = []
        self.message_lengths: List[int] = []
        
        self.injection_patterns = [
            r'(?i)(ignore|override|bypass|execute|system|command|shell)',
            r'(?i)(prompt_injection|malicious|attack|exploit|jailbreak)',
            r'(?i)(<\s*script|javascript:|onerror=|onclick=)',
            r'(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\s+(FROM|INTO|TABLE)',
            r'(?i)(\.\.\/?\.\.\/|\/etc\/passwd|cmd\.exe|powershell)',
            r'(?i)(eval|exec|__import__|os\.system)',
        ]
        
        self.anomaly_patterns = [
            (r'ERROR.*(?:timeout|hang|freeze)', 'latency_error'),
            (r'(?i)(traceback|exception|fatal|crash)', 'error_signature'),
            (r'token_count:\s*(\d+)(?=\D|$)', 'token_anomaly'),
            (r'(?i)(warning.*critical|critical.*warning)', 'severity_inconsistency'),
            (r'\[REDACTED\].*\[REDACTED\].*\[REDACTED\]', 'excessive_redaction'),
        ]
        
    def preprocess_logs(self, logs: List[LogEntry]) -> Tuple[List[float], List[float], List[int]]:
        """Extract metrics from log entries for statistical analysis."""
        tokens = []
        latencies = []
        msg_lengths = []
        
        for log in logs:
            tokens.append(float(log.token_count))
            latencies.append(log.latency_ms)
            msg_lengths.append(len(log.message))
        
        self.token_scores = tokens
        self.latency_scores = latencies
        self.message_lengths = msg_lengths
        
        return tokens, latencies, msg_lengths
    
    def calculate_z_scores(self, values: List[float]) -> List[float]:
        """Calculate z-scores for a list of values."""
        if len(values) < 2:
            return [0.0] * len(values)
        
        try:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            if stdev == 0:
                return [0.0] * len(values)
            
            return [(v - mean) / stdev for v in values]
        except (statistics.StatisticsError, ZeroDivisionError):
            return [0.0] * len(values)
    
    def detect_injection_patterns(self, message: str) -> List[str]:
        """Detect prompt injection and security-related patterns."""
        detected = []
        
        for pattern in self.injection_patterns:
            if re.search(pattern, message):
                detected.append(pattern)
        
        return detected
    
    def detect_anomaly_patterns(self, message: str) -> List[str]:
        """Detect application-specific anomaly patterns."""
        detected = []
        
        for pattern, pattern_type in self.anomaly_patterns:
            if re.search(pattern, message):
                detected.append(f"{pattern_type}:{pattern}")
        
        return detected
    
    def compute_anomaly_score(self, log: LogEntry, token_z: float, latency_z: float,
                             detected_patterns: List[str]) -> Tuple[float, str]:
        """Compute composite anomaly score."""
        score = 0.0
        reasons = []
        
        abs_token_z = abs(token_z)
        abs_latency_z = abs(latency_z)
        
        if abs_token_z > self.z_score_threshold:
            score += abs_token_z * 0.3
            reasons.append(f"Token count z-score: {token_z:.2f}")
        
        if abs_latency_z > self.z_score_threshold:
            score += abs_latency_z * 0.3
            reasons.append(f"Latency z-score: {latency_z:.2f}")
        
        if log.level.upper() in ['ERROR', 'CRITICAL']:
            score += 0.5
            reasons.append(f"Log level: {log.level}")
        
        pattern_count = len(detected_patterns)
        if pattern_count > 0:
            score += min(pattern_count * 0.4, 2.0)
            reasons.append(f"Detected {pattern_count} anomaly patterns")
        
        return score, "; ".join(reasons)
    
    def analyze(self, logs: List[LogEntry]) -> List[AnomalyResult]:
        """Analyze logs and detect anomalies."""
        if not logs:
            return []
        
        self.preprocess_logs(logs)
        
        token_z_scores = self.calculate_z_scores(self.token_scores)
        latency_z_scores = self.calculate_z_scores(self.latency_scores)
        
        results = []
        
        for idx, log in enumerate(logs):
            token_z = token_z_scores[idx]
            latency_z = latency_z_scores[idx]
            
            injection_patterns = self.detect_injection_patterns(log.message)
            anomaly_patterns = self.detect_anomaly_patterns(log.message)
            
            all_detected = injection_patterns + anomaly_patterns
            
            anomaly_score, reason = self.compute_anomaly_score(
                log, token_z, latency_z, all_detected
            )
            
            is_injection = len(injection_patterns) > 0
            is_statistical = (abs(token_z) > self.z_score_threshold or 
                            abs(latency_z) > self.z_score_threshold)
            is_anomaly = anomaly_score > 1.0 or is_injection or is_statistical
            
            anomaly_type = 'normal'
            if is_injection:
                anomaly_type = 'injection_attempt'
            elif is_statistical:
                anomaly_type = 'statistical_outlier'
            elif len(anomaly_patterns) > 0:
                anomaly_type = 'pattern_anomaly'
            
            result = AnomalyResult(
                log_entry=log,
                anomaly_type=anomaly_type,
                anomaly_score=anomaly_score,
                reason=reason,
                detected_patterns=all_detected,
                is_anomaly=is_anomaly
            )
            
            results.append(result)
        
        return results


def generate_sample_logs() -> List[LogEntry]:
    """Generate sample log entries for
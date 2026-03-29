#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Prompt injection detector
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-29T13:16:54.360Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Prompt Injection Detector
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2024

End-to-end observability platform for AI agents with prompt injection detection.
This module identifies potential prompt injection attacks in user inputs and LLM outputs.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Tuple, Optional


class SeverityLevel(Enum):
    """Risk severity levels for injection attempts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionFinding:
    """Represents a detected prompt injection finding."""
    timestamp: str
    text_sample: str
    detection_type: str
    severity: str
    confidence: float
    pattern_matched: str
    location: str
    remediation: str


class PromptInjectionDetector:
    """Detects prompt injection attacks in text inputs and LLM outputs."""

    def __init__(self, enable_advanced_patterns: bool = True):
        """
        Initialize the detector with pattern sets.
        
        Args:
            enable_advanced_patterns: Enable advanced regex and semantic patterns
        """
        self.enable_advanced_patterns = enable_advanced_patterns
        self.findings: List[InjectionFinding] = []
        
        # Direct instruction patterns - attempts to override system prompts
        self.direct_instruction_patterns = [
            r'(?:forget|ignore|disregard|override)\s+(?:previous|prior|all)\s+(?:instructions|prompts|directions)',
            r'(?:system|admin|root)\s+(?:command|instruction|override)',
            r'(?:new\s+)?(?:instructions?|rules?|system\s+prompt):\s*',
            r'(?:from\s+now\s+on|henceforth|instead|ignore\s+above)',
            r'(?:execute|run|perform)\s+(?:this|the\s+following)\s+(?:command|instruction|code)',
        ]
        
        # Prompt leakage patterns - attempts to extract system prompts
        self.prompt_leakage_patterns = [
            r'(?:repeat|show|display|print|output)\s+(?:your|the)\s+(?:prompt|instructions|system\s+message)',
            r'(?:what|tell|show)\s+(?:me\s+)?(?:your|the)\s+(?:real|true|actual)\s+(?:instructions|prompt)',
            r'(?:reveal|disclose|share)\s+(?:your|the)\s+(?:system|initial)\s+prompt',
            r'(?:simulate|pretend|act\s+as)\s+(?:if\s+)?you\s+were\s+(?:a|an)\s+(?:user|admin|developer)',
            r'(?:debug|trace)\s+(?:mode|output|state)',
        ]
        
        # Logical fallacy / confusion patterns
        self.confusion_patterns = [
            r'```[\s\S]*?(?:python|javascript|bash|sql|code)[\s\S]*?```',
            r'(?:eval|exec|execute)\s*\(\s*["\']',
            r'(?:SELECT|INSERT|UPDATE|DELETE)\s+(?:FROM|INTO|.*WHERE)',
            r'<(?:script|iframe|img|svg)[\s\S]*?>',
        ]
        
        # Role-play and context injection patterns
        self.roleplay_patterns = [
            r'(?:role-?play|pretend|imagine|assume|suppose|let\'s\s+say)',
            r'(?:act\s+as|play\s+the\s+role\s+of|imagine\s+you\'re)\s+(?:a|an)\s+',
            r'(?:in\s+this\s+scenario|in\s+this\s+context|within\s+this\s+universe)',
            r'(?:hypothetically|suppose|what\s+if)',
        ]
        
        # Encoding/obfuscation patterns
        self.obfuscation_patterns = [
            r'(?:base64|hex|url|unicode|rot13|caesar|morse)\s+(?:encode|decode|encoded|decoded)',
            r'(?:ascii|utf|unicode)\s+(?:code|char|character)\s+\d+',
            r'[\\x|\\u|\\0][0-9a-fA-F]{2,}',
        ]

    def detect_injections(self, text: str, location: str = "input") -> List[InjectionFinding]:
        """
        Detect prompt injection attempts in text.
        
        Args:
            text: The text to analyze
            location: Where the text came from (input/output)
            
        Returns:
            List of detected injection findings
        """
        findings = []
        text_lower = text.lower()
        
        # Check direct instruction overrides
        findings.extend(self._check_direct_instructions(text, text_lower, location))
        
        # Check prompt leakage attempts
        findings.extend(self._check_prompt_leakage(text, text_lower, location))
        
        # Check logical fallacies and code injection
        findings.extend(self._check_confusion_attacks(text, text_lower, location))
        
        # Check role-play context injection
        findings.extend(self._check_roleplay_injection(text, text_lower, location))
        
        # Check obfuscation techniques
        if self.enable_advanced_patterns:
            findings.extend(self._check_obfuscation(text, text_lower, location))
        
        # Check for multiple suspicion indicators
        findings.extend(self._check_composite_risk(text, text_lower, location))
        
        self.findings.extend(findings)
        return findings

    def _check_direct_instructions(self, text: str, text_lower: str, 
                                   location: str) -> List[InjectionFinding]:
        """Detect direct instruction override attempts."""
        findings = []
        for pattern in self.direct_instruction_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append(InjectionFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    text_sample=text[:200],
                    detection_type="direct_instruction_override",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.85,
                    pattern_matched=match.group(),
                    location=location,
                    remediation="Implement input validation and strict instruction hierarchy"
                ))
        return findings

    def _check_prompt_leakage(self, text: str, text_lower: str, 
                             location: str) -> List[InjectionFinding]:
        """Detect prompt leakage and extraction attempts."""
        findings = []
        for pattern in self.prompt_leakage_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append(InjectionFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    text_sample=text[:200],
                    detection_type="prompt_leakage",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.80,
                    pattern_matched=match.group(),
                    location=location,
                    remediation="Implement output filtering and restrict prompt disclosure"
                ))
        return findings

    def _check_confusion_attacks(self, text: str, text_lower: str, 
                                location: str) -> List[InjectionFinding]:
        """Detect logical fallacy and code injection attacks."""
        findings = []
        for pattern in self.confusion_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append(InjectionFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    text_sample=text[:200],
                    detection_type="code_injection",
                    severity=SeverityLevel.CRITICAL.value,
                    confidence=0.90,
                    pattern_matched=match.group()[:50],
                    location=location,
                    remediation="Sanitize code blocks and implement code execution sandboxing"
                ))
        return findings

    def _check_roleplay_injection(self, text: str, text_lower: str, 
                                 location: str) -> List[InjectionFinding]:
        """Detect role-play based context injection."""
        findings = []
        for pattern in self.roleplay_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append(InjectionFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    text_sample=text[:200],
                    detection_type="roleplay_injection",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.70,
                    pattern_matched=match.group(),
                    location=location,
                    remediation="Enforce explicit instruction precedence and context isolation"
                ))
        return findings

    def _check_obfuscation(self, text: str, text_lower: str, 
                          location: str) -> List[InjectionFinding]:
        """Detect obfuscation and encoding bypass attempts."""
        findings = []
        for pattern in self.obfuscation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append(InjectionFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    text_sample=text[:200],
                    detection_type="obfuscation_attempt",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.75,
                    pattern_matched=match.group(),
                    location=location,
                    remediation="Decode and re-analyze user inputs before processing"
                ))
        return findings

    def _check_composite_risk(self, text: str, text_lower: str, 
                             location: str) -> List[InjectionFinding]:
        """Detect multiple suspicion indicators suggesting composite attacks."""
        findings = []
        suspicion_score = 0
        indicators = []
        
        # Count suspicious keywords
        suspicious_keywords = [
            'forget', 'ignore', 'override', 'bypass', 'break', 'escape',
            'jailbreak', 'exploit', 'leak', 'extract', 'reveal', 'backdoor'
        ]
        
        for keyword in suspicious_keywords:
            if keyword in text_lower:
                suspicion_score += 1
                indicators.append(keyword)
        
        # Check for multiple patterns across categories
        categories_triggered = 0
        if any(re.search(p, text_lower, re.IGNORECASE) for p in self.direct_instruction_patterns):
            categories_triggered += 1
        if any(re.search(p, text_lower, re.IGNORECASE) for p in self.prompt_leakage_patterns):
            categories_triggered += 1
        if any(re.search(p, text, re.IGNORECASE) for p in self.confusion_patterns):
            categories_triggered += 1
        
        suspicion_score += categories_triggered * 2
        
        if suspicion_score >= 3 and len(indicators) > 0:
            findings.append(InjectionFinding(
                timestamp=datetime.utcnow().isoformat(),
                text_sample=text[:200],
                detection_type="composite_attack",
                severity=SeverityLevel.CRITICAL.value,
                confidence=min(0.95, 0.50 + (suspicion_score * 0.15)),
                pattern_matched=f"Multiple indicators: {', '.join(indicators[:3])}",
                location=location,
                remediation="Apply multi-layer defense: validation, filtering, sandboxing"
            ))
        
        return findings

    def get_risk_summary(self) -> Dict[str, Any]:
        """Generate a summary of all detected risks."""
        if not self.findings:
            return {
                "total_findings": 0,
                "by_severity": {},
                "by_type": {},
                "overall_risk": "low"
            }
        
        severity_counts = {}
        type_counts = {}
        
        for finding in self.findings:
            severity = finding.severity
            detection_type = finding.detection_type
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[detection_type] = type_counts.get(detection_type, 0) + 1
        
        # Determine overall risk
        overall_risk = "low"
        if severity_counts.get("critical", 0) > 0:
            overall_risk = "critical"
        elif severity_counts.get("high", 0) > 0:
            overall_risk = "high"
        elif severity_counts.get("medium", 0) > 0:
            overall_risk = "medium"
        
        return {
            "total_findings": len(self.findings),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "overall_risk": overall_risk,
            "findings": [asdict(f) for f in self.findings]
        }

    def clear_findings(self):
        """Clear all recorded findings."""
        self.findings = []


def process_batch(detector: PromptInjectionDetector, inputs: List[Dict[str, str]], 
                 output_format: str = "json") -> str:
    """
    Process a batch of inputs and generate findings report.
    
    Args:
        detector: The injection detector instance
        inputs: List of dicts with 'text' and optional 'location' keys
        output_format: Output format (json or summary)
        
    Returns:
        Formatted output string
    """
    detector.clear_findings()
    
    for item in inputs:
        text = item.get("text", "")
        location = item.get("location", "input")
        detector.detect_injections(text, location)
    
    summary = detector.get_risk_summary()
    
    if output_format == "json":
        return json.dumps(summary, indent=2)
    else:
        # Summary format
        lines = [
            "=== Prompt Injection Detection Report ===",
            f"Total Findings: {summary['total_findings']}",
            f"Overall Risk Level: {summary['overall_risk'].upper()}",
            "",
            "By Severity:",
        ]
        for severity, count in summary.get("by_severity", {}).items():
            lines.append(f"  {severity}: {count}")
        
        lines.extend(["", "By Type:"])
        for det_type, count in summary.get("by_type", {}).items():
            lines.append(f"  {det_type}: {count}")
        
        if summary['total_findings'] > 0:
            lines.extend(["", "Top Findings:"])
            for finding in summary.get("findings", [])[:5]:
                lines.append(f"  - [{finding['severity']}] {finding['detection_type']}")
                lines.append(f"    Pattern: {finding['pattern_matched'][:60]}")
        
        return "\n".join(lines)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Prompt Injection Detector for AI Agent Observability"
    )
    
    parser.add_argument(
        "--input-file",
        type=str,
        help="Path to input file with texts to analyze (JSON lines format)"
    )
    
    parser.add_argument(
        "--text",
        type=str,
        help="Single text to analyze for prompt injections"
    )
    
    parser.add_argument(
        "--location",
        type=str,
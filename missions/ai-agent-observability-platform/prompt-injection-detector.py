#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Prompt injection detector
# Mission: AI Agent Observability Platform
# Agent:   @quinn
# Date:    2026-03-28T21:58:04.628Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Prompt injection detector
Mission: AI Agent Observability Platform
Agent: @quinn
Date: 2024

Regex + ML classifier on all prompt/completion pairs in traces.
Alert on positive detections of prompt injection attempts.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List
import math


@dataclass
class InjectionIndicator:
    """Result of a single injection detection check"""
    check_name: str
    matched: bool
    confidence: float
    details: str = ""


@dataclass
class PromptInjectionAlert:
    """Alert generated when injection is detected"""
    trace_id: str
    span_id: str
    timestamp: str
    prompt_text: str
    completion_text: str
    indicators: List[InjectionIndicator] = field(default_factory=list)
    overall_risk_score: float = 0.0
    is_alert: bool = False
    detection_methods: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Convert alert to JSON"""
        data = asdict(self)
        data["indicators"] = [asdict(ind) for ind in self.indicators]
        return json.dumps(data, indent=2)


class PromptInjectionDetector:
    """Detects prompt injection attempts in LLM traces"""

    def __init__(self, regex_patterns: Optional[List[str]] = None, ml_threshold: float = 0.6):
        """
        Initialize detector with regex patterns and ML threshold.

        Args:
            regex_patterns: Optional list of regex patterns to match
            ml_threshold: Confidence threshold for ML-based detection (0.0-1.0)
        """
        self.ml_threshold = ml_threshold
        self.regex_patterns = regex_patterns or self._get_default_patterns()
        self.suspicious_keywords = self._get_suspicious_keywords()
        self.escape_indicators = self._get_escape_indicators()

    @staticmethod
    def _get_default_patterns() -> List[tuple]:
        """Default regex patterns for common injection techniques"""
        return [
            (
                "prompt_override",
                r"(ignore|disregard|override|forget).*?(previous|prior|earlier|instructions?|rules?|system)",
                0.95
            ),
            (
                "direct_instruction_injection",
                r"(you are|you're|act as|pretend to be|assume role|take on role).*?(now|immediately|from now on)",
                0.90
            ),
            (
                "context_escape",
                r"(\[END\]|\[SYSTEM\]|\[ADMIN\]|```.*?```|\\x|\\u[0-9a-f]{4})",
                0.85
            ),
            (
                "jailbreak_attempt",
                r"(jailbreak|bypass|circumvent|exploit|vulnerability|CVE-|backdoor)",
                0.92
            ),
            (
                "instruction_override",
                r"(new instructions?|updated instructions?|replace.*?instructions?)",
                0.88
            ),
            (
                "token_smuggling",
                r"(\|\||\&\&|;|&&|;|\n\n|\r\n.*?\r\n)",
                0.70
            ),
            (
                "query_parameter_injection",
                r"(\?.*?=|&.*?=|%[0-9a-f]{2})",
                0.65
            ),
            (
                "xml_injection",
                r"(<\?xml|<!DOCTYPE|<!\[CDATA\[|<.*?xmlns)",
                0.80
            ),
            (
                "encoding_obfuscation",
                r"(base64|hex|url.?encode|rot13|caesar)",
                0.75
            ),
        ]

    @staticmethod
    def _get_suspicious_keywords() -> set:
        """Keywords commonly found in injection attempts"""
        return {
            "ignore",
            "override",
            "disregard",
            "forget",
            "previous",
            "instructions",
            "rules",
            "system",
            "admin",
            "administrator",
            "root",
            "sudo",
            "bypass",
            "exploit",
            "vulnerability",
            "jailbreak",
            "backdoor",
            "act as",
            "pretend",
            "assume role",
            "new instructions",
            "updated instructions",
            "replace instructions",
            "forget about",
            "disregard the",
            "stop following",
            "no longer",
        }

    @staticmethod
    def _get_escape_indicators() -> set:
        """Escape sequences and special markers"""
        return {
            "[END]",
            "[SYSTEM]",
            "[ADMIN]",
            "[PROMPT]",
            "\\x",
            "\\u",
            "\\n",
            "```",
            "---",
            "===",
            "[BEGIN",
            "[STOP",
        }

    def _regex_check(self, text: str) -> List[InjectionIndicator]:
        """Run regex pattern checks on text"""
        indicators = []
        text_lower = text.lower()

        for pattern_name, pattern, confidence in self.regex_patterns:
            try:
                if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                    indicators.append(
                        InjectionIndicator(
                            check_name=f"regex_{pattern_name}",
                            matched=True,
                            confidence=confidence,
                            details=f"Matched pattern: {pattern[:60]}..."
                        )
                    )
            except re.error:
                pass

        return indicators

    def _keyword_check(self, text: str) -> Optional[InjectionIndicator]:
        """Check for suspicious keyword combinations"""
        text_lower = text.lower()
        words = re.findall(r"\b[a-z_]+\b", text_lower)
        keyword_matches = [w for w in words if w in self.suspicious_keywords]

        if len(keyword_matches) >= 3:
            return InjectionIndicator(
                check_name="keyword_clustering",
                matched=True,
                confidence=min(0.85, 0.5 + len(keyword_matches) * 0.1),
                details=f"Found {len(keyword_matches)} suspicious keywords: {', '.join(set(keyword_matches[:5]))}"
            )
        elif len(keyword_matches) >= 1:
            return InjectionIndicator(
                check_name="keyword_presence",
                matched=True,
                confidence=0.5 + len(keyword_matches) * 0.05,
                details=f"Found suspicious keywords: {', '.join(keyword_matches)}"
            )

        return None

    def _escape_sequence_check(self, text: str) -> Optional[InjectionIndicator]:
        """Check for escape sequences and special markers"""
        matches = [marker for marker in self.escape_indicators if marker in text]

        if matches:
            confidence = min(0.90, 0.4 + len(matches) * 0.15)
            return InjectionIndicator(
                check_name="escape_sequence_detection",
                matched=True,
                confidence=confidence,
                details=f"Found escape markers: {', '.join(matches)}"
            )

        return None

    def _statistical_check(self, text: str) -> Optional[InjectionIndicator]:
        """Statistical analysis of text for injection patterns"""
        if not text or len(text) < 20:
            return None

        words = text.split()
        word_count = len(words)
        unique_words = len(set(w.lower() for w in words))
        uniqueness_ratio = unique_words / word_count if word_count > 0 else 0

        uppercase_ratio = sum(1 for c in
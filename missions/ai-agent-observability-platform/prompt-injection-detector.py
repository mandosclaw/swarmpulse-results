#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Prompt injection detector
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-28T22:02:54.340Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Prompt injection detector
MISSION: AI Agent Observability Platform
AGENT: @dex
DATE: 2025-01-13

Detects potential prompt injection attacks in user inputs and LLM prompts.
Implements pattern matching, entropy analysis, and behavioral detection.
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Tuple
from datetime import datetime
from collections import Counter
import math


class PromptInjectionDetector:
    """Detects prompt injection attacks using multiple strategies."""

    def __init__(self, sensitivity: float = 0.7):
        """
        Initialize the detector.
        
        Args:
            sensitivity: Detection threshold (0.0 to 1.0). Higher = more aggressive.
        """
        self.sensitivity = sensitivity
        self.injection_patterns = self._load_patterns()
        self.blocked_keywords = self._load_keywords()
        self.system_prompts = self._load_system_keywords()

    def _load_patterns(self) -> List[re.Pattern]:
        """Load regex patterns for common injection techniques."""
        patterns = [
            # Role/instruction override attempts
            r'(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts|commands)',
            r'(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|assume\s+the\s+role\s+of)',
            r'(?i)(new\s+instruction|system\s+prompt|secret\s+message|hidden\s+directive)',
            # Prompt termination attempts
            r'(?i)(###|---|\*\*\*|===).*?(new\s+task|new\s+prompt|execute|run)',
            # Meta-instruction attempts
            r'(?i)(begin\s+(code\s+)?block|end\s+(code\s+)?block)',
            r'(?i)(execute.*?code|run.*?script|eval\()',
            # Extraction attempts
            r'(?i)(repeat|echo|output|print).*?(system\s+)?prompt',
            r'(?i)(show|display|dump|leak).*?(memory|context|history|configuration)',
            # Jailbreak patterns
            r'(?i)(DAN|jailbreak|bypass|circumvent)',
            r'(?i)(?<!/)/(prompt|instruction|command):\s*',
            # Encoding/obfuscation attempts
            r'(?i)(base64|hex|encoded|obfuscated)',
            r'(?i)(unicode|escape|special.*?char)',
            # XML/JSON injection
            r'</?prompt[^>]*>',
            r'</?instruction[^>]*>',
            r'(?i)("prompt"\s*:|"instruction"\s*:)',
            # SQL/Code injection markers in prompts
            r'(?i)(select\s+\*|drop\s+table|delete\s+from)',
            r'(?i)(\bor\b.*?=\s*["\']?["\']|\band\b.*?["\'].*?["\'])',
        ]
        return [re.compile(p) for p in patterns]

    def _load_keywords(self) -> List[str]:
        """Load keywords associated with injection attempts."""
        return [
            'jailbreak', 'ignore', 'forget', 'bypass', 'override',
            'execute', 'eval', 'system', 'secret', 'hidden',
            'previous', 'prior', 'original', 'instructions',
            'DAN', 'unrestricted', 'unfiltered', 'uncensored',
        ]

    def _load_system_keywords(self) -> List[str]:
        """Load system-level keywords that shouldn't appear in user input."""
        return [
            'system_prompt', 'admin', 'root', 'sudo', 'vulnerability',
            'exploit', 'backdoor', 'credentials', 'password', 'token',
        ]

    def _entropy_score(self, text: str) -> float:
        """Calculate Shannon entropy of text (high entropy = suspicious)."""
        if not text:
            return 0.0
        
        frequencies = Counter(text.lower())
        entropy = 0.0
        text_len = len(text)
        
        for count in frequencies.values():
            probability = count / text_len
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize to 0-1
        max_entropy = math.log2(min(len(frequencies), 256))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _pattern_match_score(self, text: str) -> Tuple[float, List[str]]:
        """Calculate injection score based on pattern matching."""
        matches = []
        for pattern in self.injection_patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        
        score = min(len(matches) * 0.25, 1.0)
        return score, matches

    def _keyword_score(self, text: str) -> Tuple[float, List[str]]:
        """Calculate score based on suspicious keywords."""
        text_lower = text.lower()
        found_keywords = []
        
        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        # Check for system keywords
        for keyword in self.system_keywords:
            if keyword in text_lower:
                found_keywords.append(f"SYSTEM:{keyword}")
        
        score = min(len(found_keywords) * 0.15, 1.0)
        return score, found_keywords

    def _structural_analysis(self, text: str) -> float:
        """Analyze text structure for injection markers."""
        score = 0.0
        
        # Check for suspicious delimiters
        delimiters = text.count('###') + text.count('---') + text.count('===')
        score += min(delimiters * 0.1, 0.3)
        
        # Check for mixed case/encoding markers
        unusual_chars = len(re.findall(r'[^\w\s\.\,\!\?\'\"\-\(\)]', text))
        score += min(unusual_chars * 0.01, 0.2)
        
        # Check for prompt-like structures
        if re.search(r'(?i)(prompt|instruction|task|role):', text):
            score += 0.2
        
        return min(score, 1.0)

    def _context_analysis(self, text: str, context: Dict = None) -> float:
        """Analyze context for injection attempts."""
        if not context:
            return 0.0
        
        score = 0.0
        
        # Check if input drastically differs from expected length
        if 'expected_length' in context:
            actual_length = len(text)
            expected = context['expected_length']
            if actual_length > expected * 3:
                score += 0.15
        
        # Check for sudden parameter injection
        if 'parameter_count' in context and ':' in text:
            param_count = text.count(':')
            if param_count > context['parameter_count'] * 2:
                score += 0.15
        
        return min(score, 1.0)

    def detect(
        self,
        text: str,
        context: Dict = None,
        return_details: bool = False
    ) -> Dict:
        """
        Detect prompt injection attempts.
        
        Args:
            text: Input text to analyze
            context: Optional context dict with 'expected_length', 'parameter_count'
            return_details: Include detailed analysis in response
        
        Returns:
            Detection result dictionary
        """
        if not text or not isinstance(text, str):
            return {
                'timestamp': datetime.utcnow().
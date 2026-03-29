#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement hallucination detector
# Mission: Agentic RAG Infrastructure
# Agent:   @aria
# Date:    2026-03-29T13:16:03.514Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement hallucination detector
MISSION: Agentic RAG Infrastructure
AGENT: @aria
DATE: 2024

Production-ready hallucination detection for RAG systems with multiple
detection strategies: semantic consistency, entailment checking, source
attribution verification, and statistical anomaly detection.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
from enum import Enum
from datetime import datetime
import re
import math
from collections import Counter


class HallucinationSeverity(Enum):
    """Severity levels for detected hallucinations."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HallucinationResult:
    """Result from hallucination detection analysis."""
    text: str
    is_hallucinated: bool
    severity: str
    confidence: float
    detection_methods: List[str]
    details: Dict
    timestamp: str


class SemanticConsistencyDetector:
    """Detects hallucinations via semantic consistency analysis."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute simple token-based similarity between texts."""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        return re.findall(r'\b\w+\b', text.lower())

    def detect(self, generation: str, source: str) -> Tuple[bool, float]:
        """
        Detect hallucination via semantic consistency.
        Returns (is_hallucinated, confidence).
        """
        similarity = self.compute_similarity(generation, source)
        is_hallucinated = similarity < self.threshold
        confidence = abs(similarity - self.threshold) / self.threshold
        
        return is_hallucinated, min(confidence, 1.0)


class EntailmentChecker:
    """Detects hallucinations via entailment violation."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.contradiction_patterns = [
            (r'\bnot\b.*?(\w+)', r'\b\1\b'),
            (r'\bunlike\b.*?(\w+)', r'similar.*?\1'),
            (r'\bcontrast(s|ing)?\b.*?(\w+)', r'\2'),
            (r'\bdisagree', r'\bwith\b'),
        ]

    def _extract_entities(self, text: str) -> set:
        """Extract named entities from text."""
        entity_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        return set(re.findall(entity_pattern, text))

    def _extract_facts(self, text: str) -> List[str]:
        """Extract fact-like statements."""
        sentences = re.split(r'[.!?]+', text)
        facts = [s.strip() for s in sentences if len(s.strip()) > 10]
        return facts

    def _detect_contradiction(self, fact1: str, fact2: str) -> float:
        """Detect if two facts contradict each other."""
        contradiction_score = 0.0
        
        for neg_pattern, pos_pattern in self.contradiction_patterns:
            if re.search(neg_pattern, fact1, re.IGNORECASE):
                if re.search(pos_pattern, fact2, re.IGNORECASE):
                    contradiction_score += 0.3
        
        return min(contradiction_score, 1.0)

    def detect(self, generation: str, source: str) -> Tuple[bool, float]:
        """
        Check for entailment violations.
        Returns (is_hallucinated, confidence).
        """
        gen_facts = self._extract_facts(generation)
        src_facts = self._extract_facts(source)
        
        if not gen_facts or not src_facts:
            return False, 0.0
        
        max_contradiction = 0.0
        for gen_fact in gen_facts:
            for src_fact in src_facts:
                contradiction = self._detect_contradiction(gen_fact, src_fact)
                max_contradiction = max(max_contradiction, contradiction)
        
        is_hallucinated = max_contradiction > self.threshold
        confidence = max_contradiction
        
        return is_hallucinated, confidence


class SourceAttributionValidator:
    """Validates that generated content is properly attributed to sources."""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.attribution_triggers = [
            'according to',
            'the document states',
            'the source says',
            'as mentioned',
            'cited from',
            'from the text',
            'the passage',
        ]

    def _count_verifiable_claims(self, text: str) -> int:
        """Count claims that could be verified from sources."""
        verifiable_keywords = [
            'percent', 'million', 'billion',
            'date', 'year', 'century',
            'said', 'reported', 'found',
            'study', 'research', 'data',
        ]
        
        text_lower = text.lower()
        count = sum(1 for keyword in verifiable_keywords 
                   if keyword in text_lower)
        return count

    def _check_attribution(self, text: str) -> float:
        """Check if text contains proper attribution."""
        text_lower = text.lower()
        attribution_count = sum(
            1 for trigger in self.attribution_triggers 
            if trigger in text_lower
        )
        
        sentence_count = len(re.split(r'[.!?]+', text))
        
        if sentence_count == 0:
            return 1.0
        
        attribution_ratio = attribution_count / sentence_count
        return attribution_ratio

    def detect(self, generation: str, source: str) -> Tuple[bool, float]:
        """
        Validate source attribution.
        Returns (is_hallucinated, confidence).
        """
        verifiable_claims = self._count_verifiable_claims(generation)
        attribution_score = self._check_attribution(generation)
        
        if verifiable_claims > 0 and attribution_score < self.threshold:
            is_hallucinated = True
            confidence = (self.threshold - attribution_score) / self.threshold
        else:
            is_hallucinated = False
            confidence = 0.0
        
        return is_hallucinated, min(confidence, 1.0)


class StatisticalAnomalyDetector:
    """Detects hallucinations via statistical analysis of generated text."""

    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold

    def _compute_perplexity_estimate(self, text: str) -> float:
        """Estimate perplexity based on vocabulary diversity."""
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        if len(tokens) < 2:
            return 0.0
        
        unique_tokens = len(set(tokens))
        vocab_size = unique_tokens
        text_length = len(tokens)
        
        entropy = 0.0
        token_freq = Counter(tokens)
        
        for token, count in token_freq.items():
            prob = count / text_length
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        normalized_entropy = entropy / math.log2(vocab_size) if vocab_size > 1 else 0.0
        return normalized_entropy

    def _detect_repetition(self, text: str) -> float:
        """Detect unusual repetition patterns."""
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        if len(tokens) < 3:
            return 0.0
        
        token_freq = Counter(tokens)
        max_freq = max(token_freq.values()) if token_freq else 0
        
        repetition_ratio = max_freq / len(tokens) if len(tokens) > 0 else 0
        
        return min(repetition_ratio, 1.0)

    def _detect_incoherence(self, text: str) -> float:
        """Detect logical incoherence via statistical methods."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        if len(sentences) < 2:
            return 0.0
        
        sentence_lengths = [len(re.findall(r'\b\w+\b', s)) 
                          for s in sentences]
        
        if not sentence_lengths or len(sentence_lengths) < 2:
            return 0.0
        
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((l - avg_length) ** 2 
                      for l in sentence_lengths) / len(sentence_lengths)
        
        std_dev = math.sqrt(variance)
        
        coefficient_of_variation = (std_dev / avg_length) if avg_length > 0 else 0
        
        return min(coefficient_of_variation / 2, 1.0)

    def detect(self, generation: str, source: str) -> Tuple[bool, float]:
        """
        Detect hallucinations via statistical anomalies.
        Returns (is_hallucinated, confidence).
        """
        perplexity = self._compute_perplexity_estimate(generation)
        repetition = self._detect_repetition(generation)
        incoherence = self._detect_incoherence(generation)
        
        anomaly_score = (perplexity * 0.4 + repetition * 0.3 + 
                        incoherence * 0.3)
        
        is_hallucinated = anomaly_score > self.threshold
        confidence = min(abs(anomaly_score - self.threshold), 1.0)
        
        return is_hallucinated, confidence


class HallucinationDetector:
    """Multi-method hallucination detector for RAG systems."""

    def __init__(
        self,
        semantic_weight: float = 0.25,
        entailment_weight: float = 0.25,
        attribution_weight: float = 0.25,
        statistical_weight: float = 0.25,
        overall_threshold: float = 0.5,
    ):
        self.semantic_detector = SemanticConsistencyDetector()
        self.entailment_checker = EntailmentChecker()
        self.attribution_validator = SourceAttributionValidator()
        self.statistical_detector = StatisticalAnomalyDetector()
        
        self.semantic_weight = semantic_weight
        self.entailment_weight = entailment_weight
        self.attribution_weight = attribution_weight
        self.statistical_weight = statistical_weight
        self.overall_threshold = overall_threshold
        
        weights_sum = (semantic_weight + entailment_weight + 
                      attribution_weight + statistical_weight)
        if weights_sum != 1.0:
            self.semantic_weight /= weights_sum
            self.entailment_weight /= weights_sum
            self.attribution_weight /= weights_sum
            self.statistical_weight /= weights_sum

    def detect(
        self,
        generation: str,
        source: str,
        context: Optional[str] = None,
    ) -> HallucinationResult:
        """
        Detect hallucinations using all detection methods.
        
        Args:
            generation: The text generated by the RAG system
            source: The source document/context
            context: Additional context for detection
            
        Returns:
            HallucinationResult with detailed findings
        """
        detection_methods = []
        details = {}
        
        semantic_hallucinated, semantic_confidence = (
            self.semantic_detector.detect(generation, source)
        )
        detection_methods.append("semantic_consistency")
        details["semantic_consistency"] = {
            "hallucinated": semantic_hallucinated,
            "confidence": semantic_confidence,
        }
        
        entailment_hallucinated, entailment_confidence = (
            self.entailment_checker.detect(generation, source)
        )
        detection_methods.append("entailment_checking")
        details["entailment_checking"] = {
            "hallucinated": entailment_hallucinated,
            "confidence": entailment_confidence,
        }
        
        attribution_hallucinated, attribution_confidence = (
            self.attribution_validator.detect(generation, source)
        )
        detection_methods.append("source_attribution")
        details["source_attribution"] = {
            "hallucinated": attribution_hallucinated,
            "confidence": attribution_confidence,
        }
        
        statistical_hallucinated, statistical_confidence = (
            self.statistical_detector.detect(generation, source)
        )
        detection_methods.append("statistical_anomaly")
        details["statistical_anomaly"] = {
            "hallucinated": statistical_hallucinated,
            "confidence": statistical_confidence,
        }
        
        weighted_confidence = (
            semantic_confidence * self.semantic_weight +
            entailment_confidence * self.entailment_weight +
            attribution_confidence * self.attribution_weight +
            statistical_confidence * self.statistical_weight
        )
        
        is_hallucinated = weighted_confidence > self.overall_threshold
        
        severity = self._determine_severity(weighted_confidence)
        
        return HallucinationResult(
            text=generation,
            is_hallucinated=is_hallucinated,
            severity=severity,
            confidence=weighted_confidence,
            detection_methods=detection_methods,
            details=details,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _determine_severity(self, confidence: float) -> str:
        """Determine severity level based on confidence score."""
        if confidence < 0.2:
            return HallucinationSeverity.NONE.value
        elif confidence < 0.4:
            return HallucinationSeverity.LOW.value
        elif confidence < 0.6:
            return HallucinationSeverity.MEDIUM.value
        elif confidence < 0.8:
            return HallucinationSeverity.HIGH.value
        else:
            return HallucinationSeverity.CRITICAL.value


class RAGHallucinationMonitor:
    """Monitoring system for hallucinations in RAG pipelines."""

    def __init__(self, hallucination_threshold: float = 0.5):
        self.detector = HallucinationDetector(
            overall_threshold=hallucination_threshold
        )
        self.statistics = {
            "total_checks": 0,
            "hallucinations_detected": 0,
            "by_severity": {s.value: 0 for s in HallucinationSeverity},
        }

    def analyze_generation(
        self,
        generation: str,
        source: str,
        context: Optional[str] = None,
    ) -> HallucinationResult:
        """Analyze a single generation for hallucinations."""
        result = self.detector.detect(generation, source, context)
        
        self.statistics["total_checks"] += 1
        if result.is_hallucinated:
            self.statistics["hallucinations_detected"] += 1
        self.statistics["by_severity"][result.severity] += 1
        
        return result

    def get_statistics(self) -> Dict:
        """Get monitoring statistics."""
        stats
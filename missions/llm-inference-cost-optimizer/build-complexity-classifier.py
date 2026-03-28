#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build complexity classifier
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-28T22:04:23.049Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build complexity classifier
Mission: LLM Inference Cost Optimizer
Agent: @bolt
Date: 2024

Intelligent complexity classifier for LLM requests that evaluates prompt complexity,
task requirements, and resource needs to route requests to appropriate models.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
import re
import math


class ComplexityLevel(Enum):
    """Enumeration of complexity levels."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class ComplexityMetrics:
    """Metrics used to calculate complexity."""
    token_count: int
    vocabulary_diversity: float
    sentence_count: int
    average_sentence_length: float
    has_code: bool
    has_math: bool
    has_references: bool
    punctuation_density: float
    unique_word_ratio: float
    keyword_count: int


@dataclass
class ClassificationResult:
    """Result of complexity classification."""
    complexity_level: str
    score: float
    metrics: dict
    reasoning: list
    recommended_model: str
    estimated_cost_usd: float


class ComplexityClassifier:
    """Classifies LLM prompts by complexity for cost optimization."""

    # Model routing thresholds and costs (per 1M input tokens)
    MODEL_COSTS = {
        "nano": {"threshold": 0.2, "cost": 0.05},
        "micro": {"threshold": 0.4, "cost": 0.15},
        "small": {"threshold": 0.6, "cost": 0.50},
        "medium": {"threshold": 0.8, "cost": 2.00},
        "large": {"threshold": 1.0, "cost": 10.00},
    }

    # Complexity score ranges
    COMPLEXITY_RANGES = {
        ComplexityLevel.TRIVIAL: (0.0, 0.2),
        ComplexityLevel.SIMPLE: (0.2, 0.4),
        ComplexityLevel.MODERATE: (0.4, 0.6),
        ComplexityLevel.COMPLEX: (0.6, 0.8),
        ComplexityLevel.VERY_COMPLEX: (0.8, 1.0),
    }

    # Keywords indicating complexity
    MATHEMATICAL_KEYWORDS = {
        "calculate", "compute", "equation", "formula", "integral", "derivative",
        "matrix", "tensor", "algorithm", "optimization", "probability",
        "statistical", "regression", "correlation", "variance"
    }

    CODE_INDICATORS = {"```", "def ", "class ", "import ", "function", "return"}

    REASONING_KEYWORDS = {
        "analyze", "explain", "reason", "understand", "compare", "contrast",
        "evaluate", "synthesize", "interpret", "justify", "validate"
    }

    def __init__(self):
        """Initialize the complexity classifier."""
        self.token_estimation_multiplier = 1.3

    def count_tokens(self, text: str) -> int:
        """Estimate token count using word-based approximation."""
        words = text.split()
        return max(1, int(len(words) * self.token_estimation_multiplier))

    def calculate_metrics(self, prompt: str) -> ComplexityMetrics:
        """Calculate complexity metrics from prompt text."""
        text = prompt.strip()

        # Token count
        token_count = self.count_tokens(text)

        # Vocabulary analysis
        words = text.lower().split()
        unique_words = set(words)
        vocabulary_diversity = len(unique_words) / max(1, len(words))
        unique_word_ratio = len(unique_words) / max(1, len(words))

        # Sentence analysis
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        avg_sentence_length = (
            sum(len(s.split()) for s in sentences) / max(1, sentence_count)
        )

        # Code detection
        has_code = any(indicator in text for indicator in self.CODE_INDICATORS)

        # Mathematical content detection
        has_math = any(
            keyword in text.lower() for keyword in self.MATHEMATICAL_KEYWORDS
        )

        # References detection (citations, URLs, etc.)
        has_references = bool(re.search(r'(http|https|www|ref\.|citation)', text))

        # Punctuation density
        punctuation_count = sum(1 for c in text if c in ',.;:!?-()[]{}')
        punctuation_density = punctuation_count / max(1, len(text))

        # Reasoning keywords
        keyword_count = sum(
            1 for keyword in self.REASONING_KEYWORDS if keyword in text.lower()
        )

        return ComplexityMetrics(
            token_count=token_count,
            vocabulary_diversity=vocabulary_diversity,
            sentence_count=sentence_count,
            average_sentence_length=avg_sentence_length,
            has_code=has_code,
            has_math=has_math,
            has_references=has_references,
            punctuation_density=punctuation_density,
            unique_word_ratio=unique_word_ratio,
            keyword_count=keyword_count,
        )

    def calculate_complexity_score(self, metrics: ComplexityMetrics) -> float:
        """Calculate normalized complexity score (0.0 to 1.0)."""
        score = 0.0
        reasoning = []

        # Token count contribution (0.0-0.25)
        token_score = min(metrics.token_count / 1000, 1.0) * 0.25
        score += token_score
        if metrics.token_count > 500:
            reasoning.append(
                f"High token count ({metrics.token_count}) increases complexity"
            )

        # Vocabulary diversity (0.0-0.20)
        vocab_score = metrics.vocabulary_diversity * 0.20
        score += vocab_score
        if metrics.vocabulary_diversity > 0.7:
            reasoning.append("High vocabulary diversity indicates complex domain")

        # Sentence length (0.0-0.20)
        sentence_score = min(metrics.average_sentence_length / 30, 1.0) * 0.20
        score += sentence_score
        if metrics.average_sentence_length > 20:
            reasoning.append(f"Long average sentence length ({metrics.average_sentence_length:.1f} words)")

        # Code content (0.0-0.15)
        code_score = 0.15 if metrics.has_code else 0.0
        score += code_score
        if metrics.has_code:
            reasoning.append("Prompt contains code requiring semantic understanding")

        # Mathematical content (0.0-0.10)
        math_score = 0.10 if metrics.has_math else 0.0
        score += math_score
        if metrics.has_math:
            reasoning.append("Mathematical concepts detected")

        # References (0.0-0.05)
        ref_score = 0.05 if metrics.has_references else 0.0
        score += ref_score
        if metrics.has_references:
            reasoning.append("Contains references requiring context awareness")

        # Reasoning keywords (0.0-0.05)
        keyword_contribution = min(metrics.keyword_count / 10, 1.0) * 0.05
        score += keyword_contribution
        if metrics.keyword_count > 0:
            reasoning.append(f"Contains {metrics.keyword_count} reasoning indicators")

        # Normalize to 0-1 range (should already be close)
        normalized_score = min(score, 1.0)

        return normalized_score, reasoning

    def classify(self, prompt: str